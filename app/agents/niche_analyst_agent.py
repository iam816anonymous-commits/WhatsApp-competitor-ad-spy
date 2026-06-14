import logging
from sqlalchemy.orm import Session
from app.models.models import Brand, ExtractedAd, MarketEvent
from app.agents.ai_agent import analyze_ads_with_ai

logger = logging.getLogger("AdSpyAgent.NicheAnalyst")

class NicheAnalystAgent:
    @staticmethod
    async def analyze_niche_trends(niche: str, session: Session):
        """
        Analyzes all brands within a specific niche to identify overarching trends.
        """
        logger.info(f"Analyzing niche trends for: {niche}")

        # 1. Fetch all brands in this niche
        brands = session.query(Brand).filter(Brand.niche == niche).all()
        brand_ids = [b.id for b in brands]

        if not brand_ids:
            return f"No brands found for niche: {niche}"

        # 2. Aggregate recent events across the niche
        events = session.query(MarketEvent).filter(
            MarketEvent.brand_id.in_(brand_ids)
        ).order_by(MarketEvent.timestamp.desc()).limit(20).all()

        event_summary = "\n".join([f"- {e.brand.name}: {e.event_type} - {e.description}" for e in events])

        # 3. AI synthesis for the niche
        prompt = f"""
        SYSTEM: Expert Niche Market Intelligence Analyst.
        NICHE: {niche}
        brands: {', '.join([b.name for b in brands])}

        RECENT EVENTS IN NICHE:
        {event_summary}

        TASK: Identify the top 3 trends emerging in this niche and suggest a 'Counter-Move' strategy for a new competitor.
        """

        try:
            report = await analyze_ads_with_ai([{"text": prompt}])
            return report
        except Exception as e:
            logger.error(f"Niche analysis failed: {e}")
            return f"Analysis failed: {e}"
