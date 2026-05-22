import asyncio
import logging
from unittest.mock import patch
from app.agents.ai_agent import analyze_ads_with_ai
from app.orchestrator.engine import IntelligenceOrchestrator
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChaosTest")

async def simulate_gemini_down():
    logger.info("TEST: Simulating Gemini API failure...")
    session = get_session()
    run = ScrapeRun(query="chaos_brand", status="PENDING")
    session.add(run)
    session.commit()

    ad = ExtractedAd(run_id=run.id, ad_text="chaos ad", launch_date="2023", media_links="link", content_hash="chash")
    session.add(ad)
    session.commit()

    orch = IntelligenceOrchestrator(run.id)

    with patch("app.agents.ai_agent.aiohttp.ClientSession.post") as mock_post:
        # Mock a 500 error
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = asyncio.Future()
        mock_response.text.set_result("Internal Server Error")
        mock_post.return_value.__aenter__.return_value = mock_response

        # The orchestrator should handle the failure without crashing the whole process
        try:
            await orch.execute_pipeline()
            logger.info("RESULT: System survived Gemini failure (Graceful degradation).")
        except Exception as e:
            logger.error(f"RESULT: System crashed on Gemini failure: {e}")

    session.close()

async def simulate_db_disconnect():
    logger.info("TEST: DB disconnect simulation would happen at the session layer...")
    # This usually requires a lower-level proxy or patching get_session to raise OperationalError
    pass

if __name__ == "__main__":
    from unittest.mock import MagicMock
    asyncio.run(simulate_gemini_down())
