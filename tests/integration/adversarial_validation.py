import asyncio
import json
from app.api.main import trigger_scrape
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd
from app.orchestrator.engine import IntelligenceOrchestrator

async def run_adversarial_validation():
    print("--- Phase 2: Adversarial Brand Validation ---")
    brands = [
        {"name": "Nike", "niche": "Fashion"},
        {"name": "Boat", "niche": "Electronics"},
        {"name": "AG1", "niche": "Subscription"}
    ]

    results = {}

    for b in brands:
        print(f"Validating {b['name']} ({b['niche']})...")
        res = trigger_scrape(b['name'])
        run_id = res["run_id"]

        session = get_session()
        # Mocking an ad for each niche to test extraction logic
        ad = ExtractedAd(
            run_id=run_id,
            ad_text=f"Check out our new {b['niche']} drop!",
            launch_date="2024-01-01",
            media_links=f"http://{b['name'].lower()}.com/ad.jpg",
            content_hash=f"hash_{b['name']}",
            extraction_confidence=0.95
        )
        session.add(ad)
        session.commit()
        session.close()

        orch = IntelligenceOrchestrator(run_id)
        await orch.execute_pipeline()

        # Pull metrics
        session = get_session()
        run = session.get(ScrapeRun, run_id)
        results[b['name']] = {
            "niche": b['niche'],
            "critique_score": run.critique_score,
            "quality_score": run.ads[0].quality_score
        }
        session.close()

    print("--- Adversarial Validation Report ---")
    print(json.dumps(results, indent=2))
    with open("validation_report.json", "w") as f:
        json.dump(results, f)

if __name__ == "__main__":
    asyncio.run(run_adversarial_validation())
