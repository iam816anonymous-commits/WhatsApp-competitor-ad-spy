import asyncio
import logging
from app.api.main import trigger_scrape
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd, MarketEvent

logging.basicConfig(level=logging.INFO)

async def run_snitch_intelligence():
    print("--- Phase 1: Live Intelligence Run (Snitch) ---")

    # Trigger via API logic
    res = trigger_scrape("Snitch")
    run_id = res["run_id"]
    print(f"Intelligence Run Started: Run ID {run_id}")

    # Wait for completion (in this environment, we'd normally wait for the worker)
    # Since we can't run the actual scraper here without real Meta access,
    # we simulate the orchestration of captured 'Snitch' data.

    session = get_session()
    run = session.get(ScrapeRun, run_id)

    # Add mock captured ads for Snitch
    import random
    ad1 = ExtractedAd(
        run_id=run_id,
        ad_text="Flat 50% Off on Snitch Fashion! Shop the new drop now.",
        launch_date="2023-10-01",
        media_links="http://snitch.com/media1.jpg",
        content_hash=f"snitch_run_{run_id}_{random.randint(0,9999)}",
        extraction_confidence=0.9
    )
    session.add(ad1)
    session.commit()
    ad_id = ad1.id
    session.close() # Close session before orchestrator starts its own

    print("Orchestrating Snitch Data...")
    from app.orchestrator.engine import IntelligenceOrchestrator
    orch = IntelligenceOrchestrator(run_id)
    await orch.execute_pipeline()

    # Verify Outputs
    print("--- Final Intelligence Report (Snitch) ---")
    session = get_session()
    ad_refreshed = session.get(ExtractedAd, ad_id)

    events = session.query(MarketEvent).filter_by(brand_id=ad_refreshed.brand_id).all()
    print(f"Market Events: {len(events)}")
    for e in events:
        print(f"- {e.event_type}: {e.description}")

    print(f"Predicted fatigue: {ad_refreshed.fatigue_days} days")
    print(f"Quality score: {ad_refreshed.quality_score}")

    session.close()

if __name__ == "__main__":
    asyncio.run(run_snitch_intelligence())
