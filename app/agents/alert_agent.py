import logging
import subprocess
import sys
import os
from app.db.database import get_session
from app.models.models import Brand

logger = logging.getLogger("AdSpyAgent.Alert")

class AlertAgent:
    @staticmethod
    def trigger_winning_asset_alert(brand_id: int):
        session = get_session()
        brand = session.get(Brand, brand_id)
        if not brand:
            session.close()
            return

        logger.info(f"Triggering Winning Asset Alert for {brand.name}")

        # WhatsApp Integration (Existing logic refactored)
        phone = os.getenv("ALERT_PHONE")
        chrome_dir = os.getenv("CHROME_USER_DATA_PATH")

        if phone:
            try:
                subprocess.Popen([sys.executable, "whatsapp_automation.py", phone, chrome_dir or ""])
            except Exception as e:
                logger.error(f"Failed to launch WhatsApp alert: {e}")

        session.close()

    @staticmethod
    def trigger_market_shift_alert(brand_id: int, message: str):
        logger.warning(f"MARKET SHIFT: Brand {brand_id} - {message}")
        # Could send Email/Slack here
