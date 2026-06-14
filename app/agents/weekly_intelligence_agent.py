import logging
from sqlalchemy.orm import Session
from app.models.models import WeeklyReport, ExtractedAd, Brand
from datetime import datetime, UTC, timedelta

logger = logging.getLogger("AdSpyAgent.WeeklyIntelligence")

class WeeklyIntelligenceAgent:
    @staticmethod
    def generate_weekly_snapshot(niche: str, session: Session):
        """
        Aggregates niche data into a weekly snapshot.
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        week_ago = now - timedelta(days=7)

        # Aggregate data (Mock logic)
        top_winner = session.query(ExtractedAd).filter(
            ExtractedAd.winner_score >= 80,
            ExtractedAd.last_seen >= week_ago
        ).first()

        content = {
            "niche": niche,
            "top_performer": top_winner.ad_text[:100] if top_winner else "No dominant winner",
            "market_shift": "Increased focus on UGC in fashion" if niche == "Fashion" else "Static",
            "fastest_growing_offer": "BOGO"
        }

        report = WeeklyReport(
            week_start=week_ago,
            niche=niche,
            content_json=content
        )
        session.add(report)
        session.commit()
        return report
