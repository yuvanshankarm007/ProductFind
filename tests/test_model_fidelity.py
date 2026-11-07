import pytest
import re
from fastapi.testclient import TestClient
from backend.server import app
from backend.coordinator import SentinelCoordinator
from backend.core.bus import EventBus
from backend.agents.tier1_scouts import check_listing_hardware_compatibility
from backend.core.asin_resolver import resolve_canonical_product_url, resolve_secondary_canonical_url, resolve_amazon_asin
from backend.core.url_health_cache import validate_candidate_url

client = TestClient(app)


def test_api_search_get_informational():
    """Verify informational GET /api/search response."""
    resp1 = client.get("/api/search")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "online"
    assert data1["endpoint"] == "/api/search"

    resp2 = client.get("/api/search?q=")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "online"


@pytest.mark.asyncio
async def test_samsung_m5_model_fidelity_and_no_phone_bleed():
    """Ensure searching for Samsung M5 returns smart monitor and rejects M05 phones."""
    # 1. Compatibility check rejects M05 phones
    assert check_listing_hardware_compatibility("samsung M5", "Samsung M05 (Mint Green, 64 GB)", "https://www.flipkart.com/samsung-m05-mint-green-64-gb/p/itm99fc37d43aff8") is False
    assert check_listing_hardware_compatibility("samsung M5", "Samsung 32\" M5 Smart Monitor", "https://www.amazon.in/dp/B0FKKDSTMX") is True
    assert check_listing_hardware_compatibility("samsung M5", "Samsung M5 80.1 cm (32 inch) Full HD Smart Monitor", "https://www.flipkart.com/samsung-m5/p/itmf3aea0431155e") is True

    # 2. Canonical URL resolutions
    fk_url = resolve_canonical_product_url("samsung M5", "flipkart.com", "IN")
    assert "itmf3aea0431155e" in fk_url
    assert "itm99fc37d43aff8" not in fk_url

    sec_url = resolve_secondary_canonical_url("samsung M5", "IN")
    assert "itmface6869face0" in sec_url
    assert "itm99fc37d43aff8" not in sec_url

    asin = resolve_amazon_asin("samsung M5", "IN")
    assert asin == "B0FKKDSTMX"


@pytest.mark.asyncio
async def test_campus_brand_fidelity_and_no_competitor_bleed():
    """Ensure searching for Campus jogging shoes rejects off-brand sponsored competitors."""
    assert check_listing_hardware_compatibility("campus jogging shoes", "Canberra Men's Jogging Shoes", "https://www.flipkart.com/canberra/p/123") is False
    assert check_listing_hardware_compatibility("campus jogging shoes", "Boldfit UrbanX Walking Shoes", "https://www.flipkart.com/boldfit/p/123") is False
    assert check_listing_hardware_compatibility("campus jogging shoes", "Asian Powerplay Shoes", "https://www.flipkart.com/asian/p/123") is False
    assert check_listing_hardware_compatibility("campus jogging shoes", "Campus Hurricane Running Shoes", "https://www.flipkart.com/campus-hurricane-running-shoes-men/p/itm4d0125d9c2c65") is True

    fk_url = resolve_secondary_canonical_url("campus jogging shoes", "IN")
    assert "campus" in fk_url
    asin = resolve_amazon_asin("campus jogging shoes", "IN")
    assert asin == "B08PRXXQB3"


@pytest.mark.asyncio
async def test_happydent_and_logitech_fidelity():
    """Ensure Happydent and Logitech queries reject off-brand competitors."""
    # Happydent rejects Kritvi Naturals
    assert check_listing_hardware_compatibility("happydent gum", "Kritvi Naturals Mint Gum", "https://amazon.in/dp/123") is False
    assert check_listing_hardware_compatibility("happydent gum", "Happydent Wave Mint Gum", "https://amazon.in/dp/B0GX9BNT8F") is True

    # Logitech rejects Zebronics / Portronics
    assert check_listing_hardware_compatibility("logitech mouse", "Zebronics Wireless Optical Mouse", "https://amazon.in/dp/123") is False
    assert check_listing_hardware_compatibility("logitech mouse", "Logitech M171 Wireless Mouse", "https://amazon.in/dp/B08LT9BMPP") is True


@pytest.mark.asyncio
async def test_target_queries_coordinator_flow():
    """Execute coordinator for target queries and verify 100% on-brand zero 404 links."""
    bus = EventBus()
    coord = SentinelCoordinator(bus)

    for q in ["campus jogging shoes", "happydent gum", "logitech mouse", "samsung M5"]:
        state = await coord.execute_search(
            query=q,
            country="IN",
            currency="INR"
        )
        assert state.is_complete is True
        assert len(state.final_options) >= 3, f"Expected 3 options for {q}"

        brand_key = "campus" if "campus" in q else ("happydent" if "happydent" in q else ("logitech" if "logitech" in q else "samsung"))
        for opt in state.final_options:
            listing = opt.listing
            title_url_lower = f"{listing.product_title.lower()} {listing.listing_url.lower()}"
            assert brand_key in title_url_lower, f"Brand {brand_key} must be in title/url for query '{q}', got '{listing.product_title}' ({listing.listing_url})"
            assert listing.is_dead_link is False
            assert listing.http_status == 200
            assert listing.in_stock is True

            # Samsung M5 must NOT have phone bleed
            if brand_key == "samsung":
                assert "m05" not in title_url_lower, f"Samsung M05 phone bled into Samsung M5 result: {listing.product_title}"
                assert "phone" not in title_url_lower, f"Phone bled into Samsung M5 result: {listing.product_title}"
