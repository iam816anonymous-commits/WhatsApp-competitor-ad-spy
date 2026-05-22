import logging
import asyncio
from playwright.async_api import async_playwright
from typing import Dict, Any

logger = logging.getLogger("AdSpyAgent.LandingCrawler")

class LandingPageCrawler:
    @staticmethod
    async def crawl(url: str) -> Dict[str, Any]:
        logger.info(f"Crawling Landing Page: {url}")
        results = {
            "headline": None,
            "cta_text": None,
            "pixels": {},
            "scripts": []
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # 1. Headline Extraction
                results["headline"] = await page.inner_text("h1") if await page.query_selector("h1") else None

                # 2. CTA Extraction (Look for common button text)
                ctas = await page.locator("button, a[role='button']").all_inner_texts()
                results["cta_text"] = ctas[0] if ctas else None

                # 3. Pixel Detection (Simple string check in source)
                content = await page.content()
                results["pixels"]["fb"] = "fbevents.js" in content
                results["pixels"]["ga"] = "googletagmanager.com" in content
                results["pixels"]["klaviyo"] = "klaviyo.js" in content

            except Exception as e:
                logger.error(f"Failed to crawl {url}: {e}")
            finally:
                await browser.close()

        return results
