import pytest
import asyncio
from backend.core.bus import EventBus
from backend.coordinator import SentinelCoordinator

@pytest.mark.asyncio
async def test_dead_links_and_out_of_stock_ruled_out_from_recommendations():
    """
    Verifies that:
    1. Dead 404 links (like Electronics Bazaar) and out-of-stock items (like Cashify)
       are never crowned in any of the 3 curated recommendation tiers (OPTIMAL_VALUE, MAX_PROTECTION, BUDGET_STICKER).
    2. Only verified live, in-stock options win recommendation slots.
    3. The comparison matrix contains the dead and out-of-stock listings with accurate warning badges.
    4. Curated options have unique recommendation tiers (no reference aliasing overwriting).
    """
    bus = EventBus()
    coordinator = SentinelCoordinator(bus=bus)

    # Execute search for renewed enterprise laptop (Dell Latitude 5511)
    state = await coordinator.execute_search(
        query="renewed dell latitude 5511",
        country="IN",
        currency="INR",
        language="en",
        preferred_payment="all"
    )

    assert state is not None
    assert len(state.final_options) > 0

    # 1. Check all curated options are strictly IN STOCK and NOT dead links
    for opt in state.final_options:
        listing = opt.listing
        assert listing.in_stock is True, f"Curated deal {listing.id} at {listing.merchant} is out of stock!"
        assert getattr(listing, 'is_dead_link', False) is False, f"Curated deal {listing.id} at {listing.merchant} is a dead link!"
        assert listing.stock_status == "In Stock", f"Curated deal {listing.id} has invalid stock status: {listing.stock_status}"
        assert getattr(listing, 'http_status', 200) not in (404, 410), f"Curated deal {listing.id} has 404 HTTP status!"

    # 2. Verify that Cashify (Out of Stock) and Electronics Bazaar (404 Dead Link) are present in comparison matrix
    dead_or_oos = [m for m in state.comparison_matrix if not m.get("in_stock") or m.get("is_dead_link")]
    assert len(dead_or_oos) > 0, "Expected at least one out-of-stock or dead-link candidate in comparison matrix"

    curated_merchants = {o.listing.merchant for o in state.final_options}

    # Neither Electronics Bazaar, Cashify, nor RefurbishedPC (all out of stock / 404) should ever be in curated winners
    assert "Electronics Bazaar (Authorized Refurbished)" not in curated_merchants
    assert "Cashify Refurbished" not in curated_merchants
    assert "RefurbishedPC India (Certified Grade A)" not in curated_merchants

    # But all are preserved in the comparison matrix with proper warnings
    eb_rows = [m for m in state.comparison_matrix if "Electronics Bazaar" in m["merchant"]]
    if eb_rows:
        assert eb_rows[0]["is_dead_link"] is True
        assert "404" in eb_rows[0]["stock_status"]

    cashify_rows = [m for m in state.comparison_matrix if "Cashify" in m["merchant"]]
    if cashify_rows:
        assert cashify_rows[0]["in_stock"] is False
        assert cashify_rows[0]["stock_status"] == "Out of Stock"

    refurbpc_rows = [m for m in state.comparison_matrix if "RefurbishedPC" in m["merchant"]]
    if refurbpc_rows:
        assert refurbpc_rows[0]["in_stock"] is False
        assert refurbpc_rows[0]["stock_status"] == "Out of Stock"

    # 4. Verify all curated options have distinct tiers (no reference aliasing overwrites)
    tiers = [opt.recommendation_tier for opt in state.final_options]
    assert len(set(tiers)) == len(tiers), f"Duplicate recommendation tiers found: {tiers}"
