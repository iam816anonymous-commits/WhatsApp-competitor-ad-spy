import streamlit as st
import pandas as pd
import threading
import os
from datetime import datetime, UTC, timedelta
from sqlalchemy import desc

from app.db.database import get_session
from app.models.models import ExtractedAd, ScrapeRun, Brand, MarketEvent
from app.engines.winner_engine import WinnerEngine, EmergingEngine, FamilyTreeEngine
from app.engines.intelligence_engine import IntelligenceFeedEngine

def render_winner_ui(task_queue):
    st.set_page_config(page_title="Winner Intelligence Platform", layout="wide")
    st.title("🏆 Winner Intelligence Engine")

    # Sidebar: Daily Intelligence Brief
    st.sidebar.header("📅 Daily Intelligence Brief")
    session = get_session()
    feed = IntelligenceFeedEngine.get_daily_feed(session)

    st.sidebar.subheader("🚀 Emerging Winners")
    for ad in feed['emerging'][:3]:
        st.sidebar.info(f"**{ad.brand.name if ad.brand else 'Unknown'}**\n{ad.ad_text[:50]}...")

    st.sidebar.subheader("⚠️ Critical Shifts")
    for event in feed['events'][:3]:
        st.sidebar.warning(f"**{event.brand.name}**: {event.event_type}")

    tabs = st.tabs(["🔥 Winner Feed", "🌳 Creative Family Trees", "📈 Emerging Trends", "🔍 Niche Analysis", "🔔 Watchlists", "🩺 System Health", "⚡ Command Center"])

    with tabs[0]:
        st.subheader("High-Confidence Winning Creatives")
        ads = session.query(ExtractedAd).filter(ExtractedAd.winner_score >= 70).order_by(desc(ExtractedAd.winner_score)).limit(50).all()

        if ads:
            for ad in ads:
                with st.expander(f"[{ad.winner_score:.0f}] {ad.brand.name if ad.brand else 'Ad'} - {ad.launch_date}"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if ad.local_media_path:
                            st.image(ad.local_media_path)
                        else:
                            st.info("No Preview")
                    with col2:
                        st.write(f"**Score:** {ad.winner_score:.1f}")
                        st.write(f"**Offer:** {ad.offer or 'Standard'}")
                        st.write(f"**Funnel:** {ad.landing_page.funnel_category if ad.landing_page else 'Unknown'}")
                        st.write(f"**Text:** {ad.ad_text}")
        else:
            st.info("No high-confidence winners detected yet.")

    with tabs[1]:
        st.subheader("Creative Family Trees (Clone Detection)")
        if st.button("Run Family Tree Identification"):
            FamilyTreeEngine.identify_creative_clones(session)
            st.success("Re-linked family trees.")

        clones = session.query(ExtractedAd).filter(ExtractedAd.original_ad_id != None).limit(50).all()
        if clones:
            df_clones = pd.DataFrame([{
                "Clone ID": c.id,
                "Original ID": c.original_ad_id,
                "Brand": c.brand.name if c.brand else "Unknown",
                "Launched": c.launch_date
            } for c in clones])
            st.table(df_clones)
        else:
            st.info("No creative clones identified yet.")

    with tabs[2]:
        st.subheader("Emerging Market Trends")
        if st.button("Detect Emerging Trends"):
            EmergingEngine.detect_emerging_winners(session)
            st.success("Scanned for emerging patterns.")

        emerging = session.query(ExtractedAd).filter(ExtractedAd.is_emerging == True).all()
        if emerging:
            for em in emerging:
                st.success(f"**Emerging Winner Detected:** {em.brand.name if em.brand else 'Unknown'} - {em.ad_text[:100]}")
        else:
            st.info("Scanning for next breakout creatives...")

    with tabs[3]:
        st.subheader("Niche Deep-Dive & Weekly Reports")
        niche = st.selectbox("Select Niche", ["Skincare", "Fashion", "Electronics", "SaaS"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Analyze Niche Trends"):
                from app.agents.niche_analyst_agent import NicheAnalystAgent
                with st.spinner("Synthesizing market movements..."):
                    import asyncio
                    # Note: This is a hack for Streamlit's sync environment
                    report = asyncio.run(NicheAnalystAgent.analyze_niche_trends(niche, session))
                    st.markdown(report)

        with col2:
            if st.button("Generate Weekly Snapshot"):
                from app.agents.weekly_intelligence_agent import WeeklyIntelligenceAgent
                WeeklyIntelligenceAgent.generate_weekly_snapshot(niche, session)
                st.success(f"Snapshot for {niche} saved.")

        st.divider()
        st.subheader("Historical Weekly Reports")
        from app.models.models import WeeklyReport
        historical = session.query(WeeklyReport).order_by(WeeklyReport.week_start.desc()).all()
        for h in historical:
            with st.expander(f"{h.niche} - Week of {h.week_start.strftime('%Y-%m-%d')}"):
                st.json(h.content_json)

    with tabs[4]:
        st.subheader("🔔 Intelligence Watchlists")
        from app.models.models import Watchlist, Brand

        # Add new watcher
        with st.form("add_watcher"):
            st.write("Watch a Brand for changes")
            brands = session.query(Brand).all()
            b_choice = st.selectbox("Brand", [b.name for b in brands]) if brands else None
            threshold = st.slider("Alert Score Threshold", 50, 100, 80)
            if st.form_submit_button("Add to Watchlist"):
                if b_choice and st.session_state.user:
                    b_obj = session.query(Brand).filter_by(name=b_choice).first()
                    w = Watchlist(org_id=st.session_state.user['org_id'], brand_id=b_obj.id, alert_threshold=threshold)
                    session.add(w)
                    session.commit()
                    st.success(f"Watching {b_choice}")

        st.divider()
        st.subheader("Active Watchers")
        # List watchers...
        watchers = session.query(Watchlist).all()
        for w in watchers:
            st.write(f"- Watching **{w.brand.name if w.brand else 'Unknown'}** (Alert at {w.alert_threshold}+ score)")

    with tabs[5]:
        st.subheader("Enterprise System Health")
        from app.utils.metrics import MetricsEngine
        stats = MetricsEngine.get_stats()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("P95 Latency", f"{stats['p95_ms']}ms")
        col2.metric("Failure Rate", f"{stats['failure_rate_pct']:.2f}%")
        col3.metric("Tasks Completed", stats['total_tasks'])
        col4.metric("Pred. Drift", f"{stats['prediction_drift']*100}%")

        st.divider()
        st.subheader("🧠 Self-Review Audit (Technical Debt)")
        from app.agents.self_review_agent import SelfReviewAgent
        issues = SelfReviewAgent.audit_code_efficiency()
        if issues:
            for issue in issues:
                st.error(f"**[{issue['module']}]** {issue['issue']} -> {issue['fix']}")
        else:
            st.success("No technical debt issues detected.")

        st.divider()
        worker_alive = any("background_worker" in str(t) or t.name == "Thread-1" for t in threading.enumerate())
        st.info(f"Worker Status: {'ONLINE' if worker_alive else 'OFFLINE'}")
        if os.path.exists("agent.log"):
            with open("agent.log", "r") as f:
                st.code("".join(f.readlines()[-20:]))

    with tabs[6]:
        st.subheader("System Control & Winner Generation")
        brand_name = st.text_input("Enter Brand Name to Analyze")
        if st.button("🚀 Generate Winner Report"):
            if brand_name:
                # 1. Create a ScrapeRun
                from app.models.models import ScrapeRun
                new_run = ScrapeRun(query=brand_name, status="PENDING")
                session.add(new_run)
                session.commit()
                run_id = new_run.id

                # 2. Queue the Scraper task
                from app.scrapers.base_scraper import MetaScraper
                from app.workers.scheduler import scrape_meta_ads_task

                st.info(f"Pipeline started for {brand_name}. Check progress in Sidebar.")
                # We reuse the existing scrape task which calls IntelligenceOrchestrator
                task_queue.put((scrape_meta_ads_task, (run_id, brand_name)))
            else:
                st.error("Please enter a brand name.")

    session.close()
