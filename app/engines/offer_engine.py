import logging
from sqlalchemy.orm import Session
from app.models.models import ExtractedAd, LandingPage, Offer
import re

logger = logging.getLogger("AdSpyAgent.OfferEngine")

class OfferEngine:
    @staticmethod
    def extract_offer_details(ad: ExtractedAd, lp: LandingPage = None):
        """
        Parses ad text and landing page content to identify the core offer.
        Example: 'BOGO', '50% Off', 'Free Shipping'.
        """
        text = ad.ad_text or ""
        if lp and lp.headline:
            text += " " + lp.headline

        # 1. Look for percentage discounts
        pct_match = re.search(r'(\d+)%\s*(off|discount)', text, re.IGNORECASE)
        if pct_match:
            return f"{pct_match.group(1)}% Off"

        # 2. Look for BOGO
        if re.search(r'bogo|buy one get one', text, re.IGNORECASE):
            return "BOGO"

        # 3. Look for Free Shipping
        if re.search(r'free shipping', text, re.IGNORECASE):
            return "Free Shipping"

        # 4. Look for flat discounts
        flat_match = re.search(r'off\s*(?:of\s*)?\$(\d+)', text, re.IGNORECASE)
        if flat_match:
            return f"${flat_match.group(1)} Off"

        return "Standard Price"

    @staticmethod
    def link_ad_to_offer(ad: ExtractedAd, session: Session):
        """
        Ensures the ad is linked to an Offer record in the DB.
        """
        offer_text = OfferEngine.extract_offer_details(ad)

        # Find or create offer
        offer = session.query(Offer).filter_by(
            brand_id=ad.brand_id,
            name=offer_text
        ).first()

        if not offer:
            offer = Offer(
                brand_id=ad.brand_id,
                name=offer_text,
                type="Discount" if "Off" in offer_text or "BOGO" in offer_text else "Standard"
            )
            session.add(offer)
            session.flush()

        ad.offer_id = offer.id
        # ad.offer = offer_text # Removed as it conflicts with relationship if not careful
