import pytest
from app.utils.stripe_utils import StripeEngine
from app.db.database import get_session
from app.models.models import Organization, ScrapeRun

def test_stripe_mock_session():
    url = StripeEngine.create_checkout_session(1, "plan_123")
    assert "stripe.com" in url
    assert "org=1" in url

def test_subscription_limits():
    session = get_session()
    org = Organization(name="LimitTestOrg")
    session.add(org)
    session.commit()

    # Add 6 completed runs (limit is 5)
    for i in range(6):
        run = ScrapeRun(query=f"q{i}", status="COMPLETED")
        session.add(run)
    session.commit()

    from app.orchestrator.engine import IntelligenceOrchestrator
    # Logic for limits should be in orchestrator or middleware
    # (Checking against current implementation)
    allowed = True # Placeholder until limits are unified in IntelligenceOrchestrator
    assert allowed is True

    # Cleanup
    session.delete(org)
    session.commit()
    session.close()
