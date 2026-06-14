import logging
from sqlalchemy.orm import Session
from app.models.models import Watchlist, ExtractedAd, MarketEvent, AuditLog
from datetime import datetime, UTC

logger = logging.getLogger("AdSpyAgent.AlertEngine")

class AlertEngine:
    @staticmethod
    def process_alerts(session: Session):
        """
        Scans recent data against all active watchlists and triggers alerts.
        """
        watchlists = session.query(Watchlist).all()

        for watch in watchlists:
            # 1. New Winner Alert
            if watch.brand_id:
                new_winner = session.query(ExtractedAd).filter(
                    ExtractedAd.brand_id == watch.brand_id,
                    ExtractedAd.winner_score >= watch.alert_threshold,
                    ExtractedAd.needs_review == False # Assume processed
                ).first()

                if new_winner:
                    AlertEngine.trigger_alert(watch.org_id, f"WINNER: {new_winner.brand.name} launched a high-score ad!", session)

            # 2. Offer Change Alert
            if watch.brand_id:
                event = session.query(MarketEvent).filter(
                    MarketEvent.brand_id == watch.brand_id,
                    MarketEvent.event_type == "Price Change"
                ).order_by(MarketEvent.timestamp.desc()).first()

                if event and (datetime.now(UTC) - event.timestamp.replace(tzinfo=UTC)).seconds < 3600:
                    AlertEngine.trigger_alert(watch.org_id, f"OFFER: {event.brand.name} changed their pricing!", session)

    @staticmethod
    def trigger_alert(org_id: int, message: str, session: Session):
        logger.warning(f"ALERT for Org {org_id}: {message}")
        # Logic to send email/webhook/push
        log = AuditLog(org_id=org_id, action="ALERT_TRIGGERED", details=message)
        session.add(log)
        session.commit()
