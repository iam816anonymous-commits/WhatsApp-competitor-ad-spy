import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import subprocess
import sys
import urllib.parse
import re
import requests
import pandas as pd
import logging
import random
import time
import hashlib
from datetime import datetime, timedelta
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
    analysis_text = Column(Text)
    ads = relationship("ExtractedAd", back_populates="run", cascade="all, delete-orphan")

class ScrapeSchedule(Base):
    __tablename__ = 'scrape_schedules'
    id = Column(Integer, primary_key=True)
    query = Column(String)
    frequency_hours = Column(Integer)
    next_run_at = Column(DateTime)
    is_active = Column(Integer, default=1)

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
    last_schedule_check = datetime.utcnow()
    while True:
        # 1. Process tasks from queue
        try:
            # Short timeout to allow periodic schedule checks
            task = q.get(timeout=30)
            if task is not None:
                func, args = task
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(func(*args))
                    loop.close()
                except Exception as e:
                    logger.error(f"Error in background task: {e}")
                finally:
                    q.task_done()
        except Exception: # Timeout from q.get
            pass

        # 2. Autonomous Scheduling Check (every 60s)
        if datetime.utcnow() - last_schedule_check > timedelta(seconds=60):
            last_schedule_check = datetime.utcnow()
            try:
                session = Session()
                now = datetime.utcnow()
                due_schedules = session.query(ScrapeSchedule).filter(
                    ScrapeSchedule.is_active == 1,
                    ScrapeSchedule.next_run_at <= now
                ).all()

                for sch in due_schedules:
                    logger.info(f"Triggering scheduled scrape for: {sch.query}")
                    # Create new run
                    new_run = ScrapeRun(query=sch.query, status="PENDING")
                    session.add(new_run)
                    session.commit()

                    # Enqueue
                    q.put((scrape_meta_ads_task, (new_run.id, sch.query)))

                    # Update schedule
                    sch.next_run_at = now + timedelta(hours=sch.frequency_hours)
                    session.commit()
                session.close()
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")

task_queue = get_task_queue()

# AI Analysis Configuration
class AIConfig:
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # Placeholder

def analyze_ads_with_ai(ads_data_list):
    if not AIConfig.GEMINI_API_KEY or AIConfig.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return "AI analysis skipped: API Key not provided."

    # Aggregating ad text for analysis
    combined_text = "\n---\n".join([f"Ad: {ad['text']}" for ad in ads_data_list[:10]]) # Limit to 10 ads for free tier

    prompt = f"""
    Analyze the following batch of Meta ads for a competitor. Provide a structured report:
    1. Dominant Emotional Hook: What is the main angle/emotion they are testing?
    2. Marketing Strategy: 3 bullet points summarizing their current approach.
    3. Aggression Rating: Low, Medium, or High (based on variety and quantity).

    Ads:
    {combined_text}
    """

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={AIConfig.GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"AI Analysis failed: {e}")
        return f"AI Analysis failed: {str(e)}"

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

# Dashboard and Filtering
tabs = st.tabs(["📊 Command Center", "🕵️ Manual Scrape", "📅 Schedule Manager", "📁 Historical Data"])

with tabs[0]:
    st.subheader("System Overview")
    session = Session()
    total_ads = session.query(ExtractedAd).count()
    active_schedules = session.query(ScrapeSchedule).filter_by(is_active=1).count()
    total_runs = session.query(ScrapeRun).count()

    # Calculate most active competitor
    from sqlalchemy import func
    most_active = session.query(ScrapeRun.query, func.count(ExtractedAd.id).label('ad_count'))\
        .join(ExtractedAd).group_by(ScrapeRun.query).order_by(func.count(ExtractedAd.id).desc()).first()
    most_active_str = most_active[0] if most_active else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Ads Tracked", total_ads)
    col2.metric("Active Schedules", active_schedules)
    col3.metric("Scrape Runs", total_runs)
    col4.metric("Most Active", most_active_str)

    st.markdown("### Recent AI Analytics")
    latest_analyses = session.query(ScrapeRun).filter(ScrapeRun.analysis_text != None).order_by(ScrapeRun.timestamp.desc()).limit(3).all()
    for run in latest_analyses:
        with st.expander(f"Analysis for {run.query} ({run.timestamp.strftime('%Y-%m-%d')})"):
            st.write(run.analysis_text)
    session.close()

with tabs[1]:
    brand_or_url = st.text_input("Instagram Brand Name or Meta Ad Library URL", placeholder="e.g. nike", key="manual_q")
    target_phone = st.text_input("Target Mobile Number", placeholder="e.g. 1234567890", key="manual_p")
    if st.button("Start Scrape", key="manual_btn"):
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
            st.info(f"Task queued (Run ID: {run_id}).")

with tabs[2]:
    st.subheader("Automated Monitoring")
    with st.form("new_schedule"):
        sch_query = st.text_input("Brand to Monitor")
        sch_freq = st.number_input("Frequency (Hours)", min_value=1, value=24)
        if st.form_submit_button("Create Schedule"):
            session = Session()
            new_sch = ScrapeSchedule(
                query=sch_query,
                frequency_hours=sch_freq,
                next_run_at=datetime.utcnow(),
                is_active=1
            )
            session.add(new_sch)
            session.commit()
            session.close()
            st.success(f"Schedule created for {sch_query}")

    st.markdown("---")
    session = Session()
    schedules = session.query(ScrapeSchedule).all()
    if schedules:
        for s in schedules:
            col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2])
            col1.write(f"#{s.id}")
            col2.write(f"**{s.query}**")
            col3.write(f"{s.frequency_hours}h freq")
            col4.write("✅ Active" if s.is_active else "⏸️ Paused")

            with col5:
                if s.is_active:
                    if st.button("Pause", key=f"pause_{s.id}"):
                        s.is_active = 0
                        session.commit()
                        st.rerun()
                else:
                    if st.button("Resume", key=f"resume_{s.id}"):
                        s.is_active = 1
                        session.commit()
                        st.rerun()
                if st.button("Delete", key=f"del_{s.id}"):
                    session.delete(s)
                    session.commit()
                    st.rerun()
    session.close()

with tabs[3]:
    st.subheader("Historical Ad Database")
    session = Session()
    all_queries = [r[0] for r in session.query(ScrapeRun.query).distinct().all()]
    filter_q = st.multiselect("Filter by Competitor", all_queries)
    filter_text = st.text_input("Search in Ad Text")
    date_range = st.date_input("Date Range", [])

    query = session.query(ExtractedAd).join(ScrapeRun)
    if filter_q:
        query = query.filter(ScrapeRun.query.in_(filter_q))
    if filter_text:
        query = query.filter(ExtractedAd.ad_text.like(f"%{filter_text}%"))
    if len(date_range) == 2:
        start_date = datetime.combine(date_range[0], datetime.min.time())
        end_date = datetime.combine(date_range[1], datetime.max.time())
        query = query.filter(ScrapeRun.timestamp.between(start_date, end_date))

    historical_ads = query.order_by(ExtractedAd.id.desc()).limit(100).all()
    if historical_ads:
        df_data = [{"Run": ad.run.query, "Date": ad.launch_date, "Text": ad.ad_text} for ad in historical_ads]
        st.dataframe(pd.DataFrame(df_data), use_container_width=True)
    session.close()

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

            # Perform AI Analysis before completing
            run_ads_data = [{"text": ad.ad_text} for ad in run.ads]
            if run_ads_data:
                logger.info(f"Starting AI analysis for run {run_id}")
                run.analysis_text = analyze_ads_with_ai(run_ads_data)
                session.commit()

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

if st.sidebar.button("Send Latest Digest to WhatsApp"):
    if not target_phone:
        st.error("Please enter a target phone number in the Manual Scrape tab.")
    else:
        st.info("Triggering WhatsApp automation process...")
        subprocess.Popen([sys.executable, "whatsapp_automation.py", target_phone, BrowserConfig.CHROME_USER_DATA_DIR])
