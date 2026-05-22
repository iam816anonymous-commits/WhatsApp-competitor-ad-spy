import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import subprocess
import sys
import urllib.parse
import re
import pandas as pd
import logging
import random
import time
import hashlib
from datetime import datetime
from threading import Thread
from queue import Queue
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AdSpyAgent")

# Database Setup
Base = declarative_base()

class ScrapeRun(Base):
    __tablename__ = 'scrape_runs'
    id = Column(Integer, primary_key=True)
    query = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String) # PENDING, RUNNING, COMPLETED, FAILED
    ads = relationship("ExtractedAd", back_populates="run", cascade="all, delete-orphan")

class ExtractedAd(Base):
    __tablename__ = 'extracted_ads'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('scrape_runs.id'))
    ad_text = Column(Text)
    launch_date = Column(String)
    media_links = Column(Text)
    content_hash = Column(String, unique=True)
    run = relationship("ScrapeRun", back_populates="ads")

engine = create_engine('sqlite:///ad_spy.db', connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Task Queue and Worker using Streamlit's cache_resource for persistence
@st.cache_resource
def get_task_queue():
    q = Queue()
    worker_thread = Thread(target=background_worker, args=(q,), daemon=True)
    worker_thread.start()
    logger.info("Background worker started.")
    return q

def background_worker(q):
    while True:
        task = q.get()
        if task is None:
            break
        func, args = task
        try:
            # Create a new event loop for each task in this background thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(func(*args))
            loop.close()
        except Exception as e:
            logger.error(f"Error in background task: {e}")
        finally:
            q.task_done()

task_queue = get_task_queue()

# BrowserConfig placeholder for local Chrome user path
class BrowserConfig:
    CHROME_USER_DATA_DIR = "/path/to/your/chrome/user/data"  # Plug in your local path here
    EXECUTABLE_PATH = None  # Optional: path to chrome executable

st.set_page_config(page_title="Competitor Ad Spy AI Agent", layout="wide")

st.title("🕵️ Competitor Ad Spy AI Agent")
st.write("Modular, resilient, and database-backed ad intelligence.")

# Sidebar for Job History
st.sidebar.header("Job History")
session = Session()
recent_runs = session.query(ScrapeRun).order_by(ScrapeRun.timestamp.desc()).limit(10).all()
for r in recent_runs:
    st.sidebar.write(f"[{r.status}] {r.query} ({r.timestamp.strftime('%H:%M:%S')})")
session.close()

# Main UI
brand_or_url = st.text_input("Instagram Brand Name or Meta Ad Library URL", placeholder="e.g. nike or https://www.facebook.com/ads/library/...")
target_phone = st.text_input("Target Mobile Number (with country code)", placeholder="e.g. 1234567890")

async def scrape_meta_ads_task(run_id, query_or_url):
    session = Session()
    run = session.query(ScrapeRun).get(run_id)
    if not run:
        session.close()
        return
    run.status = "RUNNING"
    session.commit()

    browser_context = None
    browser = None
    try:
        async with async_playwright() as p:
            try:
                if BrowserConfig.CHROME_USER_DATA_DIR and BrowserConfig.CHROME_USER_DATA_DIR != "/path/to/your/chrome/user/data":
                    browser_context = await p.chromium.launch_persistent_context(
                        BrowserConfig.CHROME_USER_DATA_DIR,
                        executable_path=BrowserConfig.EXECUTABLE_PATH,
                        headless=False
                    )
                else:
                    browser = await p.chromium.launch(headless=True)
                    browser_context = await browser.new_context()
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                run.status = "FAILED"
                session.commit()
                return

            page = await browser_context.new_page()
            # Anti-bot evasion
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            if query_or_url.startswith("http"):
                url = query_or_url
            else:
                query_encoded = urllib.parse.quote(query_or_url)
                url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={query_encoded}&search_type=keyword_unordered&media_type=all"

            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Human-like scrolling
            for i in range(5):
                scroll_amount = random.randint(300, 700)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
                if i % 3 == 0:
                    await page.evaluate(f"window.scrollBy(0, -{random.randint(100, 200)})")
                    await asyncio.sleep(random.uniform(0.3, 0.7))

            # Extraction
            ad_cards = page.locator('div').filter(has_text="Started running on")
            count = await ad_cards.count()

            for i in range(count):
                card = ad_cards.nth(i)
                try:
                    card_text = await card.inner_text()
                    date_match = re.search(r"Started running on (.*)", card_text)
                    launch_date = date_match.group(1).split('\n')[0] if date_match else "Unknown"
                    lines = card_text.split('\n')
                    ad_text = max(lines, key=len) if lines else "No text found"

                    images = await card.locator('img').all()
                    image_links = [await img.get_attribute('src') for img in images if await img.get_attribute('src')]
                    videos = await card.locator('video').all()
                    video_links = [await vid.get_attribute('src') for vid in videos if await vid.get_attribute('src')]
                    media_links_str = ", ".join(image_links + video_links)

                    content_to_hash = f"{launch_date}|{ad_text}|{media_links_str}"
                    content_hash = hashlib.md5(content_to_hash.encode()).hexdigest()

                    existing = session.query(ExtractedAd).filter_by(content_hash=content_hash).first()
                    if not existing:
                        new_ad = ExtractedAd(
                            run_id=run.id,
                            ad_text=ad_text,
                            launch_date=launch_date,
                            media_links=media_links_str,
                            content_hash=content_hash
                        )
                        session.add(new_ad)
                except Exception as e:
                    continue

            run.status = "COMPLETED"
            session.commit()
    except Exception as e:
        logger.error(f"Scrape failed for run {run_id}: {e}")
        run.status = "FAILED"
        session.commit()
    finally:
        if browser_context:
            await browser_context.close()
        if browser:
            await browser.close()
        session.close()

if st.button("Start Scrape"):
    if not brand_or_url:
        st.error("Please enter a brand name or URL.")
    else:
        session = Session()
        new_run = ScrapeRun(query=brand_or_url, status="PENDING")
        session.add(new_run)
        session.commit()
        run_id = new_run.id
        session.close()

        task_queue.put((scrape_meta_ads_task, (run_id, brand_or_url)))
        st.info(f"Task queued (Run ID: {run_id}). Check Job History for status.")

# Display latest results
session = Session()
latest_ads = session.query(ExtractedAd).order_by(ExtractedAd.id.desc()).limit(20).all()
if latest_ads:
    st.subheader("Latest Extracted Ads")
    df_data = []
    for ad in latest_ads:
        df_data.append({
            "Run": ad.run.query if ad.run else "Unknown",
            "Date": ad.launch_date,
            "Text": ad.ad_text,
            "Media": ad.media_links
        })
    st.dataframe(pd.DataFrame(df_data), use_container_width=True)

if st.button("Send to WhatsApp"):
    if not target_phone:
        st.error("Please enter a target phone number.")
    else:
        # Launch WhatsApp automation as a separate process
        st.info("Triggering WhatsApp automation process...")
        subprocess.Popen([sys.executable, "whatsapp_automation.py", target_phone, BrowserConfig.CHROME_USER_DATA_DIR])
session.close()
