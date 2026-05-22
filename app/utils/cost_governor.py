import logging
from datetime import datetime, UTC
from typing import Dict
from app.db.database import get_session
from app.models.models import Organization, OrganizationUsage

logger = logging.getLogger("AdSpyAgent.CostGovernor")

# Enterprise tier cost tracking (estimated)
COST_PER_1K_TOKENS = 0.0005
COST_PER_EMBEDDING = 0.0001

class CostGovernor:
    """
    Manages budget tracking and hard-stops for Organizations.
    """

    @classmethod
    def check_budget(cls, org_id: int) -> bool:
        """
        Returns True if the organization is within its budget.
        """
        session = get_session()
        try:
            org = session.get(Organization, org_id)
            if not org:
                return False

            month = datetime.now(UTC).strftime("%Y-%m")
            usage = session.query(OrganizationUsage).filter_by(org_id=org_id, month=month).first()

            if not usage:
                return True # No usage yet

            if usage.total_spend >= org.monthly_budget:
                logger.warning(f"Org {org_id} has exceeded budget! Spend: {usage.total_spend}, Limit: {org.monthly_budget}")
                return False

            return True
        finally:
            session.close()

    @classmethod
    def log_spend(cls, org_id: int, tokens: int = 0, embeddings: int = 0):
        """
        Updates the organization's monthly spend.
        """
        cost = (tokens / 1000) * COST_PER_1K_TOKENS + (embeddings * COST_PER_EMBEDDING)

        session = get_session()
        try:
            month = datetime.now(UTC).strftime("%Y-%m")
            usage = session.query(OrganizationUsage).filter_by(org_id=org_id, month=month).first()

            if not usage:
                usage = OrganizationUsage(org_id=org_id, month=month, total_spend=0.0)
                session.add(usage)

            usage.total_spend += cost
            session.commit()
            logger.info(f"Logged ${cost:.5f} spend for Org {org_id}. Monthly Total: ${usage.total_spend:.5f}")
        except Exception as e:
            logger.error(f"Failed to log spend: {e}")
            session.rollback()
        finally:
            session.close()
