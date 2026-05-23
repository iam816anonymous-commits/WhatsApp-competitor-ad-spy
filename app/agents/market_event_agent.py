import logging
from sqlalchemy.orm import Session
from app.models.models import Brand, MarketEvent, Product, ExtractedAd
from datetime import datetime, UTC, timedelta

logger = logging.getLogger("AdSpyAgent.MarketEvent")

class MarketEventAgent:
    @staticmethod
    def detect_events(brand_id: int, session: Session):
        """
        Analyzes recent data to detect market events.
        """
        brand = session.get(Brand, brand_id)
        if not brand: return

        logger.info(f"Analyzing market events for {brand.name}...")

        # 1. Detect Price Changes
        products = session.query(Product).filter_by(brand_id=brand_id).all()
        for p in products:
            if p.price_history and len(p.price_history) >= 2:
                # Sort history keys (timestamps)
                sorted_keys = sorted(p.price_history.keys())
                last_val = p.price_history[sorted_keys[-1]]
                prev_val = p.price_history[sorted_keys[-2]]

                if abs(last_val - prev_val) > 0.01:
                    event = MarketEvent(
                        brand_id=brand_id,
                        event_type="Price Change",
                        description=f"Price of {p.name} changed from {prev_val} to {last_val} on {p.source}",
                        old_value=str(prev_val),
                        new_value=str(last_val),
                        confidence=1.0
                    )
                    session.add(event)

        # 2. Detect New Collections (Via Ad Text or Product Names)
        # Look for keywords like "Collection", "Drop", "Launched" in ads from the last 24h
        recent_threshold = datetime.now(UTC) - timedelta(days=1)
        new_ads = session.query(ExtractedAd).filter(
            ExtractedAd.brand_id == brand_id,
            ExtractedAd.last_seen >= recent_threshold
        ).all()

        for ad in new_ads:
            if "collection" in ad.ad_text.lower() or "new drop" in ad.ad_text.lower():
                # Avoid duplicate events for same collection in same day
                existing = session.query(MarketEvent).filter(
                    MarketEvent.brand_id == brand_id,
                    MarketEvent.event_type == "New Collection",
                    MarketEvent.timestamp >= recent_threshold
                ).first()

                if not existing:
                    event = MarketEvent(
                        brand_id=brand_id,
                        event_type="New Collection",
                        description=f"New collection detected in ad: {ad.ad_text[:50]}...",
                        confidence=0.85
                    )
                    session.add(event)

        session.commit()
