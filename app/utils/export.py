import pandas as pd
from sqlalchemy import desc
from app.db.database import get_session
from app.models.models import ExtractedAd, CompetitorProfile
import io

class ExportEngine:
    @staticmethod
    def generate_market_pulse_xlsx():
        """
        Generates an XLSX report with multiple sheets for Market Intelligence.
        """
        session = get_session()

        # 1. Competitor Profiles
        profiles = session.query(CompetitorProfile).all()
        df_profiles = pd.DataFrame([{
            "Brand": p.brand_name,
            "First Seen": p.first_seen.strftime('%Y-%m-%d'),
            "Last Seen": p.last_seen.strftime('%Y-%m-%d'),
            "Offer Shifts": p.offer_shift_count,
            "Creative Count": p.creative_count,
            "Dominant Hook": p.dominant_hook,
            "Velocity": p.market_velocity
        } for p in profiles])

        # 2. Winning Assets (based on highest longevity or quality)
        ads = session.query(ExtractedAd).order_by(desc(ExtractedAd.quality_score)).limit(100).all()
        df_ads = pd.DataFrame([{
            "Brand": a.run.query,
            "Text": a.ad_text,
            "Launch Date": a.launch_date,
            "Quality Score": a.quality_score,
            "Funnel": a.funnel_type,
            "Media": a.media_links
        } for a in ads])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_profiles.to_excel(writer, sheet_name='Competitor Summary', index=False)
            df_ads.to_excel(writer, sheet_name='Winning Assets', index=False)

        session.close()
        return output.getvalue()

if __name__ == "__main__":
    # Test
    data = ExportEngine.generate_market_pulse_xlsx()
    with open("market_pulse_test.xlsx", "wb") as f:
        f.write(data)
    print("Report generated: market_pulse_test.xlsx")
