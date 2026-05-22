from datetime import datetime, UTC
from typing import Tuple

def get_ad_longevity_category(launch_date_str: str) -> Tuple[str, int]:
    try:
        # Meta format is often "May 22, 2024"
        launch_date = datetime.strptime(launch_date_str, "%b %d, %Y")
        days = (datetime.now(UTC).replace(tzinfo=None) - launch_date).days
        if days > 21:
            return "Winning Core Asset", days
        elif days > 7:
            return "Scaling", days
        else:
            return "Testing Phase", days
    except Exception:
        return "Unknown", 0
