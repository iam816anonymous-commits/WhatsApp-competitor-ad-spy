import sys
import asyncio
from playwright.async_api import async_playwright
import urllib.parse

async def send_whatsapp_message(phone, message, user_data_dir=None):
    async with async_playwright() as p:
        if user_data_dir and user_data_dir != "/path/to/your/chrome/user/data":
            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False
            )
        else:
            # Fallback if no user data dir provided - though WhatsApp Web usually needs a session
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()

        page = await context.new_page()

        encoded_message = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_message}"

        print(f"Navigating to: {url}")
        await page.goto(url)

        # Wait for the send button to appear.
        # WhatsApp Web can take a while to load.
        try:
            # Try multiple common selectors for the send button
            send_button_selectors = [
                "button[aria-label='Send']",
                "[data-testid='send']",
                "span[data-icon='send']"
            ]

            # Wait for any of these to be visible
            button = None
            for selector in send_button_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=30000)
                    if button:
                        break
                except:
                    continue

            if button:
                await button.click()
                print("Send button clicked.")
                # Wait a bit for the message to be sent
                await page.wait_for_timeout(5000)
            else:
                print("Send button not found. You might need to log in to WhatsApp Web first.")

        except Exception as e:
            print(f"Error during automation: {e}")

        if user_data_dir and user_data_dir != "/path/to/your/chrome/user/data":
            await context.close()
        else:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python whatsapp_automation.py <phone> <message> [user_data_dir]")
        sys.exit(1)

    phone = sys.argv[1]
    message = sys.argv[2]
    user_data_dir = sys.argv[3] if len(sys.argv) > 3 else None

    asyncio.run(send_whatsapp_message(phone, message, user_data_dir))
