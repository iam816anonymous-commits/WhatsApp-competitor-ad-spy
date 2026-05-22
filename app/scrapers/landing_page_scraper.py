import asyncio
import logging
import re
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger("AdSpyAgent.LandingPageScraper")

class LandingPageScraper:
    @staticmethod
    async def analyze_url(url: str) -> Dict[str, Any]:
        """
        Navigates to a landing page and extracts marketing intelligence.
        """
        results = {
            "headline": None,
            "cta_text": None,
            "pricing": None,
            "email_capture_detected": False,
            "pixels_detected": {},
            "has_checkout": False,
            "resolved_url": url
        }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                page = await context.new_page()

                logger.info(f"Analyzing Landing Page: {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except:
                    logger.warning(f"Timeout on {url}, attempting partial extraction.")

                results["resolved_url"] = page.url

                # 1. Extract Headline (H1 or high prominence)
                h1_loc = page.locator("h1").first
                h1 = await h1_loc.text_content() if await h1_loc.count() > 0 else None
                results["headline"] = h1.strip() if h1 else None

                # 2. Detect Email Capture (Inputs with type email or newsletter text)
                email_input = await page.locator('input[type="email"], input[name*="email"]').count()
                results["email_capture_detected"] = email_input > 0

                # 3. Detect Checkout/Pricing
                body_text = await page.inner_text("body")
                # Simple regex for price detection
                prices = re.findall(r"(\$|₹|£|€)\d+(?:\.\d{2})?", body_text)
                if prices:
                    results["pricing"] = "Detected" # Could refine to find actual digits

                checkout_keywords = ["checkout", "cart", "buy now", "add to bag"]
                results["has_checkout"] = any(kw in body_text.lower() for kw in checkout_keywords)

                # 4. CTA Text
                cta_loc = page.locator('button, a[role="button"]').first
                cta = await cta_loc.text_content(timeout=5000) if await cta_loc.count() > 0 else None
                results["cta_text"] = cta.strip() if cta else None

                # 5. Pixel Detection (Check for common script patterns)
                html_content = await page.content()
                pixels = {
                    "facebook": "fbevents.js" in html_content,
                    "google": "googletagmanager.com" in html_content,
                    "tiktok": "ttq.instance" in html_content
                }
                results["pixels_detected"] = pixels

                await browser.close()
        except Exception as e:
            logger.error(f"Landing page analysis failed for {url}: {e}")

        return results

if __name__ == "__main__":
    # Test run
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(asyncio.run(LandingPageScraper.analyze_url(test_url)))
