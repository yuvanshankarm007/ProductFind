"""
Comprehensive Test of Untested, Real-World, Adversarial, and Out-of-Domain Prompts.
Tests prompt constraint extraction, clean query resolution, quarantine enforcement,
TCO compilation, PayPal Pay in 4 calculations, and latency SLAs (< 3-4s).
"""

import time
import pytest
from backend.coordinator import SentinelCoordinator
from backend.core.bus import EventBus
from backend.server import app
from fastapi.testclient import TestClient

client = TestClient(app)

UNTESTED_PROMPTS = [
    {
        "prompt": "Nvidia RTX 4090 GPU in stock only no scams no refurbished avoid ebay.com",
        "expected_clean_contains": "rtx 4090",
        "must_have_constraint": "in_stock_only",
        "banned_domain": "ebay.com",
        "country": "US",
        "currency": "USD"
    },
    {
        "prompt": "Herman Miller Aeron Chair genuine only without 404 dead links",
        "expected_clean_contains": "herman miller aeron",
        "must_have_constraint": "no_404_dead_links",
        "country": "US",
        "currency": "USD"
    },
    {
        "prompt": "Sony A7 IV mirrorless camera in stock only no accessories avoid shady-deals.in",
        "expected_clean_contains": "sony a7 iv",
        "must_have_constraint": "in_stock_only",
        "banned_domain": "shady-deals.in",
        "country": "IN",
        "currency": "INR"
    },
    {
        "prompt": "Synology DS923+ 4-Bay NAS DiskStation in stock only no 404s",
        "expected_clean_contains": "synology ds923+",
        "must_have_constraint": "no_404_dead_links",
        "country": "US",
        "currency": "USD"
    },
    {
        "prompt": "Nintendo Switch OLED Mario Edition in stock only avoid scam stores",
        "expected_clean_contains": "nintendo switch oled",
        "must_have_constraint": "anti_scam",
        "country": "US",
        "currency": "USD"
    },
    {
        "prompt": "Framework Laptop 16 DIY Edition in stock only",
        "expected_clean_contains": "framework laptop 16",
        "must_have_constraint": "in_stock_only",
        "country": "DE",
        "currency": "EUR"
    },
    {
        "prompt": "Sennheiser HD 660S2 audiophile headphones in stock only no broken links",
        "expected_clean_contains": "sennheiser hd 660s2",
        "must_have_constraint": "no_404_dead_links",
        "country": "GB",
        "currency": "GBP"
    },
    {
        "prompt": "hey can you find me a steam deck oled 512gb in stock only please no scams",
        "expected_clean_contains": "steam deck oled 512gb",
        "must_have_constraint": "in_stock_only",
        "country": "US",
        "currency": "USD"
    },
    {
        "prompt": "iphone 15 pro max 256gb blue titanium dont show me out of stock or broken links",
        "expected_clean_contains": "iphone 15 pro max 256gb blue titanium",
        "must_have_constraint": "no_404_dead_links",
        "country": "US",
        "currency": "USD"
    },
    {
        "prompt": "Bowers & Wilkins PX8 wireless headphones authentic only exclude 404s",
        "expected_clean_contains": "bowers & wilkins px8",
        "must_have_constraint": "no_404_dead_links",
        "country": "GB",
        "currency": "GBP"
    },
    {
        "prompt": "Dell Precision 5820 Xeon W-2245 in stock only ban shady-depot.com",
        "expected_clean_contains": "dell precision 5820",
        "must_have_constraint": "in_stock_only",
        "banned_domain": "shady-depot.com",
        "country": "US",
        "currency": "USD"
    },
    {
        "prompt": "Roborock S8 Pro Ultra robot vacuum in stock only no accessories",
        "expected_clean_contains": "roborock s8 pro ultra",
        "must_have_constraint": "no_accessories",
        "country": "US",
        "currency": "USD"
    }
]

@pytest.mark.asyncio
async def test_batch_untested_prompts_coordinator():
    bus = EventBus()
    coord = SentinelCoordinator(bus)
    
    print("\n" + "=" * 80)
    print("EXECUTING BATCH TEST ON UNTESTED PROMPTS")
    print("=" * 80)
    
    for item in UNTESTED_PROMPTS:
        p = item["prompt"]
        country = item["country"]
        currency = item["currency"]
        
        t0 = time.time()
        state = await coord.execute_search(p, country=country, currency=currency)
        elapsed = time.time() - t0
        
        # 1. Assert SLA latency < 3.5 seconds
        assert elapsed < 3.5, f"Search took too long ({elapsed:.2f}s) for prompt '{p}'"
        
        # 2. Assert Clean Query Extraction
        assert item["expected_clean_contains"] in state.clean_query.lower(), (
            f"Expected '{item['expected_clean_contains']}' in clean query, got '{state.clean_query}'"
        )
        
        # 3. Assert Constraints
        constraints = state.prompt_constraints or {}
        assert constraints.get(item["must_have_constraint"]) is True, (
            f"Expected constraint '{item['must_have_constraint']}' to be True in {constraints}"
        )
        if item.get("banned_domain"):
            assert item["banned_domain"] in constraints.get("banned_domains", []), (
                f"Expected banned domain '{item['banned_domain']}' in {constraints.get('banned_domains')}"
            )
            
        # 4. Assert Curated Deals (final_options)
        assert len(state.final_options) > 0, f"Expected curated deals for '{p}'"
        for opt in state.final_options:
            assert opt.listing.in_stock is True, f"OOS deal in final_options: {opt.listing.merchant}"
            assert getattr(opt.listing, "is_dead_link", False) is False, f"Dead link in final_options: {opt.listing.merchant}"
            assert getattr(opt.listing, "http_status", 200) != 404, f"404 in final_options: {opt.listing.merchant}"
            assert opt.risk_adjusted_tco > 0, f"Invalid TCO: {opt.risk_adjusted_tco}"
            assert opt.trust.overall_score >= 50, f"Low trust seller crowned: {opt.listing.merchant}"
            assert opt.paypal is not None
            assert opt.paypal.pay_later_eligible is True
            assert opt.paypal.pay_in_4_biweekly > 0
            
        # 5. Assert AG Grid Comparison Matrix
        assert len(state.comparison_matrix) > 0, f"Expected rows in comparison matrix for '{p}'"
        if constraints.get("in_stock_only"):
            for row in state.comparison_matrix:
                assert row.get("in_stock", True) is not False, f"OOS in comparison matrix when in_stock_only was requested: {row.get('merchant')}"
                assert row.get("action") != "Out of Stock"
                
        if constraints.get("no_404_dead_links"):
            for row in state.comparison_matrix:
                assert row.get("is_dead_link", False) is not True, f"Dead link in comparison matrix when no_404 was requested: {row.get('merchant')}"
                assert row.get("http_status") != 404
                
        top = state.final_options[0]
        print(f"[PASS] ({elapsed:.3f}s) | Query: '{state.clean_query}' | TCO: ${top.risk_adjusted_tco:,.2f} | PayIn4: ${top.paypal.pay_in_4_biweekly:,.2f} bi-weekly")


def test_batch_untested_prompts_http_endpoint():
    """Verify live HTTP POST /api/search across untested prompts."""
    for item in UNTESTED_PROMPTS:
        t0 = time.time()
        res = client.post("/api/search", json={
            "query": item["prompt"],
            "country": item["country"],
            "currency": item["currency"]
        })
        elapsed = time.time() - t0
        assert res.status_code == 200
        assert elapsed < 3.5, f"HTTP endpoint exceeded SLA: {elapsed:.2f}s"
        data = res.json()
        assert len(data.get("final_options", [])) >= 1
        assert len(data.get("comparison_matrix", [])) >= 1
