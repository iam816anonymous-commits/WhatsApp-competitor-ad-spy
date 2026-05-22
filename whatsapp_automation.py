import sys
import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import sqlite3
import logging

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WhatsAppAutomation")

async def send_whatsapp_message(phone, user_data_dir=None):
    # Upgrade 3: High-Signal Intelligence Digest
    digest = ""
    try:
        conn = sqlite3.connect('ad_spy.db')
        cursor = conn.cursor()
        # Fetch AI analysis from the most recent completed run
        cursor.execute("""
            SELECT query, analysis_text, timestamp
            FROM scrape_runs
            WHERE status = 'COMPLETED'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row or not row[1]:
            logger.warning("No completed scrape runs with AI analysis found.")
            return

        query, analysis, timestamp = row
        digest = f"*🕵️ Ad Intelligence Digest: {query}*\n"
        digest += f"📅 _Generated: {timestamp}_\n\n"
        digest += f"📈 *Market Intelligence:*\n{analysis}\n\n"
        digest += "🚀 _Sent by Competitor Ad Spy Agent_"
        conn.close()
    except Exception as e:
        logger.error(f"Database error: {e}")
        return

    logger.info(f"Starting WhatsApp automation for {phone}")

    async with async_playwright() as p:
        browser_context = None
        browser = None
        try:
            if user_data_dir and user_data_dir != "/path/to/your/chrome/user/data":
                try:
                    browser_context = await p.chromium.launch_persistent_context(
                        user_data_dir,
                        headless=False
                    )
                except Exception as e:
                    logger.error(f"Failed to launch persistent context (is Chrome open?): {e}")
                    return
            else:
                browser = await p.chromium.launch(headless=False)
                browser_context = await browser.new_context()

            page = await browser_context.new_page()

            encoded_message = urllib.parse.quote(digest)
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"

            logger.info(f"Navigating to: {url}")
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Explicit timeouts and element checks
            send_button_selectors = [
                "button[aria-label='Send']",
                "[data-testid='send']",
                "span[data-icon='send']"
            ]

            button = None
            for selector in send_button_selectors:
                try:
                    # Wait up to 60 seconds
                    logger.info(f"Waiting for selector: {selector}")
                    button = await page.wait_for_selector(selector, timeout=60000)
                    if button:
                        break
                except Exception:
                    continue

            if button:
                await asyncio.sleep(2) # Short pause for stability
                await button.click()
                logger.info("Send button clicked successfully.")
                await page.wait_for_timeout(5000) # Wait for send to complete
            else:
                logger.error("Send button not found after 60s. Network lag or login required.")

        except Exception as e:
            logger.error(f"Automation error: {e}")
        finally:
            # Guarantee browser closure
            if browser_context:
                await browser_context.close()
            if browser:
                await browser.close()
            logger.info("Browser closed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python whatsapp_automation.py <phone> [user_data_dir]")
        sys.exit(1)

    phone = sys.argv[1]
    user_data_dir = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(send_whatsapp_message(phone, user_data_dir))
