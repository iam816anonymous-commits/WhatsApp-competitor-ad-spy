import asyncio
import re
import urllib.parse
import random
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime, UTC
from playwright.async_api import async_playwright, Browser, BrowserContext

from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd
from app.utils.media import download_media, resolve_redirects
from app.agents.ai_agent import analyze_ads_with_ai
from app.agents.vision_agent import generate_image_embedding

logger = logging.getLogger("AdSpyAgent.Scraper")

class BrowserConfig:
    CHROME_USER_DATA_DIR: Optional[str] = None # Should be loaded from env or passed

class BaseScraper(ABC):
    def __init__(self, run_id: int, query_or_url: str):
        self.run_id = run_id
        self.query_or_url = query_or_url
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    @abstractmethod
    async def initialize_browser(self, playwright: Any):
        pass

    @abstractmethod
    async def execute_scrape(self, page):
        pass

    async def run(self):
        session = get_session()
        run = session.get(ScrapeRun, self.run_id)
        if not run:
            session.close()
            return

        run.status = "RUNNING"
        session.commit()

        try:
            async with async_playwright() as p:
                try:
                    await self.initialize_browser(p)
                    ctx = self.context
                    if not ctx:
                        raise Exception("Browser context not initialized")

                    page = await ctx.new_page()
                    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                    await self.execute_scrape(page)

                    # Multimodal AI analysis
                    run_ads_data = [
                        {
                            "text": ad.ad_text,
                            "local_path": ad.local_media_path,
                            "destination_url": ad.final_destination_url
                        } for ad in run.ads
                    ]
                    if run_ads_data:
                        logger.info(f"Starting Multimodal AI analysis for run {self.run_id}")
                        raw_result = await analyze_ads_with_ai(run_ads_data)

                        try:
                            # Clean markdown code blocks if Gemini includes them
                            clean_json = re.sub(r'```json\n?|\n?```', '', raw_result).strip()
                            data = json.loads(clean_json)

                            run.analysis_text = data.get("analysis_text", raw_result)
                            run.cta_type = data.get("cta_type")
                            run.emotion = data.get("emotion")
                            run.offer_type = data.get("offer_type")
                            run.price_point = data.get("price_point")
                            run.discount = data.get("discount")
                            run.urgency_score = data.get("urgency_score")
                            run.persona = data.get("persona")
                            run.visual_style = data.get("visual_style")
                            run.headline = data.get("headline")
                            run.hook_type = data.get("hook_type")
                            run.cta_text = data.get("cta_text")
                            run.brand_color = data.get("brand_color")

                            # Also update individual ads with funnel type
                            for ad_db in run.ads:
                                ad_db.funnel_type = data.get("funnel_type")
                        except Exception as e:
                            logger.error(f"Failed to parse AI JSON: {e}")
                            run.analysis_text = raw_result

                        session.commit()

                    run.status = "COMPLETED"
                    session.commit()
                finally:
                    if self.context:
                        try: await self.context.close()
                        except: pass
                    if self.browser:
                        try: await self.browser.close()
                        except: pass
        except Exception as e:
            logger.error(f"Scrape failed for run {self.run_id}: {e}")
            run.status = "FAILED"
            from datetime import timedelta
            run.next_retry_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=15)
            session.commit()
        finally:
            session.close()

class MetaScraper(BaseScraper):
    async def initialize_browser(self, playwright):
        # Local Windows Chrome Path Placeholder logic
        import os
        chrome_path = os.getenv("CHROME_USER_DATA_PATH")
        if chrome_path:
            self.context = await playwright.chromium.launch_persistent_context(
                chrome_path,
                headless=False
            )
        else:
            self.browser = await playwright.chromium.launch(headless=True)
            if self.browser:
                self.context = await self.browser.new_context()

    async def execute_scrape(self, page):
        if self.query_or_url.startswith("http"):
            url = self.query_or_url
        else:
            query_encoded = urllib.parse.quote(self.query_or_url)
            url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={query_encoded}&search_type=keyword_unordered&media_type=all"

        logger.info(f"Navigating to Meta Ad Library: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)

        for i in range(5):
            await page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
            await asyncio.sleep(random.uniform(0.5, 1.5))

        ad_cards = page.locator('div').filter(has_text="Started running on")
        count = await ad_cards.count()
        session = get_session()
        run = session.get(ScrapeRun, self.run_id)
        if not run:
             session.close()
             return

        for i in range(count):
            card = ad_cards.nth(i)
            try:
                card_text = await card.inner_text()
                date_match = re.search(r"Started running on (.*)", card_text)
                launch_date_str = date_match.group(1).split('\n')[0] if date_match else "Unknown"

                lines = card_text.split('\n')
                ad_text = max(lines, key=len) if lines else "No text found"

                images = await card.locator('img').all()
                image_links = [await img.get_attribute('src') for img in images if await img.get_attribute('src')]
                media_links_str = ", ".join(image_links)

                cta_link = await card.locator('a[role="button"]').first.get_attribute('href')
                final_url = await resolve_redirects(cta_link) if cta_link else None

                content_to_hash = f"{launch_date_str}|{ad_text}|{media_links_str}"
                content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()

                existing = session.query(ExtractedAd).filter_by(content_hash=content_hash).first()
                if not existing:
                    local_path = await download_media(media_links_str)

                    embedding = None
                    if local_path:
                        # Synchronous embedding generation for now as most ML libs are sync
                        embedding = generate_image_embedding(local_path)

                    new_ad = ExtractedAd(
                        run_id=run.id,
                        ad_text=ad_text,
                        launch_date=launch_date_str,
                        media_links=media_links_str,
                        local_media_path=local_path,
                        content_hash=content_hash,
                        final_destination_url=final_url,
                        last_seen=datetime.now(UTC),
                        creative_embedding=embedding
                    )
                    session.add(new_ad)
                else:
                    existing.last_seen = datetime.now(UTC)
                session.commit()
            except Exception as e:
                logger.error(f"Error parsing ad card: {e}")
                continue
        session.close()

class TikTokScraper(BaseScraper):
    async def initialize_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        if self.browser:
            self.context = await self.browser.new_context()

    async def execute_scrape(self, page):
        url = "https://ads.tiktok.com/business/creativecenter/ads/pc/en"
        logger.info(f"Navigating to TikTok (Stub): {url}")
        await page.goto(url)
        await asyncio.sleep(2)
