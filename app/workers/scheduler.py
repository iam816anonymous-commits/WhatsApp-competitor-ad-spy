import asyncio
import logging
from queue import Queue
from threading import Thread
from datetime import datetime, UTC, timedelta

from app.db.database import get_session
from app.models.models import ScrapeRun, ScrapeSchedule, ExtractedAd
from app.scrapers.base_scraper import MetaScraper
import os

logger = logging.getLogger("AdSpyAgent.Worker")

async def scrape_meta_ads_task(run_id, query_or_url):
    scraper = MetaScraper(run_id, query_or_url)
    await scraper.run()

def background_worker(q: Queue):
    last_schedule_check = datetime.now(UTC)
    last_maintenance_check = datetime.now(UTC)

    while True:
        try:
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
        except Exception:
            pass

        now = datetime.now(UTC)

        # Scheduling
        if now - last_schedule_check > timedelta(seconds=60):
            last_schedule_check = now
            try:
                session = get_session()
                due_schedules = session.query(ScrapeSchedule).filter(
                    ScrapeSchedule.is_active == 1,
                    ScrapeSchedule.next_run_at <= now.replace(tzinfo=None)
                ).all()

                for sch in due_schedules:
                    logger.info(f"Triggering scheduled scrape for: {sch.query}")
                    new_run = ScrapeRun(query=str(sch.query), status="PENDING")
                    session.add(new_run)
                    session.commit()
                    q.put((scrape_meta_ads_task, (int(new_run.id), str(sch.query))))
                    sch.next_run_at = now.replace(tzinfo=None) + timedelta(hours=float(sch.frequency_hours))
                    session.commit()

                # Recovery
                failed_runs = session.query(ScrapeRun).filter(
                    ScrapeRun.status == "FAILED",
                    ScrapeRun.retry_count < 1,
                    ScrapeRun.next_retry_at <= now.replace(tzinfo=None)
                ).all()
                for run in failed_runs:
                    run.status = "PENDING"
                    run.retry_count = int(run.retry_count) + 1
                    session.commit()
                    q.put((scrape_meta_ads_task, (int(run.id), str(run.query))))
                session.close()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

        # Maintenance
        if now - last_maintenance_check > timedelta(hours=24):
            last_maintenance_check = now
            try:
                session = get_session()
                prune_threshold = now - timedelta(days=90)
                old_ads = session.query(ExtractedAd).filter(
                    ExtractedAd.last_seen < prune_threshold,
                    ExtractedAd.local_media_path != ""
                ).all()
                for ad in old_ads:
                    if ad.local_media_path and os.path.exists(str(ad.local_media_path)):
                        os.remove(str(ad.local_media_path))
                    ad.local_media_path = ""
                session.commit()
                session.close()
            except Exception as e:
                logger.error(f"Maintenance error: {e}")
