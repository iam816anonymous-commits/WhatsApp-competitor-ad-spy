import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import subprocess
import sys
import urllib.parse
import re
import pandas as pd

# BrowserConfig placeholder for local Chrome user path
class BrowserConfig:
    CHROME_USER_DATA_DIR = "/path/to/your/chrome/user/data"  # Plug in your local path here
    EXECUTABLE_PATH = None  # Optional: path to chrome executable

st.set_page_config(page_title="Competitor Ad Spy", layout="wide")

st.title("🕵️ Competitor Ad Spy")
st.write("Extract active ads from Meta Ad Library and send a summary via WhatsApp.")

# Initial layout
brand_or_url = st.text_input("Instagram Brand Name or Meta Ad Library URL", placeholder="e.g. nike or https://www.facebook.com/ads/library/...")
target_phone = st.text_input("Target Mobile Number (with country code)", placeholder="e.g. 1234567890")

if "ads_data" not in st.session_state:
    st.session_state.ads_data = None

async def scrape_meta_ads(query_or_url):
    ads = []
    async with async_playwright() as p:
        # Check if user data dir exists/is provided, otherwise launch standard
        if BrowserConfig.CHROME_USER_DATA_DIR and BrowserConfig.CHROME_USER_DATA_DIR != "/path/to/your/chrome/user/data":
            context = await p.chromium.launch_persistent_context(
                BrowserConfig.CHROME_USER_DATA_DIR,
                executable_path=BrowserConfig.EXECUTABLE_PATH,
                headless=False # Meta Ad Library often blocks headless
            )
        else:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

        page = await context.new_page()

        # Construct URL
        if query_or_url.startswith("http"):
            url = query_or_url
        else:
            query_encoded = urllib.parse.quote(query_or_url)
            url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={query_encoded}&search_type=keyword_unordered&media_type=all"

        await page.goto(url, wait_until="networkidle")

        # Handle lazy-loading scroll
        for _ in range(5): # Scroll 5 times
            await page.evaluate("window.scrollBy(0, 2000)")
            await page.wait_for_timeout(2000)

        # Extraction logic
        ad_cards = page.locator('div').filter(has_text="Started running on")
        count = await ad_cards.count()

        for i in range(count):
            card = ad_cards.nth(i)
            # Basic extraction - we look for typical patterns
            try:
                card_text = await card.inner_text()

                # Extract date
                date_match = re.search(r"Started running on (.*)", card_text)
                launch_date = date_match.group(1).split('\n')[0] if date_match else "Unknown"

                # Extract primary text (heuristic: largest block)
                lines = card_text.split('\n')
                ad_text = max(lines, key=len) if lines else "No text found"

                # Extract media links
                images = await card.locator('img').all()
                image_links = [await img.get_attribute('src') for img in images if await img.get_attribute('src')]

                videos = await card.locator('video').all()
                video_links = [await vid.get_attribute('src') for vid in videos if await vid.get_attribute('src')]

                ads.append({
                    "Launch Date": launch_date,
                    "Ad Text": ad_text,
                    "Media Links": ", ".join(image_links + video_links)
                })
            except Exception as e:
                continue

        if not BrowserConfig.CHROME_USER_DATA_DIR or BrowserConfig.CHROME_USER_DATA_DIR == "/path/to/your/chrome/user/data":
            await browser.close()
        else:
            await context.close()

    return ads

if st.button("Search Ads"):
    if not brand_or_url:
        st.error("Please enter a brand name or URL.")
    else:
        with st.spinner("Scraping Meta Ad Library..."):
            results = asyncio.run(scrape_meta_ads(brand_or_url))
            if results:
                st.session_state.ads_data = pd.DataFrame(results)
                st.success(f"Found {len(results)} ads!")
            else:
                st.session_state.ads_data = None
                st.info("No ads found or scraping failed.")

if st.session_state.ads_data is not None:
    st.subheader("Extracted Ads")
    st.dataframe(st.session_state.ads_data, use_container_width=True)

    if st.button("Send Summary to WhatsApp"):
        if not target_phone:
            st.error("Please enter a target phone number.")
        else:
            # Construct summary
            df = st.session_state.ads_data
            summary = "Competitor Ad Spy Summary:\n\n"
            for i, row in df.iterrows():
                summary += f"Ad {i+1} ({row['Launch Date']}):\n{row['Ad Text'][:100]}...\n\n"

            with st.spinner("Executing WhatsApp automation..."):
                try:
                    cmd = [sys.executable, "whatsapp_automation.py", target_phone, summary, BrowserConfig.CHROME_USER_DATA_DIR]
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    st.info("WhatsApp automation script started in a separate process. Please check the browser window if it opens.")
                except Exception as e:
                    st.error(f"Failed to execute WhatsApp script: {e}")
