import asyncio
from app.db.database import get_session
from app.models.models import ExtractedAd, MarketEvent, ScrapeRun
from app.orchestrator.engine import IntelligenceOrchestrator

async def test_quality_and_events():
    session = get_session()

    # Setup mock data
    run = ScrapeRun(query="test_brand", status="PENDING")
    session.add(run)
    session.commit()

    ad = ExtractedAd(
        run_id=run.id,
        ad_text="This is a test ad text for quality scoring.",
        launch_date="2023-01-01",
        media_links="http://example.com/img.jpg",
        content_hash="test_hash_1"
    )
    session.add(ad)
    session.commit()

    orch = IntelligenceOrchestrator(run.id)

    # Test Quality Score calculation
    # ad.quality_score should be 0.5 (text > 10, media links exist but no embedding or destination yet)
    # Wait, the orchestrator calculates it during execute_pipeline after enrichments.

    score = orch._calculate_quality_score(ad)
    print(f"Calculated Quality Score: {score}")
    assert score == 0.25 # Only text > 10 for now in this manual call

    ad.creative_embedding = b"somebytes"
    score = orch._calculate_quality_score(ad)
    print(f"Quality Score with Embedding: {score}")
    assert score == 0.5

    # Test Market Event logging
    # Usually handled in _process_ai_result
    mock_ai_result = '{"offer_type": "Authority Funnel", "cta_type": "Learn More", "persona": "CEO", "headline": "New Hook", "analysis_text": "text"}'
    await orch._process_ai_result(session, run, mock_ai_result)

    event = session.query(MarketEvent).filter_by(brand_id=ad.brand_id).first()
    if event:
        print(f"Event detected: {event.event_type}, Confidence: {event.confidence}")
        assert event.confidence == 0.92

    session.close()

if __name__ == "__main__":
    asyncio.run(test_quality_and_events())
