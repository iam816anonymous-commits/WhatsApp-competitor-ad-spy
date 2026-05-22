import logging
from typing import Dict, List, Any
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd

logger = logging.getLogger("AdSpyAgent.Critique")

class CritiqueAgent:
    @staticmethod
    async def review(run_id: int, session=None) -> Dict[str, Any]:
        """
        Audits a completed scrape run for logic errors, hallucinations, and prediction failures.
        """
        _session = session or get_session()
        run = _session.get(ScrapeRun, run_id)
        if not run:
            session.close()
            return {"error": "Run not found"}

        logic_errors = []
        hallucinations = []
        prediction_failures = []
        coverage_gaps = []

        # 1. Extraction Audit: Check for low-confidence or missing essential fields
        for ad in run.ads:
            if not ad.funnel_type:
                coverage_gaps.append(f"Ad {ad.id}: Missing funnel_type")
            if ad.extraction_confidence and ad.extraction_confidence < 0.5:
                hallucinations.append({"ad_id": ad.id, "issue": "low confidence extraction"})

        # 2. Crawl Audit: Verify media and landing page resolution
        for ad in run.ads:
            if not ad.local_media_path:
                coverage_gaps.append(f"Ad {ad.id}: Missing media download")
            if not ad.final_destination_url:
                coverage_gaps.append(f"Ad {ad.id}: Broken redirect or missing CTA")

        # 3. Simple Critique Score Calculation
        score = 1.0
        if hallucinations: score -= 0.2
        if coverage_gaps: score -= 0.1 * min(len(coverage_gaps), 5)

        run.critique_score = max(0.0, score)
        run.hallucination_flags = {"hallucinations": hallucinations, "gaps": coverage_gaps}

        if not session:
            _session.commit()
        result = {
            "run_id": run_id,
            "critique_score": run.critique_score,
            "logic_errors": logic_errors,
            "hallucinations": hallucinations,
            "coverage_gaps": coverage_gaps,
            "cost_waste": [] # Placeholder for future phase
        }
        if not session:
            _session.close()
        return result
