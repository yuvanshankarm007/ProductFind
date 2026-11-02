"""
Test Suite for Everything Claude Code (ECC) Inspired Modules:
- SwarmLifecycleHooks
- CommerceInstinctsVault
- CommerceAgentShield
- Coordinator Zero-Trust Pipeline & Instincts REST Endpoints
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.server import app
from backend.core.bus import EventBus
from backend.core.instincts import CommerceInstinctsVault, CommerceInstinct, commerce_instincts
from backend.core.agent_shield import CommerceAgentShield, commerce_agent_shield
from backend.core.hooks import SwarmLifecycleHooks
from backend.core.state import ScrapedListing, AnalyzedDealOption
from backend.coordinator import SentinelCoordinator


client = TestClient(app)


def test_commerce_instincts_vault(tmp_path):
    """Verifies durable pattern memory, blacklisting, and zero-latency URL repair."""
    test_storage = tmp_path / "test_instincts.json"
    vault = CommerceInstinctsVault(storage_path=str(test_storage))

    instincts = vault.list_instincts()
    assert len(instincts) >= 5, "Baseline instincts must be seeded"

    # Verify blacklisted dead ASIN repair
    dead_url = "https://www.amazon.in/Dell-Latitude-15-6-Inch-Refurbished-Business/dp/B0CKZJ8V3C"
    repaired_url = vault.match_and_repair_url(dead_url, query="Dell Latitude 5511 renewed", dest_country="IN")
    assert "B0HP26WLF4" in repaired_url, "Dead ASIN B0CKZJ8V3C must be automatically repaired to B0HP26WLF4"

    # Verify search page query repair
    search_url = "https://www.amazon.in/s?k=dell+latitude+laptop"
    repaired_search = vault.match_and_repair_url(search_url, query="Dell Latitude", dest_country="IN")
    assert "/s?k=" not in repaired_search, "Search queries must be sanitized"
    assert "/dp/" in repaired_search, "Must resolve to direct canonical product page"

    # Test dynamic instinct crystallization
    new_inst = vault.record_dead_link_instinct(
        pattern="OBSOLETE-SKU-999",
        reason="Detected HTTP 410 Gone on merchant supplier",
        replacement_url="https://www.amazon.in/dp/B0BZP2H373"
    )
    assert new_inst.rule_id.startswith("INST-DEAD-")
    assert vault.match_and_repair_url("https://example.com/item/OBSOLETE-SKU-999") == "https://www.amazon.in/dp/B0BZP2H373"


def test_commerce_agent_shield():
    """Verifies CommerceAgentShield zero-trust security and URL sanitization."""
    # Test search query interception
    rogue_url_1 = "https://www.amazon.com/s?k=headphones"
    clean_1 = commerce_agent_shield.sanitize_url(rogue_url_1, query="sony wh-1000xm5", merchant_domain="amazon.com", dest_country="US")
    assert "/s?k=" not in clean_1
    assert "B09Z2S9FSX" in clean_1

    # Test Newegg search query interception
    rogue_url_2 = "https://www.newegg.com/p/pl?d=dell+latitude"
    clean_2 = commerce_agent_shield.sanitize_url(rogue_url_2, query="dell latitude 5511", merchant_domain="newegg.com", dest_country="US")
    assert "pl?d=" not in clean_2
    assert "B0D16TS69T" in clean_2

    # Test listing in-place validation
    mock_listing = ScrapedListing(
        id="TEST-1",
        merchant="Amazon India",
        merchant_domain="amazon.in",
        product_title="Dell Latitude 5511 Laptop",
        base_price=32000.0,
        currency="INR",
        origin_country="IN",
        shipping_cost=0.0,
        estimated_tax=0.0,
        condition="Renewed",
        seller_name="Verified Partner",
        is_third_party=False,
        listing_url="https://www.amazon.in/Dell-Latitude-15-6-Inch-Refurbished-Business/dp/B0CKZJ8V3C"
    )
    valid = commerce_agent_shield.validate_listing(mock_listing, query="dell latitude 5511", dest_country="IN")
    assert valid is True
    assert "B0HP26WLF4" in mock_listing.listing_url, "Listing URL must be hot-swapped to active canonical URL"


@pytest.mark.asyncio
async def test_swarm_lifecycle_hooks():
    """Verifies event-driven lifecycle hooks (pre_search, post_scout, pre_render)."""
    bus = EventBus()
    hooks = SwarmLifecycleHooks(bus=bus)

    # 1. Pre-search
    calib = await hooks.pre_search("Renewed Laptop", "IN", "INR")
    assert calib["country"] == "IN"
    assert calib["currency"] == "INR"

    # 2. Post-scout
    mock_listings = [
        ScrapedListing(
            id="L1", merchant="Store A", merchant_domain="amazon.in",
            product_title="Dell Laptop", base_price=28000.0, currency="INR",
            origin_country="IN", shipping_cost=0.0, estimated_tax=0.0, condition="Renewed",
            seller_name="Partner", is_third_party=False,
            listing_url="https://www.amazon.in/s?k=dell+laptop"
        )
    ]
    sanitized = await hooks.post_scout(mock_listings, query="dell laptop", dest_country="IN")
    assert len(sanitized) == 1
    assert "/s?k=" not in sanitized[0].listing_url

    # Check event bus logs
    logs = bus.get_logs()
    events = [l.event_type for l in logs]
    assert "LIFECYCLE_PRE_SEARCH" in events
    assert "LIFECYCLE_POST_SCOUT" in events


@pytest.mark.asyncio
async def test_coordinator_with_ecc_harness():
    """Verifies that the SentinelCoordinator executes the full ECC-enhanced lifecycle harness."""
    bus = EventBus()
    coord = SentinelCoordinator(bus=bus)

    state = await coord.execute_search(
        query="renewed dell latitude 5511 core i7-10850h",
        country="IN",
        currency="INR"
    )

    assert state.is_complete is True
    assert len(state.final_options) >= 3

    # Check that zero search URLs and zero dead ASINs exist across all final options
    for opt in state.final_options:
        url = opt.listing.listing_url
        assert not any(marker in url for marker in ["/s?k=", "/search", "/pl?", "pl?d="]), f"Rogue search leak: {url}"
        assert "B0CKZJ8V3C" not in url, "Delisted ASIN B0CKZJ8V3C must not be surfaced"
        assert "1TS-000A-0U1G3" not in url, "Delisted Newegg item must not be surfaced"


def test_instincts_api_endpoints():
    """Verifies REST endpoints for viewing and teaching operational instincts."""
    # 1. GET /api/system/instincts
    res = client.get("/api/system/instincts")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_instincts"] >= 5

    # 2. POST /api/system/instincts/learn
    learn_payload = {
        "pattern": "EXPIRED-ITEM-XYZ",
        "reason": "Merchant confirmed item end of life",
        "replacement_target": "https://www.amazon.in/dp/B0HP26WLF4"
    }
    learn_res = client.post("/api/system/instincts/learn", json=learn_payload)
    assert learn_res.status_code == 200
    learn_data = learn_res.json()
    assert learn_data["status"] == "success"
    assert learn_data["instinct"]["pattern"] == "EXPIRED-ITEM-XYZ"
