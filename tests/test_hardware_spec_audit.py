import sys
import pytest
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.core.bus import EventBus
from backend.coordinator import SentinelCoordinator
from backend.core.state import ScrapedListing
from backend.agents.tier2_processors import HardwareSpecAuditorAgent
from backend.core.asin_resolver import (
    resolve_canonical_product_url,
    resolve_amazon_asin,
    resolve_flipkart_search_url,
    resolve_amazon_search_url
)
from backend.core.url_health_cache import (
    is_generic_category_or_homepage,
    is_e002_error_url,
    validate_candidate_url
)


@pytest.mark.asyncio
async def test_canonical_m1_max_url_resolution():
    """Validates that canonical resolver respects exact RAM specs and regional delivery boundaries."""
    query_32gb = "apple macbook m1 max 32gb"
    query_64gb = "apple macbook m1 max 64gb"

    # 1. Flipkart M1 Max 32GB resolves to verified 32GB SKU
    fk_32_url = resolve_canonical_product_url(query_32gb, "flipkart.com", "IN")
    assert fk_32_url == "https://www.flipkart.com/apple-2021-macbook-pro-m1-max-32-gb-1-tb-ssd-mac-os-monterey-mk1a3hn-a/p/itm00aac391057cc"
    assert "itm00aac391057cc" in fk_32_url
    assert "32-gb" in fk_32_url

    # 2. Flipkart M1 Max 64GB: strictly omits 32GB model (zero spec mismatch)
    fk_64_url = resolve_canonical_product_url(query_64gb, "flipkart.com", "IN")
    assert fk_64_url == "", "Flipkart 32GB model must NOT be returned for 64GB query"

    # 3. Amazon: B09V5RWQXY does NOT deliver to India, so omitted for dest=IN
    amz_in_url = resolve_canonical_product_url(query_64gb, "amazon.com", "IN")
    assert amz_in_url == "", "Amazon US link must NOT be returned for India destination when it does not deliver to India"

    # For US destination, B09V5RWQXY is valid
    amz_us_url = resolve_canonical_product_url(query_64gb, "amazon.com", "US")
    assert amz_us_url == "https://www.amazon.com/dp/B09V5RWQXY"

    # 4. Apple: Never returns generic US refurbished directory page
    apple_url = resolve_canonical_product_url(query_64gb, "apple.com", "IN")
    assert apple_url == "", "Generic Apple refurbished category page must NOT be returned"


@pytest.mark.asyncio
async def test_url_validation_and_sanity():
    """Validates 200 OK, not 404, not E002, and not generic category/home pages."""
    # A. Valid product URLs (with appropriate destination countries)
    status_us, valid_us, _ = validate_candidate_url("https://www.amazon.com/dp/B09V5RWQXY", dest_country="US")
    assert valid_us is True
    assert status_us == 200

    status_in, valid_in, _ = validate_candidate_url(
        "https://www.flipkart.com/apple-2021-macbook-pro-m1-max-32-gb-1-tb-ssd-mac-os-monterey-mk1a3hn-a/p/itm00aac391057cc",
        dest_country="IN"
    )
    assert valid_in is True
    assert status_in == 200

    # B. Generic category / home pages
    category_urls = [
        "https://www.apple.com/shop/refurbished/mac/16-inch-macbook-pro",
        "https://www.apple.com/shop/buy-mac/macbook-pro",
        "https://www.apple.com/in/shop/buy-mac/macbook-pro",
        "https://www.apple.com/shop/buy-mac",
        "https://www.flipkart.com/",
        "https://www.amazon.com/s?k=macbook+pro"
    ]
    for u in category_urls:
        assert is_generic_category_or_homepage(u) is True, f"Expected {u} to be detected as category/homepage"
        status, is_valid, reason = validate_candidate_url(u)
        assert is_valid is False
        assert reason == "generic_category_or_homepage"

    # C. E002 Error URLs
    e002_urls = [
        "https://www.flipkart.com/some-laptop/p/itm5a18a5bf29ffb",
        "https://www.flipkart.com/error-listing-e002"
    ]
    for u in e002_urls:
        assert is_e002_error_url(u, body_text="E002 Error") is True
        status, is_valid, reason = validate_candidate_url(u)
        assert is_valid is False
        assert reason == "flipkart_e002_error"


@pytest.mark.asyncio
async def test_hardware_spec_auditor_agent_challenges():
    """Validates HardwareSpecAuditorAgent detecting mismatches and issuing SPEC_MISMATCH_CHALLENGE."""
    bus = EventBus()
    auditor = HardwareSpecAuditorAgent(bus=bus)

    # 1. Mismatched Chip & RAM Listing (M5 Max 36GB on M1 Max 64GB query)
    bad_listing_m5 = ScrapedListing(
        id="M5-LISTING-001",
        merchant="Flipkart Assured",
        merchant_domain="flipkart.com",
        product_title="Apple MacBook Pro ProLED XDR Display M5 Max 36GB",
        base_price=249900.0,
        seller_name="OmniRetail Assured",
        listing_url="https://www.flipkart.com/apple-macbook-pro-proled-xdr-display-m5-max-2026-m5-max-36-gb-2-tb-ssd-tahoe-mj2j4hn-a/p/itmd4bc234552798"
    )

    audit_result = await auditor.audit_hardware_specs(bad_listing_m5, query="apple macbook m1 max 64gb")
    assert audit_result["is_compliant"] is False
    assert audit_result["mismatch_type"] == "SPEC_MISMATCH"

    events = bus.get_logs()
    challenge_events = [e for e in events if e.event_type == "SPEC_MISMATCH_CHALLENGE"]
    assert len(challenge_events) == 1
    assert "M5 Max" in challenge_events[0].content or "M1 Max" in challenge_events[0].content

    # 2. Generic Category URL Listing
    bad_listing_cat = ScrapedListing(
        id="APPLE-CAT-001",
        merchant="Apple Store Direct",
        merchant_domain="apple.com",
        product_title="Apple MacBook Pro 16",
        base_price=249900.0,
        seller_name="Apple Retail",
        listing_url="https://www.apple.com/shop/buy-mac/macbook-pro"
    )

    audit_cat = await auditor.audit_hardware_specs(bad_listing_cat, query="apple macbook m1 max 64gb")
    assert audit_cat["is_compliant"] is False
    assert any("Generic Category Page Violation" in m for m in audit_cat["mismatches"])

    # 3. Fully Compliant Listing
    good_listing = ScrapedListing(
        id="M1-MAX-GOOD",
        merchant="Amazon Renewed",
        merchant_domain="amazon.com",
        product_title="Apple MacBook Pro 16\" (2021 M1 Max / 64GB RAM / 2TB SSD - Certified Refurbished)",
        base_price=219900.0,
        seller_name="Amazon Renewed Store",
        listing_url="https://www.amazon.com/dp/B09V5RWQXY"
    )
    audit_good = await auditor.audit_hardware_specs(good_listing, query="apple macbook m1 max 64gb")
    assert audit_good["is_compliant"] is True
    assert len(audit_good["mismatches"]) == 0

    # 4. Cross-Category Bleed Listing (Vivo Y31 smartphone query returning CMF Buds Pro 2 earbuds)
    bad_listing_bleed = ScrapedListing(
        id="CMF-BUDS-BLEED",
        merchant="Flipkart Assured",
        merchant_domain="flipkart.com",
        product_title="CMF by Nothing Buds Pro 2 with 50 dB ANC",
        base_price=3499.0,
        seller_name="OmniRetail Assured",
        listing_url="https://www.flipkart.com/cmf-nothing-buds-pro-2-50-db-anc-hi-res-ldac-smart-dial-spatial-audio-dual-drivers-bluetooth/p/itm30c0d780a4c6c"
    )
    audit_bleed = await auditor.audit_hardware_specs(bad_listing_bleed, query="vivo y31")
    assert audit_bleed["is_compliant"] is False
    assert any("Category Bleed Violation" in m for m in audit_bleed["mismatches"])


@pytest.mark.asyncio
async def test_bidirectional_coordinator_spec_resolution():
    """Validates Coordinator resolving SPEC_MISMATCH_CHALLENGE bidirectionally into canonical URL."""
    bus = EventBus()
    coord = SentinelCoordinator(bus=bus)

    # 1. 32GB query: verified canonical repair to genuine 32GB Flipkart SKU
    state_32 = await coord.execute_search(
        query="apple macbook m1 max 32gb",
        country="IN",
        currency="INR"
    )
    assert state_32.is_complete is True
    assert len(state_32.raw_listings) >= 1
    assert len(state_32.final_options) >= 1

    # Verify that every curated listing has an exact verified canonical product URL
    for opt in state_32.final_options:
        url = opt.listing.listing_url
        assert not is_generic_category_or_homepage(url), f"Curated listing {opt.listing.id} has category URL: {url}"
        assert not is_e002_error_url(url), f"Curated listing {opt.listing.id} has E002 URL: {url}"
        assert "itmd4bc234552798" not in url, "M5 Max listing should not be present in M1 Max results"
        assert "B0HPGT4XRT" not in url, "M6 listing should not be present in M1 Max results"

    # Targeted client challenge
    target_id = state_32.raw_listings[0].id
    challenged_state = await coord.challenge_listing(target_id, "AUDIT_SPECS")
    assert challenged_state is not None
    events = [e for e in bus.get_logs() if e.source_agent == "HardwareSpecAuditorAgent"]
    assert len(events) >= 1

    # 2. 64GB query: strictly omits 32GB models and non-delivering US links
    state_64 = await coord.execute_search(
        query="apple macbook m1 max 64gb",
        country="IN",
        currency="INR"
    )
    assert state_64.is_complete is True
    for opt in state_64.final_options:
        assert "32-gb" not in opt.listing.listing_url, "32GB model must never be returned for 64GB query"
        assert "B09V5RWQXY" not in opt.listing.listing_url, "Amazon US non-delivering link must not be returned for India"
