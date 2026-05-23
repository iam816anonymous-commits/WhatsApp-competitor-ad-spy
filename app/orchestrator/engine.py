import logging
import json
import re
from typing import List, Dict, Any
from datetime import datetime, UTC
from app.agents.ai_agent import analyze_ads_with_ai
from app.agents.vision_agent import generate_image_embedding
from app.agents.prediction_agent import PredictionAgent
from app.db.database import get_session
from app.db.tenant_context import get_tenant
from app.models.models import ScrapeRun, ExtractedAd, Brand, Campaign, Offer, LandingPage, MarketEvent, Persona, Hook, CompetitorProfile
from app.utils.media import resolve_redirects
from app.utils.fingerprint import get_creative_fingerprint

logger = logging.getLogger("AdSpyAgent.Orchestrator")

class IntelligenceOrchestrator:
    def __init__(self, run_id: int):
        self.run_id = run_id

    def _calculate_quality_score(self, ad: ExtractedAd) -> float:
        score = 0.0
        if ad.ad_text and len(ad.ad_text) > 10: score += 0.25
        if ad.creative_embedding: score += 0.25
        if ad.final_destination_url: score += 0.25
        if ad.landing_page_id:
            score += 0.25
        return score

    async def execute_pipeline(self):
        org_id = get_tenant()
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
        Market Intelligence Agent (Trend Analysis)
        ↓
        Alert Engine (Notifications)
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

                    # Async Crawl (Phase 5 - use new scraper)
                    from app.scrapers.landing_page_scraper import LandingPageScraper
                    crawl_data = await LandingPageScraper.analyze_url(ad.final_destination_url)
                    lp.headline = crawl_data.get("headline")
                    lp.cta_text = crawl_data.get("cta_text")
                    lp.pixels_detected = crawl_data.get("pixels_detected")
                    lp.pricing = crawl_data.get("pricing")
                    lp.email_capture_detected = crawl_data.get("email_capture_detected")
                    lp.has_checkout = crawl_data.get("has_checkout")

                ad.landing_page_id = lp.id

            # Phase 5: Fingerprinting
            if ad.local_media_path and not ad.phash:
                fp = get_creative_fingerprint(ad.local_media_path)
                if fp:
                    ad.phash = fp["phash"]
                    ad.dominant_colors = fp["dominant_colors"]

            ad.quality_score = self._calculate_quality_score(ad)

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
        MarketAgent.analyze_trends(brand.id, session=session)

        # Phase 3: Market Event Agent
        logger.info("Executing Market Event Agent...")
        from app.agents.market_event_agent import MarketEventAgent
        MarketEventAgent.detect_events(brand.id, session=session)

        # Phase 9: Analyst Agent
        logger.info("Executing Analyst Agent...")
        from app.agents.analyst_agent import AnalystAgent
        await AnalystAgent.generate_market_pulse(brand.id, session=session)

        # Phase 5: Competitor Profile Update
        profile = session.query(CompetitorProfile).filter_by(brand_name=run.query).first()
        if not profile:
            profile = CompetitorProfile(
                brand_name=run.query,
                creative_count=0,
                offer_shift_count=0,
                market_velocity=0.0
            )
            session.add(profile)

        profile.last_seen = datetime.now(UTC)
        profile.creative_count = (profile.creative_count or 0) + len(run.ads)
        if run.offer_type: profile.offer_shift_count += 1

        # 5. Prediction Engine
        logger.info("Executing Prediction Agent...")
        try:
            for ad in run.ads:
                PredictionAgent.forecast_ad_performance(ad.id, session=session)
        except Exception as e:
            logger.error(f"Prediction Engine failed: {e}")

        # 6. Post-Run Critique & Auto-Repair
        logger.info("Executing Critique Layer...")
        try:
            from app.agents.critique_agent import CritiqueAgent
            await CritiqueAgent.review(self.run_id, session=session)

            from app.orchestrator.repair import RetryManager
            await RetryManager.repair_low_confidence_run(self.run_id, session=session)
        except Exception as e:
            logger.error(f"Critique/Repair Layer failed: {e}")

        # Check for winners to alert
        from app.agents.alert_agent import AlertAgent
        # Logic: If any ad in this run has longevity > 21 days
        for ad in run.ads:
             from app.utils.analytics import get_ad_longevity_category
             status, _ = get_ad_longevity_category(ad.launch_date)
             if status == "Winning Core Asset":
                  AlertAgent.trigger_winning_asset_alert(brand.id)
                  break

        # Ensure MediaResolver is closed
        from app.utils.media import MediaResolver
        await MediaResolver.close()

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

            brand_id = run.ads[0].brand_id if run.ads else None

            # 1. Map Offer & Detect Shifts
            offer_type = data.get("offer_type")
            if offer_type and brand_id:
                existing_active_offer = session.query(Offer).filter_by(brand_id=brand_id, is_active=1).first()

                if not existing_active_offer or existing_active_offer.type != offer_type:
                    # Log Market Event: Offer Shift
                    event = MarketEvent(
                        brand_id=brand_id,
                        event_type="Offer Shift",
                        description=f"Brand shifted offer strategy to {offer_type}",
                        old_value=existing_active_offer.type if existing_active_offer else "None",
                        new_value=offer_type,
                        confidence=0.92
                    )
                    session.add(event)

                    if existing_active_offer: existing_active_offer.is_active = 0

                    new_offer = Offer(brand_id=brand_id, name=offer_type, type=offer_type, is_active=1)
                    session.add(new_offer)
                    session.flush()
                    for ad in run.ads: ad.offer_id = new_offer.id
                else:
                    for ad in run.ads: ad.offer_id = existing_active_offer.id

            # 2. Map Persona
            persona_name = data.get("persona")
            if persona_name and brand_id:
                persona = session.query(Persona).filter_by(brand_id=brand_id, name=persona_name).first()
                if not persona:
                    persona = Persona(brand_id=brand_id, name=persona_name)
                    session.add(persona)
                    session.flush()
                for ad in run.ads: ad.persona_id = persona.id

            # 3. Map Hook
            hook_text = data.get("headline") or "Generic Hook"
            if hook_text and brand_id:
                hook = session.query(Hook).filter_by(brand_id=brand_id, text=hook_text).first()
                if not hook:
                    hook = Hook(brand_id=brand_id, text=hook_text, type=data.get("hook_type"))
                    session.add(hook)
                    session.flush()
                for ad in run.ads: ad.hook_id = hook.id

            # Update Ads
            for ad in run.ads:
                ad.funnel_type = data.get("funnel_type")
                ad.headline = data.get("headline")

        except Exception as e:
            logger.error(f"Failed to process AI JSON in orchestrator: {e}")
            run.analysis_text = raw_result
