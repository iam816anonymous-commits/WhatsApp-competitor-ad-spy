import logging
from datetime import datetime, UTC, timedelta
from sqlalchemy import func
from app.db.database import get_session
from app.models.models import ExtractedAd, CreativeCluster, LandingPage

logger = logging.getLogger("AdSpyAgent.WinnerEngine")

class WinnerEngine:
    @staticmethod
    def calculate_winner_score(ad: ExtractedAd) -> float:
        """
        Calculates a score from 0-100 based on ad longevity and creative reuse.
        Formula: (Longevity * 0.4) + (CreativeReuse * 0.4) + (PlatformEngagement * 0.2)
        """
        try:
            # 1. Longevity Score (max 40 pts)
            launch_dt = datetime.strptime(ad.launch_date, "%Y-%m-%d").replace(tzinfo=UTC)
            days_active = (datetime.now(UTC) - launch_dt).days
            # Assume 90 days active is a 100% longevity score
            longevity_score = min(days_active / 90.0, 1.0) * 40

            # 2. Creative Reuse Score (max 40 pts)
            # Placeholder: In a real system, this would query Cluster size
            # If ad belongs to a cluster with many ads, it's a "winning" creative
            reuse_score = 0
            if ad.cluster_id:
                # Mock logic for now
                reuse_score = 20 # Assume some reuse

            # 3. Platform Engagement Score (max 20 pts)
            # Placeholder: Based on views/likes if available
            engagement_score = 10

            return min(longevity_score + reuse_score + engagement_score, 100.0)
        except Exception as e:
            logger.error(f"Error calculating winner score: {e}")
            return 0.0

class EmergingEngine:
    @staticmethod
    def detect_emerging_winners(session=None):
        """
        Identifies ads that are rapidly gaining traction (velocity).
        """
        should_close = False
        if session is None:
            session = get_session()
            should_close = True

        try:
            # Logic: Ads launched in the last 7 days with high initial engagement or
            # appearing across multiple brand accounts (creative sprawl).
            seven_days_ago = datetime.now(UTC) - timedelta(days=7)

            # Simple implementation: find ads launched recently
            recent_ads = session.query(ExtractedAd).filter(
                ExtractedAd.launch_date >= seven_days_ago.strftime("%Y-%m-%d"),
                ExtractedAd.is_emerging == False
            ).all()

            for ad in recent_ads:
                # Criteria: launched in last 7 days + specific text patterns or high engagement
                if "OFFER" in ad.ad_text.upper() or "SALE" in ad.ad_text.upper():
                    ad.is_emerging = True
                    ad.winner_confidence = 0.65

            session.commit()
        except Exception as e:
            logger.error(f"Error detecting emerging winners: {e}")
        finally:
            if should_close:
                session.close()

class FamilyTreeEngine:
    @staticmethod
    def identify_creative_clones(session=None):
        """
        Uses pHash similarity to link ads back to an 'original' creative.
        """
        should_close = False
        if session is None:
            session = get_session()
            should_close = True

        try:
            # 1. Find ads with phash but no original_ad_id
            target_ads = session.query(ExtractedAd).filter(
                ExtractedAd.phash != None,
                ExtractedAd.original_ad_id == None
            ).all()

            for ad in target_ads:
                # 2. Look for an earlier ad with the same or similar phash
                # Simple implementation: exact phash match for now
                earlier_ad = session.query(ExtractedAd).filter(
                    ExtractedAd.phash == ad.phash,
                    ExtractedAd.id != ad.id,
                    ExtractedAd.launch_date <= ad.launch_date
                ).order_by(ExtractedAd.launch_date.asc()).first()

                if earlier_ad and earlier_ad.id != ad.id:
                    ad.original_ad_id = earlier_ad.id
                    logger.info(f"Linked ad {ad.id} to original {earlier_ad.id} via phash")

            session.commit()
        except Exception as e:
            logger.error(f"Error identifying clones: {e}")
        finally:
            if should_close:
                session.close()
