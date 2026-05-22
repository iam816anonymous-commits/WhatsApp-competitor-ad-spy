from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_session
from app.models.models import Brand, Campaign, ExtractedAd, ScrapeRun
from app.workers.scheduler import scrape_meta_ads_task
from queue import Queue

app = FastAPI(title="AdSpy Market Intelligence API")

# Simple dependency for task queue injection
_task_queue: Queue = None

def set_task_queue(q: Queue):
    global _task_queue
    _task_queue = q

@app.get("/health")
def health_check():
    from app.utils.cost_tracker import CostTracker
    return {
        "status": "alive",
        "costs": CostTracker.get_summary()
    }

@app.post("/scrape")
def trigger_scrape(query: str):
    session = get_session()
    new_run = ScrapeRun(query=query, status="PENDING")
    session.add(new_run)
    session.commit()
    run_id = int(new_run.id)
    session.close()

    if _task_queue:
        _task_queue.put((scrape_meta_ads_task, (run_id, query)))
        return {"run_id": run_id, "message": "Scrape queued"}
    else:
        return {"run_id": run_id, "message": "Run created but queue not initialized"}

@app.get("/brands")
def get_brands():
    session = get_session()
    brands = session.query(Brand).all()
    res = [{"id": b.id, "name": b.name} for b in brands]
    session.close()
    return res

@app.get("/winners")
def get_winners():
    session = get_session()
    # Placeholder winner logic: ads active for > 21 days
    # (Implementation would use the helper in app.py logic)
    ads = session.query(ExtractedAd).all()
    session.close()
    return {"winners_count": len(ads)} # Simplified for stub
