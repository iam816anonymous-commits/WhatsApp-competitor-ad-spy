import asyncio
import logging
import re
from app.scrapers.base_scraper import BaseScraper
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd
from datetime import datetime, UTC

logger = logging.getLogger("AdSpyAgent.TikTokScraper")

class TikTokScraper(BaseScraper):
    async def collect(self, brand: str):
        await self.run()

    async def initialize_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()

    async def execute_scrape(self, page):
        url = f"https://ads.tiktok.com/business/creativecenter/ads/pc/en?period=30&q={self.query_or_url}"
        logger.info(f"Navigating to TikTok Creative Center: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)

        # Wait for ad cards to load
        card_selector = "div[class*='Card']"
        try:
            await page.wait_for_selector(card_selector, timeout=15000)
        except:
            logger.warning("TikTok ad cards did not appear within 15s")

        cards = await page.query_selector_all(card_selector)
        logger.info(f"Found {len(cards)} TikTok cards.")

        session = get_session()
        for card in cards[:10]: # Limit to 10 for performance
            try:
                # 1. Extraction
                text_el = await card.query_selector("[class*='AdText']")
                text = await text_el.inner_text() if text_el else ""

                creator_el = await card.query_selector("[class*='CreatorName']")
                creator = await creator_el.inner_text() if creator_el else "Unknown"

                # 2. Score Calculations (Mocked or simplified logic)
                hashtags = " ".join(re.findall(r"#\w+", text))

                # 3. Save to DB
                # Note: content_hash needed for uniqueness
                content_hash = f"tiktok_{self.run_id}_{creator}_{hash(text)}"

                new_ad = ExtractedAd(
                    run_id=self.run_id,
                    source="TikTok",
                    advertiser=creator,
                    ad_text=text,
                    tiktok_hashtags=hashtags,
                    creative_type="Video",
                    content_hash=content_hash,
                    last_seen=datetime.now(UTC)
                )
                session.add(new_ad)
                session.commit()
            except Exception as e:
                logger.error(f"Error parsing TikTok card: {e}")
        session.close()
