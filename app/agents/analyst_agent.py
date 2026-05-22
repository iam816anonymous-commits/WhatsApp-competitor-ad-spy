import logging
from datetime import datetime, UTC, timedelta
from app.db.database import get_session
from app.models.models import Brand, MarketEvent
from app.agents.ai_agent import analyze_ads_with_ai

logger = logging.getLogger("AdSpyAgent.Analyst")

class MarketAnalystAgent:
    @staticmethod
    async def generate_market_pulse(brand_id: int) -> str:
        """
        Synthesizes recent market events into a strategic summary.
        """
        session = get_session()
        try:
            brand = session.get(Brand, brand_id)
            if not brand:
                return "Brand not found."

            # 1. Fetch recent events (last 14 days for more context)
            fourteen_days_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
            events = session.query(MarketEvent).filter(
                MarketEvent.brand_id == brand_id,
                MarketEvent.timestamp >= fourteen_days_ago
            ).order_by(MarketEvent.timestamp.desc()).all()

            if not events:
                return f"No recent market events recorded for {brand.name} in the last 14 days."

            event_summary = "\n".join([
                f"- [{e.timestamp.strftime('%Y-%m-%d')}] {e.event_type}: {e.description}"
                for e in events
            ])

            # 2. Ask Gemini to synthesize
            prompt = f"""
            SYSTEM: You are a Senior Market Intelligence Analyst.
            TASK: Synthesize a 'Market Pulse' report for the brand: {brand.name}.

            RECENT DATA LOG:
            {event_summary}

            ANALYTICAL REQUIREMENTS:
            1. MOMENTUM: Is this brand scaling or retracting based on event frequency?
            2. STRATEGY SHIFTS: Identify changes in their offer stack or hook patterns.
            3. COMPETITIVE THREAT: Rate their current market aggression (1-10).
            4. ACTIONABLE INSIGHT: What should a competitor do in response to these moves?

            Format the response in professional markdown with clear sections.
            """

            # Use the AI agent. We pass a mock "ad" object that contains our prompt.
            # analyze_ads_with_ai expects a list of dicts.
            res = await analyze_ads_with_ai([{"text": prompt}])

            return res
        except Exception as e:
            logger.error(f"Error generating market pulse: {e}")
            return f"Error generating market pulse: {str(e)}"
        finally:
            session.close()
