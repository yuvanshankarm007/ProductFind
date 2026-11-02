import asyncio
import os
import pytest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')

from backend.core.bus import EventBus
from backend.agents.tier1_scouts import ScoutSwarm

@pytest.mark.asyncio
async def test_live_stealth_search_end_to_end():
    """
    Verifies that the stealth browser engine (Chrome 124 TLS impersonation)
    successfully searches and extracts products from live retail platforms
    (Amazon, Flipkart, IndiaMART, etc.) and ensures that ALL listings have
    100% direct product URLs (no search page /s?k= or /search?q= links).
    """
    bus = EventBus()
    swarm = ScoutSwarm(bus)
    queries = [
        "Sony WH-1000XM5",
        "renewed dell latitude 5511 core i7-10850h"
    ]
    for q in queries:
        listings = await swarm.search(query=q, destination_country="IN")
        assert len(listings) >= 3, f"Expected at least 3 listings for {q}, got {len(listings)}"
        for i, l in enumerate(listings, 1):
            url = l.listing_url or ""
            is_search_page = any(m in url for m in ["/search", "/s?k=", "/s/"])
            assert not is_search_page, f"Listing {i} for '{q}' has search page URL: {url}"
            assert l.base_price > 0, f"Listing {i} for '{q}' has invalid price: {l.base_price}"
            assert len(l.product_title) > 5, f"Listing {i} for '{q}' has empty title"
