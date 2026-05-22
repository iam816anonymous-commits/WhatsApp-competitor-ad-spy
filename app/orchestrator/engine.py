import logging
import json
import re
from typing import List, Dict, Any
from app.agents.ai_agent import analyze_ads_with_ai
from app.agents.vision_agent import generate_image_embedding
from app.db.database import get_session
from app.models.models import ScrapeRun, ExtractedAd, Brand, Campaign, Offer, LandingPage
from app.utils.media import resolve_redirects

logger = logging.getLogger("AdSpyAgent.Orchestrator")

class IntelligenceOrchestrator:
    def __init__(self, run_id: int):
        self.run_id = run_id

    async def execute_pipeline(self):
        """
        Execution Graph:
        Collector (already done by Scraper)
        ↓
        Normalizer (Links & Brands)
        ↓
        Vision Agent (Embeddings)
        ↓
        Strategy Agent (AI Analysis)
        ↓
        Market Intelligence Agent (Trend Analysis - Next Step)
        ↓
        Alert Engine (Notifications - Next Step)
        """
        session = get_session()
        run = session.get(ScrapeRun, self.run_id)
        if not run:
            session.close()
            return

        logger.info(f"Orchestrating pipeline for run {self.run_id} ({run.query})")

        # 1. Normalization & Pre-processing
        brand_name = run.query.lower().strip()
        brand = session.query(Brand).filter_by(name=brand_name).first()
        if not brand:
            brand = Brand(name=brand_name)
            session.add(brand)
            session.flush()

        # 2. Vision & Link Resolution (Enhanced Normalization)
        for ad in run.ads:
            ad.brand_id = brand.id

            # Resolve Redirects if not done
            if ad.final_destination_url and ("fb.me" in ad.final_destination_url or "l.php" in ad.final_destination_url):
                 ad.final_destination_url = await resolve_redirects(ad.final_destination_url)

            # Generate Embeddings if not done
            if ad.local_media_path and not ad.creative_embedding:
                ad.creative_embedding = generate_image_embedding(ad.local_media_path)

            # Associate Landing Page & Crawl
            if ad.final_destination_url:
                lp = session.query(LandingPage).filter_by(url=ad.final_destination_url).first()
                if not lp:
                    lp = LandingPage(url=ad.final_destination_url)
                    session.add(lp)
                    session.flush()

                    # Async Crawl
                    from app.scrapers.landing_page import LandingPageCrawler
                    crawl_data = await LandingPageCrawler.crawl(ad.final_destination_url)
                    lp.headline = crawl_data.get("headline")
                    lp.cta_text = crawl_data.get("cta_text")
                    lp.pixels_detected = crawl_data.get("pixels")

                ad.landing_page_id = lp.id

        session.commit()

        # 3. Strategy Analysis
        run_ads_data = [
            {
                "text": ad.ad_text,
                "local_path": ad.local_media_path,
                "destination_url": ad.final_destination_url
            } for ad in run.ads
        ]

        if run_ads_data:
            logger.info("Executing Strategy Agent...")
            raw_result = await analyze_ads_with_ai(run_ads_data)
            await self._process_ai_result(session, run, raw_result)

        # 4. Market & Alerting
        logger.info("Executing Market Intelligence Agent...")
        from app.agents.market_agent import MarketAgent
        MarketAgent.analyze_trends(brand.id)

        # Check for winners to alert
        from app.agents.alert_agent import AlertAgent
        # Logic: If any ad in this run has longevity > 21 days
        for ad in run.ads:
             from app.utils.analytics import get_ad_longevity_category
             status, _ = get_ad_longevity_category(ad.launch_date)
             if status == "Winning Core Asset":
                  AlertAgent.trigger_winning_asset_alert(brand.id)
                  break

        session.commit()
        session.close()

    async def _process_ai_result(self, session, run, raw_result):
        try:
            clean_json = re.sub(r'```json\n?|\n?```', '', raw_result).strip()
            data = json.loads(clean_json)

            run.analysis_text = data.get("analysis_text", raw_result)
            run.cta_type = data.get("cta_type")
            run.emotion = data.get("emotion")
            run.offer_type = data.get("offer_type")
            run.urgency_score = data.get("urgency_score")
            run.persona = data.get("persona")

            # Map Offer if identified
            offer_name = data.get("offer_type")
            if offer_name:
                offer = session.query(Offer).filter_by(brand_id=run.ads[0].brand_id, name=offer_name).first()
                if not offer:
                    offer = Offer(brand_id=run.ads[0].brand_id, name=offer_name, type=offer_name)
                    session.add(offer)
                    session.flush()
                for ad in run.ads:
                    ad.offer_id = offer.id

            # Update Ads
            for ad in run.ads:
                ad.funnel_type = data.get("funnel_type")
                ad.headline = data.get("headline")

        except Exception as e:
            logger.error(f"Failed to process AI JSON in orchestrator: {e}")
            run.analysis_text = raw_result
