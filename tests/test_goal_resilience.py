"""
Comprehensive Verification Test Suite for User Directives (/goal):
1. No default fallback (no B0CS5X8286 catch-all, no blind random laptop/phone fallback).
2. Dynamic keyword categorization using search patterns (hp victus 5050 -> HP Victus RTX 5050 Gaming Laptop).
3. Omission of useless links (zero 404s, zero dog pages, zero empty URLs).
4. Up-to-date listings with real inventory tracking.
5. Horizontal multi-bot layer in Tier 1 with fast-fail.
6. Live inventory monitoring: "Notify Me", "Out of stock", "Currently unavailable" omitted from curated options.
7. Zero cross-region contamination: US links that do not deliver to India are pruned when dest is IN.
8. HTTP 200 payload content inspection: Dog pages and Flipkart Notify Me return 200 but are caught and disqualified.
"""

import pytest
from backend.core.bus import EventBus
from backend.coordinator import SentinelCoordinator
from backend.core.listing_auditor import LiveListingAuditor
from backend.core.asin_resolver import resolve_amazon_asin, resolve_canonical_product_url
from backend.agents.tier1_scouts import LiveInventoryProbeBot, RegionalLogisticsBot, LivePriceAuditorBot
from backend.agents.web_scout_engine import LiveWebScoutEngine


def test_no_default_fallback_asin():
    """Verify that unmapped queries do not fall back to Galaxy S24 B0CS5X8286."""
    asin_us = resolve_amazon_asin("xyz non existent gadget 9999", dest="US")
    assert asin_us is None, f"Expected None, got fallback ASIN: {asin_us}"

    asin_in = resolve_amazon_asin("xyz non existent gadget 9999", dest="IN")
    assert asin_in is None, f"Expected None, got fallback ASIN: {asin_in}"


def test_no_blind_canonical_url_fallback():
    """Verify that canonical product URL resolver returns empty string instead of random devices."""
    url = resolve_canonical_product_url("xyz unknown brand 123", merchant_domain="flipkart.com", dest_country="IN")
    assert url == "", f"Expected empty string for unmapped product, got: {url}"


def test_hp_victus_5050_categorization():
    """Verify that 'hp victus 5050' is recognized as an HP Victus Gaming Laptop with RTX 5050."""
    engine = LiveWebScoutEngine()
    profile = engine.get_semantic_profile("hp victus 5050", "IN")
    assert profile["brand"] == "HP"
    assert "Victus" in profile["title"]
    assert "5050" in profile["title"]
    assert "Gaming" in profile["category"]


def test_http_200_payload_auditor_amazon_dog_page():
    """Verify that Amazon Dog Page (returning 200 or 404 with dog text) is flagged as delisted."""
    dog_html = "<html><body><h1>Sorry, we couldn't find that page</h1><p>Martini - Meet the dogs of Amazon</p></body></html>"
    res = LiveListingAuditor.audit_url_and_content("https://www.amazon.com/dp/B0CS5X8286", body_text=dog_html, status_code=200)
    assert res.is_valid is False
    assert res.failure_reason == "amazon_dog_page_delisted"


def test_http_200_payload_auditor_flipkart_notify_me():
    """Verify that Flipkart 'Notify Me' depleted stock (HTTP 200) is caught and flagged as out of stock."""
    notify_me_html = '<html><body><button class="_2KpZ6l _2U9uOA _3v1-ww">Notify Me</button><div class="_16FRp0">Sold Out</div></body></html>'
    res = LiveListingAuditor.audit_url_and_content("https://www.flipkart.com/vivo-y31-5g/p/itm5337e173eced8", body_text=notify_me_html, status_code=200)
    assert res.is_valid is False
    assert res.is_in_stock is False
    assert "notify_me" in (res.failure_reason or "")


def test_http_200_payload_auditor_vijay_sales_currently_unavailable():
    """Verify that Vijay Sales 'Currently unavailable' / 'Notify Me' (HTTP 200) is flagged out of stock."""
    vs_html = '<html><body><button>Notify Me</button><button class="btn">Currently unavailable</button></body></html>'
    res = LiveListingAuditor.audit_url_and_content("https://www.vijaysales.com/p/230993/cmf-by-nothing", body_text=vs_html, status_code=200)
    assert res.is_valid is False
    assert res.is_in_stock is False


def test_regional_logistics_bot_rejects_non_shipping_us_links():
    """Verify that US links that do not ship to India are disqualified when dest is IN."""
    res, reason = RegionalLogisticsBot.audit_shipping(
        url="https://www.amazon.com/dp/B09V5RWQXY",
        origin="US",
        dest="IN",
        body_text="This item cannot be shipped to your selected delivery location."
    )
    assert res is False
    assert reason == "does_not_ship_to_india"


@pytest.mark.asyncio
async def test_search_hp_victus_5050_end_to_end():
    """End-to-end arbitration search for hp victus 5050."""
    bus = EventBus()
    coord = SentinelCoordinator(bus)
    state = await coord.execute_search("hp victus 5050", country="IN", currency="INR")

    assert state.is_complete is True
    # Zero dog pages
    for opt in state.final_options:
        url = opt.listing.listing_url or ""
        assert "amazon.com/dp/B0CS5X8286" not in url
        assert "amazon.com/dp/b0cs5x8286" not in url.lower()
        assert opt.listing.in_stock is True
        assert getattr(opt.listing, "is_dead_link", False) is False


@pytest.mark.asyncio
async def test_search_vivo_y31_omits_depleted_flipkart():
    """End-to-end search for vivo y31 ensures permanently sold-out itm5337e173eced8 is omitted from curated deals."""
    bus = EventBus()
    coord = SentinelCoordinator(bus)
    state = await coord.execute_search("vivo y31", country="IN", currency="INR")

    assert state.is_complete is True
    for opt in state.final_options:
        url = opt.listing.listing_url or ""
        assert "itm5337e173eced8" not in url
        assert opt.listing.in_stock is True
