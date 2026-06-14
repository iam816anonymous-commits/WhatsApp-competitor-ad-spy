import pytest
from app.agents.weekly_intelligence_agent import WeeklyIntelligenceAgent
from app.db.database import get_session
from app.models.models import WeeklyReport

def test_weekly_report_generation():
    session = get_session()
    report = WeeklyIntelligenceAgent.generate_weekly_snapshot("SaaS", session)
    assert report.id is not None
    assert report.niche == "SaaS"

    # Verify retrieval
    retrieved = session.get(WeeklyReport, report.id)
    assert retrieved.content_json["niche"] == "SaaS"

    # Cleanup
    session.delete(report)
    session.commit()
    session.close()
