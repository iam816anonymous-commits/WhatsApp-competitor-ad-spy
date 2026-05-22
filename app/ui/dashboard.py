import streamlit as st
import pandas as pd
import threading
import os
import io
from datetime import datetime, UTC
from sqlalchemy import func, desc

from app.db.database import get_session
from app.models.models import ScrapeRun, ScrapeSchedule, ExtractedAd
from app.workers.scheduler import scrape_meta_ads_task
from app.utils.analytics import get_ad_longevity_category

def render_ui(task_queue):
    st.set_page_config(page_title="AdSpy AI Competitor Intelligence OS", layout="wide")
    st.title("🕵️ AdSpy AI Competitor Intelligence OS")

    # Sidebar
    st.sidebar.header("Job History")
    session = get_session()
    recent_runs = session.query(ScrapeRun).order_by(desc(ScrapeRun.timestamp)).limit(10).all()
    for r in recent_runs:
        st.sidebar.write(f"[{r.status}] {r.query} ({r.timestamp.strftime('%H:%M:%S')})")
    session.close()

    tabs = st.tabs(["📊 Command Center", "🕵️ Manual Scrape", "📅 Schedule Manager", "📁 Historical Data", "🩺 System Health"])

    with tabs[0]:
        st.subheader("System Overview")
        session = get_session()
        total_ads = session.query(ExtractedAd).count()
        active_schedules = session.query(ScrapeSchedule).filter(ScrapeSchedule.is_active == 1).count()
        total_runs = session.query(ScrapeRun).count()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Ads Tracked", total_ads)
        col2.metric("Active Schedules", active_schedules)
        col3.metric("Scrape Runs", total_runs)
        session.close()

    with tabs[1]:
        brand_or_url = st.text_input("Brand or URL")
        if st.button("Start Scrape"):
            session = get_session()
            new_run = ScrapeRun(query=str(brand_or_url), status="PENDING")
            session.add(new_run)
            session.commit()
            run_id = int(new_run.id)
            session.close()
            task_queue.put((scrape_meta_ads_task, (run_id, str(brand_or_url))))
            st.info("Queued.")

    with tabs[2]:
        with st.form("new_schedule"):
            q = st.text_input("Brand")
            f = st.number_input("Freq (H)", value=24)
            if st.form_submit_button("Create"):
                session = get_session()
                s = ScrapeSchedule(query=q, frequency_hours=f, next_run_at=datetime.now(UTC).replace(tzinfo=None))
                session.add(s)
                session.commit()
                session.close()

    with tabs[3]:
        st.subheader("Historical Data")
        session = get_session()
        ads = session.query(ExtractedAd).order_by(desc(ExtractedAd.id)).limit(100).all()
        if ads:
            df = pd.DataFrame([{
                "ID": a.id, "Brand": a.run.query, "Text": a.ad_text[:50], "Funnel": a.funnel_type
            } for a in ads])
            st.dataframe(df)
        session.close()

    with tabs[4]:
        st.subheader("System Health")
        worker_alive = any("background_worker" in str(t) or t.name == "Thread-1" for t in threading.enumerate())
        st.info(f"Worker: {'ALIVE' if worker_alive else 'DEAD'}")
        if os.path.exists("agent.log"):
            with open("agent.log", "r") as f:
                st.code("".join(f.readlines()[-20:]))
