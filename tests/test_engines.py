from datetime import datetime
from app.engines.winner_engine import WinnerEngine, EmergingEngine
from app.models.models import ExtractedAd
from app.db.database import get_session

def test_winner_engine_logic():
    ad = ExtractedAd(
        launch_date="2023-01-01", # Very old
        ad_text="SALE NOW ON",
        media_links="http://test.com/img.jpg"
    )
    score = WinnerEngine.calculate_winner_score(ad)
    assert score > 40 # At least 40 from longevity

def test_emerging_detection():
    session = get_session()
    # No ads in DB by default in test env if not seeded
    EmergingEngine.detect_emerging_winners(session)
    session.close()

def test_family_tree_logic():
    from app.engines.winner_engine import FamilyTreeEngine
    from app.models.models import ScrapeRun
    session = get_session()

    run = ScrapeRun(query="test", status="COMPLETED")
    session.add(run)
    session.commit()

    # Create two ads with same phash
    ad1 = ExtractedAd(run_id=run.id, ad_text="Original", launch_date="2023-01-01", phash="abc", content_hash="h1", media_links="m1", last_seen=datetime.now())
    ad2 = ExtractedAd(run_id=run.id, ad_text="Clone", launch_date="2023-01-02", phash="abc", content_hash="h2", media_links="m2", last_seen=datetime.now())

    session.add_all([ad1, ad2])
    session.commit()

    FamilyTreeEngine.identify_creative_clones(session)

    session.refresh(ad2)
    assert ad2.original_ad_id == ad1.id

    # Cleanup
    session.delete(ad1)
    session.delete(ad2)
    # Cleanup
    session.delete(ad1)
    session.delete(ad2)
    session.delete(run)
    session.commit()
    session.close()

def test_offer_engine():
    from app.engines.offer_engine import OfferEngine
    from app.models.models import ExtractedAd, Brand, ScrapeRun
    session = get_session()

    # Use unique name to avoid conflicts
    brand_name = f"TestBrand_Offer_{datetime.now().timestamp()}"
    brand = Brand(name=brand_name)
    run = ScrapeRun(query="test_offer", status="COMPLETED")
    session.add_all([brand, run])
    session.commit()

    ad = ExtractedAd(ad_text="Get 20% off today!", brand_id=brand.id, run_id=run.id, launch_date="2023-01-01", content_hash="oh_offer_1", media_links="m1", last_seen=datetime.now())
    session.add(ad)
    session.commit()

    offer_text = OfferEngine.extract_offer_details(ad)
    assert offer_text == "20% Off"

    OfferEngine.link_ad_to_offer(ad, session)
    session.commit()
    assert ad.offer_id is not None

    # Cleanup
    session.delete(ad)
    session.delete(brand)
    session.delete(run)
    session.commit()
    session.close()
