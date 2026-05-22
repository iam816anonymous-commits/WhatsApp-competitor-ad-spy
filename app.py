import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import subprocess
import sys
import urllib.parse
import re
import os
import requests
import pandas as pd
import logging
import random
import time
import hashlib
import base64
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue
from abc import ABC, abstractmethod
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, func
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
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime)
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
    local_media_path = Column(String)
    content_hash = Column(String, unique=True)
    final_destination_url = Column(Text)
    funnel_type = Column(String)
    last_seen = Column(DateTime, default=datetime.utcnow)
    run = relationship("ScrapeRun", back_populates="ads")

engine = create_engine('sqlite:///ad_spy.db', connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Media Archive setup
os.makedirs("media_archive", exist_ok=True)

def get_ad_longevity_category(launch_date_str):
    try:
        launch_date = datetime.strptime(launch_date_str, "%b %d, %Y")
        days = (datetime.utcnow() - launch_date).days
        if days > 21:
            return "Winning Core Asset", days
        elif days > 7:
            return "Scaling", days
        else:
            return "Testing Phase", days
    except:
        return "Unknown", 0

def download_media(url):
    if not url:
        return None
    try:
        # Some URLs are comma separated strings in our DB
        first_url = url.split(',')[0].strip()
        if not first_url.startswith('http'):
            return None

        response = requests.get(first_url, timeout=10)
        if response.status_code == 200:
            content = response.content
            h = hashlib.sha256(content).hexdigest()
            ext = 'jpg' # Default extension
            filename = f"{h}.{ext}"
            filepath = os.path.join("media_archive", filename)

            with open(filepath, "wb") as f:
                f.write(content)
            return filepath
    except Exception as e:
        logger.error(f"Media download failed: {e}")
    return None

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
    last_maintenance_check = datetime.utcnow()
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

        # 2. Autonomous Scheduling and Recovery Check (every 60s)
        if datetime.utcnow() - last_schedule_check > timedelta(seconds=60):
            last_schedule_check = datetime.utcnow()
            try:
                session = Session()
                now = datetime.utcnow()

                # Check for schedules
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

                # Recovery Logic: Check for failed runs with retries remaining
                failed_runs = session.query(ScrapeRun).filter(
                    ScrapeRun.status == "FAILED",
                    ScrapeRun.retry_count < 1, # Only retry once as requested
                    ScrapeRun.next_retry_at <= now
                ).all()

                for run in failed_runs:
                    logger.info(f"Retrying failed run {run.id} for query: {run.query}")
                    run.status = "PENDING"
                    run.retry_count += 1
                    session.commit()
                    q.put((scrape_meta_ads_task, (run.id, run.query)))

                session.close()
            except Exception as e:
                logger.error(f"Error in scheduler/recovery: {e}")

        # 3. Intelligent Auto-Pruning & Maintenance (every 24h)
        if datetime.utcnow() - last_maintenance_check > timedelta(hours=24):
            last_maintenance_check = datetime.utcnow()
            try:
                session = Session()
                # Prune media for ads not seen in > 90 days
                prune_threshold = datetime.utcnow() - timedelta(days=90)
                old_ads = session.query(ExtractedAd).filter(
                    ExtractedAd.last_seen < prune_threshold,
                    ExtractedAd.local_media_path != None
                ).all()

                for ad in old_ads:
                    if os.path.exists(ad.local_media_path):
                        os.remove(ad.local_media_path)
                        logger.info(f"Pruned old media: {ad.local_media_path}")
                    ad.local_media_path = None # Keep the DB row, just remove the file

                session.commit()
                session.close()
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

task_queue = get_task_queue()

# AI Analysis Configuration
class AIConfig:
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" # Placeholder

def analyze_ads_with_ai(ads_data_list):
    if not AIConfig.GEMINI_API_KEY or AIConfig.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return "AI analysis skipped: API Key not provided."

    parts = []
    text_summary = ""
    for i, ad in enumerate(ads_data_list[:5]): # Limit to 5 for multimodal/token efficiency
        text_summary += f"Ad {i+1} Text: {ad['text']}\n"
        if ad.get('local_path') and os.path.exists(ad['local_path']):
            try:
                with open(ad['local_path'], "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_data
                        }
                    })
            except Exception:
                pass

    prompt = f"""
    Analyze these ads (text, images, and destination URLs).
    Perform OCR on any text embedded in the graphics.

    Provide a structured report:
    1. Visual Strategy & OCR: What text is in the images? What colors/styles/branding are used?
    2. Funnel Mapping: Based on the destination URLs and ad copy, what is the funnel type?
       (e.g., Direct-to-Consumer Product Page, VSL/Webinar, Lead Magnet, Advertorial, or SaaS Sign-up).
    3. Dominant Emotional Hook: What is the main angle/pain point they are testing?
    4. Marketing Strategy: 3 tactical bullet points summarizing their approach.
    5. Winning Prediction: Which ad looks like the most stable 'winner' and why?

    Ads Context:
    {text_summary}
    """
    parts.append({"text": prompt})

    try:
        # Using gemini-2.0-flash for multimodal capabilities as requested
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={AIConfig.GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": parts}]
        }
        response = requests.post(url, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"AI Multimodal Analysis failed: {e}")
        return f"AI Analysis failed: {str(e)}"

# BrowserConfig placeholder for local Chrome user path
class BrowserConfig:
    CHROME_USER_DATA_DIR = "/path/to/your/chrome/user/data"  # Plug in your local path here
    EXECUTABLE_PATH = None  # Optional: path to chrome executable

class BaseScraper(ABC):
    def __init__(self, run_id, query_or_url):
        self.run_id = run_id
        self.query_or_url = query_or_url
        self.browser = None
        self.context = None

    @abstractmethod
    async def initialize_browser(self, playwright):
        pass

    @abstractmethod
    async def execute_scrape(self, page):
        pass

    async def run(self):
        session = Session()
        run = session.query(ScrapeRun).get(self.run_id)
        if not run:
            session.close()
            return

        run.status = "RUNNING"
        session.commit()

        from playwright.async_api import async_playwright
        try:
            async with async_playwright() as p:
                await self.initialize_browser(p)
                page = await self.context.new_page()
                # Anti-bot evasion
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                await self.execute_scrape(page)

                # Perform AI Analysis before completing
                run_ads_data = [
                    {
                        "text": ad.ad_text,
                        "local_path": ad.local_media_path,
                        "destination_url": ad.final_destination_url
                    } for ad in run.ads
                ]
                if run_ads_data:
                    logger.info(f"Starting Multimodal AI analysis for run {self.run_id}")
                    run.analysis_text = analyze_ads_with_ai(run_ads_data)
                    session.commit()

                run.status = "COMPLETED"
                session.commit()
        except Exception as e:
            logger.error(f"Scrape failed for run {self.run_id}: {e}")
            run.status = "FAILED"
            run.next_retry_at = datetime.utcnow() + timedelta(minutes=15)
            session.commit()
        finally:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            session.close()

class MetaScraper(BaseScraper):
    async def initialize_browser(self, p):
        if BrowserConfig.CHROME_USER_DATA_DIR and BrowserConfig.CHROME_USER_DATA_DIR != "/path/to/your/chrome/user/data":
            self.context = await p.chromium.launch_persistent_context(
                BrowserConfig.CHROME_USER_DATA_DIR,
                executable_path=BrowserConfig.EXECUTABLE_PATH,
                headless=False
            )
        else:
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context()

    async def execute_scrape(self, page):
        if self.query_or_url.startswith("http"):
            url = self.query_or_url
        else:
            query_encoded = urllib.parse.quote(self.query_or_url)
            url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=ALL&q={query_encoded}&search_type=keyword_unordered&media_type=all"

        logger.info(f"Navigating to Meta Ad Library: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)

        # Human-like scrolling
        for i in range(5):
            scroll_amount = random.randint(300, 700)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            if i % 3 == 0:
                await page.evaluate(f"window.scrollBy(0, -{random.randint(100, 200)})")
                await asyncio.sleep(random.uniform(0.3, 0.7))

        ad_cards = page.locator('div').filter(has_text="Started running on")
        count = await ad_cards.count()
        session = Session()
        run = session.query(ScrapeRun).get(self.run_id)

        for i in range(count):
            card = ad_cards.nth(i)
            try:
                card_text = await card.inner_text()
                date_match = re.search(r"Started running on (.*)", card_text)
                launch_date_str = date_match.group(1).split('\n')[0] if date_match else "Unknown"

                # Try to parse date for longevity calculations
                try:
                    # Meta format is often "May 22, 2024"
                    launch_date_parsed = datetime.strptime(launch_date_str, "%b %d, %Y")
                except:
                    launch_date_parsed = datetime.utcnow()

                lines = card_text.split('\n')
                ad_text = max(lines, key=len) if lines else "No text found"

                images = await card.locator('img').all()
                image_links = [await img.get_attribute('src') for img in images if await img.get_attribute('src')]
                videos = await card.locator('video').all()
                video_links = [await vid.get_attribute('src') for vid in videos if await vid.get_attribute('src')]
                media_links_str = ", ".join(image_links + video_links)

                # Extract Outbound Links (Upgrade 1)
                # Meta usually uses 'a' tags for CTAs
                cta_link = await card.locator('a[role="button"]').first.get_attribute('href')
                final_url = resolve_redirects(cta_link) if cta_link else None

                content_to_hash = f"{launch_date_str}|{ad_text}|{media_links_str}"
                content_hash = hashlib.md5(content_to_hash.encode()).hexdigest()

                existing = session.query(ExtractedAd).filter_by(content_hash=content_hash).first()
                if not existing:
                    local_path = download_media(media_links_str)
                    new_ad = ExtractedAd(
                        run_id=run.id,
                        ad_text=ad_text,
                        launch_date=launch_date_str,
                        media_links=media_links_str,
                        local_media_path=local_path,
                        content_hash=content_hash,
                        final_destination_url=final_url,
                        last_seen=datetime.utcnow()
                    )
                    session.add(new_ad)
                else:
                    existing.last_seen = datetime.utcnow()
                    if final_url: existing.final_destination_url = final_url
                session.commit()
            except Exception as e:
                logger.error(f"Error parsing ad card: {e}")
                continue
        session.close()

class TikTokScraper(BaseScraper):
    async def initialize_browser(self, p):
        self.browser = await p.chromium.launch(headless=True)
        self.context = await self.browser.new_context()

    async def execute_scrape(self, page):
        # Stub for TikTok Commercial Content Library
        url = "https://ads.tiktok.com/business/creativecenter/ads/pc/en"
        logger.info(f"Navigating to TikTok (Stub): {url}")
        await page.goto(url)
        # TODO: Implement TikTok specific extraction
        await asyncio.sleep(2)

def resolve_redirects(url):
    if not url or not url.startswith('http'):
        return url
    try:
        # Standard headers to avoid bot detection during redirect follow
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.head(url, allow_redirects=True, timeout=10, headers=headers)
        return response.url
    except Exception as e:
        logger.error(f"URL Resolution failed for {url}: {e}")
        return url

async def scrape_meta_ads_task(run_id, query_or_url):
    scraper = MetaScraper(run_id, query_or_url)
    await scraper.run()

async def scrape_tiktok_ads_task(run_id, query_or_url):
    scraper = TikTokScraper(run_id, query_or_url)
    await scraper.run()

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
tabs = st.tabs(["📊 Command Center", "🕵️ Manual Scrape", "📅 Schedule Manager", "📁 Historical Data", "🩺 System Health"])

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

    st.markdown("### 🏆 Top Winning Assets")
    winning_ads = session.query(ExtractedAd).all()
    winners = [ad for ad in winning_ads if get_ad_longevity_category(ad.launch_date)[0] == "Winning Core Asset"]
    if winners:
        for w in winners[:3]:
            st.success(f"**{w.run.query}** - Active for {get_ad_longevity_category(w.launch_date)[1]} days! (Funnel: {w.funnel_type or 'N/A'})")
    else:
        st.info("No 'Winning Core Assets' identified yet. Continue monitoring competitors.")
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
        df_data = []
        for ad in historical_ads:
            longevity_cat, days = get_ad_longevity_category(ad.launch_date)
            df_data.append({
                "ID": ad.id,
                "Run": ad.run.query,
                "Status": longevity_cat,
                "Age (Days)": days,
                "Funnel": ad.funnel_type or "Unclassified",
                "Destination": ad.final_destination_url,
                "Date": ad.launch_date,
                "Text": ad.ad_text[:100] + "...",
                "Local Media": ad.local_media_path
            })
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)

        st.markdown("### 🖼️ Archived Creative Gallery")
        img_cols = st.columns(4)
        img_idx = 0
        for ad in historical_ads:
            if ad.local_media_path and os.path.exists(ad.local_media_path):
                with img_cols[img_idx % 4]:
                    st.image(ad.local_media_path, caption=f"Ad #{ad.id} from {ad.run.query}")
                img_idx += 1
            if img_idx >= 12: break # Show top 12

        # Export Insights
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ad Intelligence')

        st.download_button(
            label="📥 Export Insights (Excel)",
            data=buffer,
            file_name=f"ad_intelligence_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    session.close()

# Use anchor for tab navigation if click fails
with tabs[4]:
    st.subheader("System Health & Observability", anchor="health_tab")

    # 1. Thread Status
    import threading
    st.markdown("#### Background Services")
    worker_alive = "ALIVE" if any("background_worker" in str(t) or t.name == "Thread-1" for t in threading.enumerate()) else "DEAD"
    st.info(f"Main Executor Thread: **{worker_alive}**")

    # 2. Error Tracker
    st.markdown("#### Error Rate by Competitor")
    session = Session()
    error_stats = session.query(
        ScrapeRun.query,
        ScrapeRun.status,
        func.count(ScrapeRun.id)
    ).group_by(ScrapeRun.query, ScrapeRun.status).all()

    if error_stats:
        err_df = pd.DataFrame(error_stats, columns=["Competitor", "Status", "Count"])
        st.table(err_df)

    # 3. Log Reader
    st.markdown("#### Recent Activity (agent.log)")
    if os.path.exists("agent.log"):
        with open("agent.log", "r") as f:
            lines = f.readlines()
            st.code("".join(lines[-20:]))
    else:
        st.write("No log file found yet.")
    session.close()

if st.sidebar.button("Send Latest Digest to WhatsApp"):
    if not target_phone:
        st.error("Please enter a target phone number in the Manual Scrape tab.")
    else:
        st.info("Triggering WhatsApp automation process...")
        subprocess.Popen([sys.executable, "whatsapp_automation.py", target_phone, BrowserConfig.CHROME_USER_DATA_DIR])
