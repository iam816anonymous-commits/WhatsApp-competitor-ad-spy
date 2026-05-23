import streamlit as st
import pandas as pd
import threading
import os
import io
from datetime import datetime, UTC, timedelta
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

    tabs = st.tabs(["📊 Command Center", "🎯 Competitor Intelligence", "🕵️ Manual Scrape", "📅 Schedule Manager", "📁 Historical Data", "👁️ Human Audit", "🩺 System Health"])

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
        st.subheader("🎯 Competitor Market Intelligence")
        session = get_session()
        from app.models.models import CompetitorProfile
        profiles = session.query(CompetitorProfile).all()
        if profiles:
            df_p = pd.DataFrame([{
                "Brand": p.brand_name,
                "Creative Count": p.creative_count,
                "Offer Shifts": p.offer_shift_count,
                "Market Velocity": p.market_velocity,
                "Last Seen": p.last_seen.strftime('%Y-%m-%d %H:%M')
            } for p in profiles])
            st.table(df_p)

            # Export Pulse Report
            from app.utils.export import ExportEngine
            if st.button("Generate Market Pulse Report (XLSX)"):
                xlsx_data = ExportEngine.generate_market_pulse_xlsx()
                st.download_button("Download Report", xlsx_data, file_name="market_pulse_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No competitor profiles tracked yet.")
        session.close()

    with tabs[2]:
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

    with tabs[3]:
        with st.form("new_schedule"):
            q = st.text_input("Brand")
            f = st.number_input("Freq (H)", value=24)
            if st.form_submit_button("Create"):
                session = get_session()
                s = ScrapeSchedule(query=q, frequency_hours=f, next_run_at=datetime.now(UTC).replace(tzinfo=None))
                session.add(s)
                session.commit()
                session.close()

    with tabs[4]:
        st.subheader("Historical Data")

        # Filter Logic (PHASE 5 EXPANSION)
        col1, col2, col3, col4 = st.columns(4)
        source_filter = col1.multiselect("Source", ["Meta", "TikTok", "Google", "Instagram"], default=["Meta", "TikTok", "Google", "Instagram"])
        funnel_filter = col2.multiselect("Funnel Type", ["Direct", "Lead Gen", "Awareness"])
        confidence_min = col3.slider("Min Confidence", 0.0, 1.0, 0.0)
        search_query = col4.text_input("Search Text")

        col5, col6, col7, col8 = st.columns(4)
        offer_filter = col5.multiselect("Offer Type", ["Discount", "Bundle", "Free Gift", "None"])
        persona_filter = col6.multiselect("Persona", ["Young Adult", "Professional", "Parent", "Student"])
        country_filter = col7.multiselect("Country", ["India", "USA", "UK", "Canada", "Global"])
        language_filter = col8.multiselect("Language", ["English", "Hindi", "Spanish", "French"])

        col9, col10, col11, col12 = st.columns(4)
        hook_filter = col9.multiselect("Hook Type", ["Question", "Stat", "UGC", "Problem/Solution"])
        collection_filter = col10.text_input("Collection")
        price_min = col11.number_input("Min Price", value=0.0)
        price_max = col12.number_input("Max Price", value=10000.0)

        col13, col14, col15, col16 = st.columns(4)
        ugc_only = col13.checkbox("UGC Only")
        viral_only = col14.checkbox("Viral Only (Score > 0.8)")
        date_range = col15.date_input("Date Range", [datetime.now(UTC) - timedelta(days=30), datetime.now(UTC)])

        session = get_session()
        query = session.query(ExtractedAd)

        if source_filter:
            query = query.filter(ExtractedAd.source.in_(source_filter))
        if funnel_filter:
            query = query.filter(ExtractedAd.funnel_type.in_(funnel_filter))
        if confidence_min > 0:
            query = query.filter(ExtractedAd.extraction_confidence >= confidence_min)
        if search_query:
            query = query.filter(ExtractedAd.ad_text.contains(search_query))
        if offer_filter:
            query = query.filter(ExtractedAd.offer.in_(offer_filter))
        if persona_filter:
            query = query.filter(ExtractedAd.persona.in_(persona_filter))
        if country_filter:
            query = query.filter(ExtractedAd.country.in_(country_filter))
        if language_filter:
            query = query.filter(ExtractedAd.language.in_(language_filter))
        if hook_filter:
            query = query.filter(ExtractedAd.hook_type.in_(hook_filter))
        if collection_filter:
            query = query.filter(ExtractedAd.collection.contains(collection_filter))
        if ugc_only:
            query = query.filter(ExtractedAd.ugc_score > 0.5)
        if viral_only:
            query = query.filter(ExtractedAd.viral_score > 0.8)

        ads = query.order_by(desc(ExtractedAd.id)).limit(100).all()
        if ads:
            df = pd.DataFrame([{
                "ID": a.id,
                "Source": a.source,
                "Brand": a.run.query,
                "Text": a.ad_text[:50],
                "Funnel": a.funnel_type,
                "Price": a.price,
                "Confidence": a.extraction_confidence,
                "Review Req": "⚠️" if a.needs_review else "✅"
            } for a in ads])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No ads match current filters.")
        session.close()

    with tabs[5]:
        st.subheader("👁️ Human-in-the-Loop Audit")
        session = get_session()
        review_ads = session.query(ExtractedAd).filter(ExtractedAd.needs_review == True).all()

        if not review_ads:
            st.success("No ads require manual review.")
        else:
            st.warning(f"{len(review_ads)} ads require verification.")
            for ad in review_ads:
                with st.expander(f"Review Ad {ad.id} (Run: {ad.run.query})"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write("**Extracted Text:**")
                        st.write(ad.ad_text)
                        st.write(f"**Confidence:** {ad.extraction_confidence}")
                        st.write(f"**Repair Attempts:** {ad.repair_attempts}")
                    with col2:
                        if ad.local_media_path:
                            st.image(ad.local_media_path)

                    # Traceability: Raw Evidence
                    from app.models.models import RawEvidence
                    evidence = session.query(RawEvidence).filter_by(run_id=ad.run_id).all()
                    if evidence:
                        st.write("**Traceability (Raw Evidence):**")
                        for ev in evidence:
                            if ev.file_path and os.path.exists(ev.file_path):
                                if ev.evidence_type == "screenshot":
                                    with open(ev.file_path, "rb") as f:
                                        st.download_button(f"Download {ev.evidence_type}", f.read(), file_name=f"run_{ad.run_id}_{ev.evidence_type}.png", key=f"dl_{ev.id}")
                                else:
                                    with open(ev.file_path, "r") as f:
                                        st.download_button(f"Download {ev.evidence_type}", f.read(), file_name=f"run_{ad.run_id}_{ev.evidence_type}.html", key=f"dl_{ev.id}")
                            elif ev.content:
                                st.download_button(f"Download {ev.evidence_type}", ev.content, file_name=f"run_{ad.run_id}_{ev.evidence_type}.json", key=f"dl_{ev.id}")

                    c1, c2 = st.columns(2)
                    if c1.button("Approve", key=f"app_{ad.id}"):
                        ad.needs_review = False
                        session.commit()
                        st.rerun()
                    if c2.button("Discard", key=f"disc_{ad.id}"):
                        session.delete(ad)
                        session.commit()
                        st.rerun()
        session.close()

    with tabs[6]:
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
