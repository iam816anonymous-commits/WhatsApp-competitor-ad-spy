import logging
from datetime import datetime, UTC
from app.db.database import get_session
from app.models.models import Organization, OrganizationUsage

logger = logging.getLogger("AdSpyAgent.CostAudit")

# Cost Constants
COST_CRAWL = 0.01 # per brand scrape
COST_IMAGE_EMBED = 0.0001
COST_GEMINI_TOKEN = 0.0000005 # $0.50 per million

class CostAudit:
    @staticmethod
    def run_simulation(brands=100, creatives_per_brand=50, days=30):
        total_brands = brands
        total_creatives = brands * creatives_per_brand
        total_scrapes = brands * days

        # 1. Scraping Cost
        crawl_cost = total_scrapes * COST_CRAWL

        # 2. Embedding Cost
        embedding_cost = total_creatives * COST_IMAGE_EMBED

        # 3. AI Inference (Assuming 2000 tokens per ad average)
        token_cost = (total_creatives * 2000) * COST_GEMINI_TOKEN

        total_monthly = crawl_cost + embedding_cost + token_cost

        report = {
            "simulation_params": {
                "brands": brands,
                "creatives": total_creatives,
                "days": days
            },
            "costs": {
                "crawling_usd": crawl_cost,
                "embedding_usd": embedding_cost,
                "inference_usd": token_cost,
                "total_monthly_usd": total_monthly
            },
            "per_brand_monthly": total_monthly / brands
        }
        return report

if __name__ == "__main__":
    audit = CostAudit.run_simulation()
    print("--- Enterprise Cost Audit Report ---")
    import json
    print(json.dumps(audit, indent=2))
