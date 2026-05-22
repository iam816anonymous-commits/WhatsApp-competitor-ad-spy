import logging
from typing import Dict

logger = logging.getLogger("AdSpyAgent.CostTracker")

# Enterprise tier cost tracking (estimated)
COST_PER_1K_TOKENS = 0.0005
COST_PER_EMBEDDING = 0.0001

class CostTracker:
    total_cost: float = 0.0

    @classmethod
    def log_inference(cls, tokens: int):
        cost = (tokens / 1000) * COST_PER_1K_TOKENS
        cls.total_cost += cost
        logger.info(f"AI Inference: {tokens} tokens (~${cost:.5f}). Total: ${cls.total_cost:.5f}")

    @classmethod
    def log_embedding(cls):
        cls.total_cost += COST_PER_EMBEDDING
        logger.info(f"Embedding generated (~${COST_PER_EMBEDDING:.5f}). Total: ${cls.total_cost:.5f}")

    @classmethod
    def get_summary(cls) -> Dict:
        return {"total_usd": cls.total_cost}
