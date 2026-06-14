import logging
from sqlalchemy.orm import Session
from app.models.models import Brand, ExtractedAd, LandingPage, Offer, MarketEvent
from datetime import datetime, UTC, timedelta

logger = logging.getLogger("AdSpyAgent.ReportGenerator")

class WinnerReportGenerator:
    @staticmethod
    def generate_report(brand_id: int, session: Session):
        """
        Aggregates all intelligence into a structured Winner Report for a brand.
        """
        brand = session.get(Brand, brand_id)
        if not brand:
            return None

        # 1. Top Winning Creatives (Highest score)
        top_winners = session.query(ExtractedAd).filter(
            ExtractedAd.brand_id == brand_id
        ).order_by(ExtractedAd.winner_score.desc()).limit(5).all()

        # 2. Top Emerging Creatives
        emerging = session.query(ExtractedAd).filter(
            ExtractedAd.brand_id == brand_id,
            ExtractedAd.is_emerging == True
        ).limit(5).all()

        # 3. Winning Offers
        offers = session.query(Offer).filter(
            Offer.brand_id == brand_id,
            Offer.is_active == 1
        ).all()

        # 4. Clone Families (Count per original)
        from sqlalchemy import func
        clones = session.query(
            ExtractedAd.original_ad_id,
            func.count(ExtractedAd.id)
        ).filter(
            ExtractedAd.brand_id == brand_id,
            ExtractedAd.original_ad_id != None
        ).group_by(ExtractedAd.original_ad_id).all()

        # 5. Competitive Threats (Market Events)
        threats = session.query(MarketEvent).filter(
            MarketEvent.brand_id == brand_id
        ).order_by(MarketEvent.timestamp.desc()).limit(5).all()

        return {
            "brand_name": brand.name,
            "timestamp": datetime.now(UTC),
            "top_winners": top_winners,
            "emerging": emerging,
            "offers": [o.name for o in offers],
            "clone_stats": clones,
            "threats": threats,
            "recommended_angles": ["Angle 1: Focus on Urgency", "Angle 2: Emphasize BOGO"] # Placeholder
        }
