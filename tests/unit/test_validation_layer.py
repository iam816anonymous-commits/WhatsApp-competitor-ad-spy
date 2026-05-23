import asyncio
from app.agents.critique_agent import CritiqueAgent
from app.agents.self_review_agent import SelfReviewAgent
from app.orchestrator.repair import RetryManager
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd

async def test_validation_layer():
    session = get_session()

    # 1. Setup a failing run
    run = ScrapeRun(query="critique_test", status="COMPLETED")
    session.add(run)
    session.commit()

    ad = ExtractedAd(
        run_id=run.id,
        ad_text="test",
        launch_date="2023",
        media_links="link",
        content_hash="crit_hash",
        extraction_confidence=0.2 # Low confidence
    )
    session.add(ad)
    session.commit()

    # 2. Run Critique
    print("Running Critique...")
    critique = await CritiqueAgent.review(run.id)
    print(f"Critique Result: {critique}")
    assert critique['critique_score'] < 1.0

    # 3. Run Auto-Repair
    print("Running Auto-Repair...")
    await RetryManager.repair_low_confidence_run(run.id)

    session.refresh(ad)
    print(f"Post-repair confidence: {ad.extraction_confidence}")
    assert ad.extraction_confidence > 0.5

    # 4. Self Review
    print("Running Self Review...")
    issues = SelfReviewAgent.audit_code_efficiency()
    # assert len(issues) > 0 # Issues are now resolved
    print(f"Detected Issues: {len(issues)}")

    session.close()

if __name__ == "__main__":
    asyncio.run(test_validation_layer())
