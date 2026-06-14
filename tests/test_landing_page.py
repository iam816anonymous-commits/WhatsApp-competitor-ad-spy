import pytest
from app.scrapers.landing_page_scraper import LandingPageScraper

@pytest.mark.asyncio
async def test_landing_page_intel():
    # Use example.com for testing basic extraction
    results = await LandingPageScraper.analyze_url("https://example.com")
    assert "headline" in results
    assert "pixels_detected" in results
    assert "funnel_category" in results
    assert results["funnel_category"] == "General" # example.com is general
