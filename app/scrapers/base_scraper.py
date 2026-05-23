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
from app.agents.vision_agent import generate_image_embedding
# Orchestrator will handle AI and Embeddings now

logger = logging.getLogger("AdSpyAgent.Scraper")

class BrowserConfig:
    CHROME_USER_DATA_DIR: Optional[str] = None # Should be loaded from env or passed

class BaseScraper(ABC):
    def __init__(self, run_id: int, query_or_url: str):
        self.run_id = run_id
        self.query_or_url = query_or_url
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.brand_obj = None

    @abstractmethod
    async def collect(self, brand: str):
        """Unified collection interface."""
        pass

    @abstractmethod
    async def initialize_browser(self, playwright: Any):
        pass

    @abstractmethod
    async def execute_scrape(self, page):
        pass

    async def _should_skip_brand(self, advertiser_name: str, brand_id: int, session: Any) -> bool:
        from app.models.models import Brand
        brand = session.get(Brand, brand_id)
        if not brand:
            return False

        # Exact match or alias match
        aliases = [a.strip().lower() for a in (brand.aliases or "").split(",") if a.strip()]
        aliases.append(brand.name.lower())

        if advertiser_name.lower() in aliases:
            return False

        # Check negative patterns
        negatives = [n.strip().lower() for n in (brand.negative_patterns or "").split(",") if n.strip()]
        for neg in negatives:
            if neg in advertiser_name.lower():
                logger.info(f"Disambiguation: Rejecting '{advertiser_name}' due to negative pattern '{neg}'")
                return True

        # If no match and we have aliases, it's likely a different brand
        if aliases and advertiser_name.lower() not in aliases:
             logger.info(f"Disambiguation: Rejecting '{advertiser_name}' as it doesn't match aliases for '{brand.name}'")
             return True

        return False

    async def run(self):
        session = get_session()
        run = session.get(ScrapeRun, self.run_id)
        if not run:
            session.close()
            return

        # Query Normalization
        from app.models.models import Brand
        brand_name_query = run.query.lower().strip()
        brand_obj = session.query(Brand).filter_by(name=brand_name_query).first()
        if not brand_obj:
            # Auto-seed some known brands if they don't exist
            if brand_name_query == "boat":
                brand_obj = Brand(name="boat", aliases="boAt, boat lifestyle", negative_patterns="insurance, marine, fishing, TowBoatUS")
                session.add(brand_obj)
                session.commit()

        self.brand_obj = brand_obj

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

                    # Ensure MediaResolver is closed if it was opened
                    from app.utils.media import MediaResolver
                    await MediaResolver.close()

                    # Hand off to Orchestrator
                    from app.orchestrator.engine import IntelligenceOrchestrator
                    orch = IntelligenceOrchestrator(self.run_id)
                    await orch.execute_pipeline()

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
    async def collect(self, brand: str):
        # Implementation to match unified interface
        await self.run()

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

        # New approach: Meta Ad Library uses a specific structure where each ad is in a div
        # that has a specific class or property.
        # We can find the "See ad details" link and get its closest ancestor that looks like a card.
        # This prevents leakage because each card has its own "See ad details" link.

        ad_details_buttons = page.get_by_role("button", name="See ad details")
        if await ad_details_buttons.count() == 0:
            ad_details_buttons = page.locator('div').filter(has_text=re.compile(r"^See ad details$"))

        # Increase resilience by waiting for at least one card
        try:
            await ad_details_buttons.first.wait_for(timeout=15000)
        except:
            logger.warning("No 'See ad details' buttons appeared within 15s")

        card_count = await ad_details_buttons.count()
        logger.info(f"Found {card_count} 'See ad details' buttons.")

        session = get_session()
        run = session.get(ScrapeRun, self.run_id)
        if not run:
             session.close()
             return

        seen_hashes = set()

        for i in range(card_count):
            try:
                button = ad_details_buttons.nth(i)
                card_handle = await button.evaluate_handle('''btn => {
                    let curr = btn;
                    while (curr && curr.parentElement) {
                        if (curr.innerText.includes("Started running on") &&
                            curr.offsetHeight > 200 &&
                            curr.offsetWidth > 200) {
                            return curr;
                        }
                        curr = curr.parentElement;
                    }
                    return btn.parentElement;
                }''')
                card = card_handle.as_element()
                if not card: continue

                # Disambiguation Check
                advertiser_name = await card.evaluate("card => { let lines = card.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0); let seeAdDetailsIdx = lines.indexOf('See ad details'); if (seeAdDetailsIdx !== -1 && lines.length > seeAdDetailsIdx + 1) { return lines[seeAdDetailsIdx + 1]; } return 'Unknown'; }")

                if self.brand_obj and await self._should_skip_brand(advertiser_name, self.brand_obj.id, session):
                    continue

                # Localized timeout for card internal elements
                card_text = await card.inner_text()

                # 1. Improved Metadata Removal & Text Extraction
                raw_lines = card_text.split('\n')
                lines = [line.strip() for line in raw_lines if line.strip()]

                metadata_patterns = [
                    r"Started running on",
                    r"Sponsored",
                    r"See ad details",
                    r"Library ID:",
                    r"Active",
                    r"Inactive",
                    r"Platforms",
                    r"About the Ad Library",
                    r"ID:",
                    r"Multiple versions",
                    r"Used in \d+ ads",
                    r"Open Dropdown",
                    r"See more",
                    r"System status",
                    r"Ad Library API",
                    r"About ads and data use",
                    r"Privacy",
                    r"Terms",
                    r"Cookies",
                    r"Meta ©",
                    r"English \(US\)",
                    r"SNITCH\.COM",
                    r"WWW\.SNITCH\.COM",
                    r"Shop Now",
                    r"Learn More",
                    r"Sign Up"
                ]

                # Identify launch date
                launch_date_str = "Unknown"
                for line in lines:
                    if "Started running on" in line:
                        launch_date_str = line.replace("Started running on", "").strip()
                        break

                # Filter out metadata lines
                filtered_lines = []
                for line in lines:
                    if any(re.search(pat, line, re.IGNORECASE) for pat in metadata_patterns):
                        continue
                    if len(line) < 2:
                        continue
                    filtered_lines.append(line)

                ad_text = " ".join(filtered_lines) if filtered_lines else "No text found"

                # 2. Extract Business Logic Fields
                price = None
                price_match = re.search(r"(?:Rs\.?|INR|₹)\s?(\d+(?:,\d+)?(?:\.\d+)?)|(?:$)\s?(\d+(?:\.\d+)?)", card_text)
                if price_match:
                    price = price_match.group(0)

                product_type = None
                if re.search(r"Shirt|T-shirt|Jeans|Pant|Cargo|Hoodie|Sweatshirt", card_text, re.IGNORECASE):
                    pt_match = re.search(r"Shirt|T-shirt|Jeans|Pant|Cargo|Hoodie|Sweatshirt", card_text, re.IGNORECASE)
                    product_type = pt_match.group(0)

                collection = None
                coll_match = re.search(r"(?:Collection|Drop|Line):\s?([^ \n]+)", card_text, re.IGNORECASE)
                if coll_match:
                    collection = coll_match.group(1)
                elif "New Arrival" in card_text:
                    collection = "New Arrivals"

                # 3. Media Links
                image_elements = await card.query_selector_all('img')
                image_links = []
                for img in image_elements:
                    src = await img.get_attribute('src')
                    if src and not any(x in src for x in ["/rsrc.php/", "static.xx.fbcdn.net"]):
                         image_links.append(src)

                media_links_str = ", ".join(image_links[:3])

                # 4. CTA Link
                cta_btn = await card.query_selector('a[role="button"]')
                cta_link = None
                if cta_btn:
                    cta_link = await cta_btn.get_attribute('href')

                final_url = await resolve_redirects(cta_link) if cta_link else None

                # 5. Deduplication
                normalized_text = re.sub(r'\s+', ' ', ad_text).strip().lower()
                content_to_hash = f"{normalized_text}|{media_links_str[:100]}"
                content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()

                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)

                existing = session.query(ExtractedAd).filter_by(content_hash=content_hash).first()
                if not existing:
                    local_path = await download_media(media_links_str)

                    new_ad = ExtractedAd(
                        run_id=run.id,
                        source="Meta",
                        advertiser=advertiser_name,
                        ad_text=ad_text,
                        launch_date=launch_date_str,
                        media_links=media_links_str,
                        local_media_path=local_path,
                        content_hash=content_hash,
                        final_destination_url=final_url,
                        price=price,
                        product_type=product_type,
                        collection=collection,
                        last_seen=datetime.now(UTC)
                    )
                    session.add(new_ad)
                else:
                    existing.last_seen = datetime.now(UTC)
                    existing.run_id = run.id
                session.commit()
            except Exception as e:
                logger.error(f"Error parsing ad card: {e}")
                continue
        session.close()

class TikTokScraper(BaseScraper):
    async def collect(self, brand: str):
        await self.run()

    async def initialize_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        if self.browser:
            self.context = await self.browser.new_context()

    async def execute_scrape(self, page):
        url = "https://ads.tiktok.com/business/creativecenter/ads/pc/en"
        logger.info(f"Navigating to TikTok (Stub): {url}")
        await page.goto(url)
        await asyncio.sleep(2)
