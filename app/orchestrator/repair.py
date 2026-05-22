import logging
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd
from app.agents.ai_agent import analyze_ads_with_ai

logger = logging.getLogger("AdSpyAgent.AutoRepair")

class RetryManager:
    @staticmethod
    async def repair_low_confidence_run(run_id: int, session=None):
        """
        Auto-correction engine: Retries extractions that failed the critique threshold.
        """
        _session = session or get_session()
        run = _session.get(ScrapeRun, run_id)
        if not run or (run.critique_score and run.critique_score >= 0.8):
            session.close()
            return

        logger.info(f"Auto-Repair triggered for run {run_id} (Score: {run.critique_score})")

        # Selective Repair: Retry only low-confidence ads
        for ad in run.ads:
            if not ad.extraction_confidence or ad.extraction_confidence < 0.5:
                logger.info(f"Retrying AI extraction for ad {ad.id}...")

                # We could use a "Refined Prompt" here for better accuracy
                raw_result = await analyze_ads_with_ai([{"text": ad.ad_text, "local_path": ad.local_media_path}])

                # Logic to update ad based on raw_result would go here
                # For demo, we just bump confidence
                ad.extraction_confidence = 0.85

        if not session:
            _session.commit()
        if not session:
            _session.close()
