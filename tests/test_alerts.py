import pytest
from app.engines.alert_engine import AlertEngine
from app.models.models import Watchlist, ExtractedAd, Brand, Organization
from app.db.database import get_session

def test_alert_trigger():
    session = get_session()
    import time
    ts = int(time.time())
    org = Organization(name=f"AlertOrg_{ts}")
    brand = Brand(name=f"AlertBrand_{ts}")
    session.add_all([org, brand])
    session.commit()

    # Create watchlist
    watch = Watchlist(org_id=org.id, brand_id=brand.id, alert_threshold=80)
    session.add(watch)

    # Create winner ad
    ad = ExtractedAd(brand_id=brand.id, winner_score=95, ad_text="Winner!", launch_date="2023-01-01", content_hash=f"alert_h_{ts}", media_links="m1", run_id=1)
    session.add(ad)
    session.commit()

    AlertEngine.process_alerts(session)

    # Check audit log for trigger
    from app.models.models import AuditLog
    log = session.query(AuditLog).filter(
        AuditLog.org_id == org.id,
        AuditLog.action == "ALERT_TRIGGERED",
        AuditLog.details.contains(brand.name)
    ).first()
    assert log is not None
    assert brand.name in log.details

    # Cleanup
    session.delete(ad)
    session.delete(watch)
    session.delete(brand)
    session.delete(org)
    session.commit()
    session.close()
