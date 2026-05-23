import asyncio
import logging
import re
from app.scrapers.base_scraper import BaseScraper
from app.db.database import get_session
from app.models.models import Product, Brand
from datetime import datetime, UTC

logger = logging.getLogger("AdSpyAgent.EcommerceScraper")

class EcommerceScraper(BaseScraper):
    async def collect(self, brand: str):
        await self.run()

    async def initialize_browser(self, playwright):
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()

    async def execute_scrape(self, page):
        logger.info(f"Navigating to Ecommerce sources for {self.query_or_url}...")

        sources = [
            {"name": "Amazon", "url": f"https://www.amazon.in/s?k={self.query_or_url}", "selector": "div[data-component-type='s-search-result']"},
            {"name": "Flipkart", "url": f"https://www.flipkart.com/search?q={self.query_or_url}", "selector": "div[class='_1AtVbE col-12-12'], div[class='_4dd8SX']"}
        ]

        session = get_session()
        brand_obj = session.query(Brand).filter_by(name=self.query_or_url.lower()).first()

        for source in sources:
            try:
                logger.info(f"Scraping {source['name']}...")
                await page.goto(source["url"], wait_until="domcontentloaded", timeout=60000)
                products = await page.query_selector_all(source["selector"])

                for p in products[:5]:
                    try:
                        # Shared Extraction Logic (Refined per source)
                        name = "Unknown"
                        price = 0.0
                        discount = 0.0
                        rating = 0.0

                        if source["name"] == "Amazon":
                            name_el = await p.query_selector("h2 a span")
                            name = await name_el.inner_text() if name_el else "Unknown"
                            price_el = await p.query_selector(".a-price-whole")
                            price_str = await price_el.inner_text() if price_el else "0"
                            price = float(price_str.replace(",", ""))
                            # Discount
                            off_el = await p.query_selector(".a-letter-space + span")
                            off_text = await off_el.inner_text() if off_el else ""
                            if "%" in off_text:
                                discount = float(re.search(r"(\d+)", off_text).group(1))

                        elif source["name"] == "Flipkart":
                            name_el = await p.query_selector("div._4rR01T, a.IRpwTa")
                            name = await name_el.inner_text() if name_el else "Unknown"
                            price_el = await p.query_selector("div._30jeq3")
                            price_str = await price_el.inner_text() if price_el else "₹0"
                            price = float(re.sub(r"[^\d.]", "", price_str))

                        # Update DB
                        existing = session.query(Product).filter_by(name=name, source=source["name"]).first()
                        now_str = datetime.now(UTC).isoformat()
                        if existing:
                            p_hist = existing.price_history or {}
                            p_hist[now_str] = price
                            existing.price_history = p_hist
                            existing.price = price
                            existing.discount = discount
                        else:
                            new_prod = Product(
                                brand_id=brand_obj.id if brand_obj else 0,
                                name=name,
                                price=price,
                                discount=discount,
                                source=source["name"],
                                price_history={now_str: price}
                            )
                            session.add(new_prod)
                        session.commit()
                    except Exception as e:
                        logger.error(f"Error parsing {source['name']} product: {e}")
            except Exception as e:
                logger.error(f"Failed to scrape {source['name']}: {e}")

        session.close()
