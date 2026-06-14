import logging
from sqlalchemy.orm import Session
from app.models.models import ExtractedAd, MarketEvent, Brand
from datetime import datetime, UTC, timedelta

logger = logging.getLogger("AdSpyAgent.IntelligenceEngine")

class IntelligenceFeedEngine:
    @staticmethod
    def get_daily_feed(session: Session):
        """
        Generates a summary of the most critical intelligence from the last 24 hours.
        """
        yesterday = datetime.now(UTC) - timedelta(days=1)

        # 1. High Velocity Winners
        winners = session.query(ExtractedAd).filter(
            ExtractedAd.winner_score >= 80,
            ExtractedAd.last_seen >= yesterday
        ).all()

        # 2. Critical Market Events
        events = session.query(MarketEvent).filter(
            MarketEvent.confidence >= 0.9,
            MarketEvent.timestamp >= yesterday
        ).all()

        # 3. Emerging Opportunities (is_emerging == True)
        emerging = session.query(ExtractedAd).filter(
            ExtractedAd.is_emerging == True,
            ExtractedAd.last_seen >= yesterday
        ).all()

        return {
            "winners": winners,
            "events": events,
            "emerging": emerging
        }

class OpportunityEngine:
    @staticmethod
    def detect_gaps(session: Session):
        """
        Identifies market gaps (e.g., niches with low creative velocity or outdated offers).
        """
        # Logic: Find niches where dominant brands haven't changed offers in 30 days
        # Placeholder for now
        return ["Skincare: Opportunity for low-cost bundling (competitors have static pricing)"]
