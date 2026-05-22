import logging
import random
from typing import Dict
from app.db.database import get_session
from app.models.models import ExtractedAd

logger = logging.getLogger("AdSpyAgent.Prediction")

class PredictionAgent:
    @staticmethod
    def forecast_ad_performance(ad_id: int) -> Dict:
        """
        Forecasting model for ad performance.
        In production, this would be a trained XGBoost or LLM-based evaluator.
        """
        session = get_session()
        ad = session.get(ExtractedAd, ad_id)
        if not ad:
            session.close()
            return {}

        # Heuristic-based forecasting
        text_len = len(ad.ad_text)
        has_media = 1 if ad.local_media_path else 0

        # Simulation: Higher probability for ads with media and medium length text
        base_prob = 0.5 + (0.2 * has_media)
        if 100 < text_len < 500:
            base_prob += 0.15

        # Creative fatigue estimation
        # Simulates that typical creatives start fatiguing after 14-30 days
        fatigue = random.randint(14, 30)

        ad.winner_probability = min(base_prob + random.uniform(-0.05, 0.05), 0.99)
        ad.fatigue_days = fatigue

        session.commit()
        res = {"probability": ad.winner_probability, "fatigue": fatigue}
        session.close()
        return res

    @staticmethod
    def detect_offer_shift(brand_id: int, new_offer_type: str) -> bool:
        # Placeholder for complex offer shift detection
        return True
