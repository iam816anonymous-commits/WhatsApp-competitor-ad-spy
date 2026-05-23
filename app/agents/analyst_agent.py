import logging
from datetime import datetime, UTC, timedelta
from typing import Dict, Any
from app.db.database import get_session
from app.models.models import Brand, MarketEvent, ExtractedAd, CompetitorProfile
from app.agents.ai_agent import analyze_ads_with_ai

logger = logging.getLogger("AdSpyAgent.Analyst")

class AnalystAgent:
    @staticmethod
    async def generate_market_pulse(brand_id: int, session=None) -> str:
        """
        Synthesizes recent market events into a strategic summary and calculates velocity.
        """
        should_close = False
        if session is None:
            session = get_session()
            should_close = True

        try:
            brand = session.get(Brand, brand_id)
            if not brand:
                return "Brand not found."

            # 1. Calculate Velocity Metrics
            seven_days_ago = datetime.now(UTC) - timedelta(days=7)
            recent_ads_count = session.query(ExtractedAd).filter(
                ExtractedAd.brand_id == brand_id,
                ExtractedAd.last_seen >= seven_days_ago
            ).count()

            creative_velocity = recent_ads_count / 7.0

            recent_shifts = session.query(MarketEvent).filter(
                MarketEvent.brand_id == brand_id,
                MarketEvent.event_type == "Offer Shift",
                MarketEvent.timestamp >= seven_days_ago
            ).count()
            offer_velocity = recent_shifts / 7.0

            # Update Competitor Profile
            profile = session.query(CompetitorProfile).filter_by(brand_name=brand.name).first()
            if profile:
                profile.market_velocity = creative_velocity + (offer_velocity * 10)

            # 2. Fetch recent events
            fourteen_days_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
            events = session.query(MarketEvent).filter(
                MarketEvent.brand_id == brand_id,
                MarketEvent.timestamp >= fourteen_days_ago
            ).order_by(MarketEvent.timestamp.desc()).all()

            event_summary = "\n".join([
                f"- [{e.timestamp.strftime('%Y-%m-%d')}] {e.event_type}: {e.description}"
                for e in events
            ])

            # 3. AI Synthesis
            prompt = f"""
            SYSTEM: Senior Market Intelligence Analyst.
            TASK: Market Pulse for {brand.name}.
            METRICS: Creative Velocity: {creative_velocity}/day, Offer Velocity: {offer_velocity}/day.

            RECENT DATA LOG:
            {event_summary}
            """

            res = await analyze_ads_with_ai([{"text": prompt}])
            return res
        except Exception as e:
            logger.error(f"Error in AnalystAgent: {e}")
            return f"Error: {e}"
        finally:
            if should_close:
                session.close()

class MarketAnalystAgent(AnalystAgent):
    pass
