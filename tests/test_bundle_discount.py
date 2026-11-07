import sys
import pytest
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.server import app, coordinator
from backend.core.arbitrage_catalogue import get_listings_for_workflow


@pytest.mark.asyncio
async def test_custom_items_list_arbitration():
    """Verify POST /api/workflow/arbitrate with custom items_list."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "Custom Productivity Bundle",
            "items_list": ["27-inch 4K Monitor", "Mechanical Keyboard", "Ergonomic Chair", "Webcam"],
            "budget_limit": 60000.0
        }
        res = await client.post("/api/workflow/arbitrate", json=payload)
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        assert data["optimized_total"] > 0
        assert len(data["sub_carts"]) >= 1
        assert "net_arbitrage_savings" in data
        assert data["net_arbitrage_savings"] >= 0.0
        assert "Amazon" in data["monopoly_alternatives"]
        assert "Flipkart" in data["monopoly_alternatives"]


@pytest.mark.asyncio
async def test_freeform_comma_separated_arbitration():
    """Verify comma-separated query routes into multi-item knapsack solver."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "27-inch 4K Monitor, Mechanical Keyboard, Ergonomic Chair"
        }
        res = await client.post("/api/workflow/arbitrate", json=payload)
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        assert data["optimized_total"] > 0
        assert len(data["sub_carts"]) >= 1
        assert len(data["unfulfilled_categories"]) == 0


@pytest.mark.asyncio
async def test_custom_unseen_items_synthesis():
    """Verify items not in preset catalogue are dynamically synthesized without failing."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "Ergonomic Studio Add-ons",
            "items_list": ["Ergonomic Desk Mat", "Laptop Stand", "RGB Light Bar"]
        }
        res = await client.post("/api/workflow/arbitrate", json=payload)
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        assert data["optimized_total"] > 0
        assert len(data["sub_carts"]) >= 1
        assert len(data["unfulfilled_categories"]) == 0


@pytest.mark.asyncio
async def test_api_search_bundle_detection():
    """Verify /api/search automatically routes 'WFH Setup under ₹50,000' to bundle knapsack."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        req = {
            "query": "WFH Setup under ₹50,000",
            "country": "IN",
            "currency": "INR",
            "mode": "single"  # mode single but query is bundle setup
        }
        res = await client.post("/api/search", json=req)
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        assert data.get("is_bundle") is True
        assert data.get("cart_split_result") is not None
        assert len(data.get("final_options", [])) >= 2
        assert len(data.get("comparison_matrix", [])) >= 4
        assert len(data.get("raw_listings", [])) >= 4


@pytest.mark.asyncio
async def test_api_search_explicit_bundle_mode():
    """Verify explicit mode='bundle' with items_list in /api/search."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        req = {
            "query": "Custom Bundle",
            "mode": "bundle",
            "items_list": ["Monitor", "Mechanical Keyboard"],
            "country": "IN",
            "currency": "INR"
        }
        res = await client.post("/api/search", json=req)
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        assert data["is_bundle"] is True
        assert data["cart_split_result"] is not None
        assert data["cart_split_result"]["optimized_total"] > 0


@pytest.mark.asyncio
async def test_api_search_get_bundle():
    """Verify GET /api/search?q=WFH+Setup+under+₹50,000 routes properly."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/search?q=WFH+Setup+under+₹50,000")
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        assert data["is_bundle"] is True
        assert len(data["final_options"]) > 0


@pytest.mark.asyncio
async def test_coordinator_bundle_direct():
    """Verify direct coordinator.execute_search handles bundle queries without 0 listings."""
    state = await coordinator.execute_search(
        query="WFH Setup under ₹50,000",
        country="IN",
        currency="INR"
    )
    assert state.is_bundle is True
    assert state.cart_split_result is not None
    assert len(state.final_options) == 3
    assert len(state.comparison_matrix) > 0
    assert len(state.raw_listings) > 0
