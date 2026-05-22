import logging
from datetime import datetime, UTC, timedelta
from app.db.database import get_session
from app.models.models import Brand, TrendSnapshot, ExtractedAd
from sqlalchemy import func

logger = logging.getLogger("AdSpyAgent.Market")

class MarketAgent:
    @staticmethod
    def analyze_trends(brand_id: int, session=None):
        _session = session or get_session()
        try:
            brand = _session.get(Brand, brand_id)
            if not brand: return

            now = datetime.now(UTC).replace(tzinfo=None)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # 1. Ad Volume Analysis
            total_ads = session.query(ExtractedAd).filter(ExtractedAd.brand_id == brand_id).count()

            # Simple simulation of "new ads" for the snapshot
            new_ads = session.query(ExtractedAd).filter(
                ExtractedAd.brand_id == brand_id,
                ExtractedAd.last_seen >= today_start
            ).count()

            # 2. Create Snapshot
            snapshot = TrendSnapshot(
                brand_id=brand_id,
                date=now,
                ad_count=total_ads,
                new_ads_count=new_ads
            )
            session.add(snapshot)

            # 3. Detect Velocity (Aggression Alert)
            if new_ads > 10:
                logger.info(f"High Aggression detected for brand {brand.name}: {new_ads} new ads.")
                # Could trigger AlertAgent here

            if not session:
                _session.commit()
        except Exception as e:
            logger.error(f"Market Analysis failed for brand {brand_id}: {e}")
        finally:
            if not session:
                _session.close()
