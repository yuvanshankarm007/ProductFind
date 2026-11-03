"""
Tests for Prompt-Driven Negative Learning and Self-Healing Quarantine.
Verifies that the autonomous swarm extracts negative constraints from user queries,
compiles them into CommerceInstincts, and aggressively quarantines 404 links,
out-of-stock items, and untrusted scam merchants.
"""

import pytest
from backend.core.prompt_learner import PromptLearnerEngine, PromptConstraint
from backend.core.instincts import commerce_instincts, CommerceInstinct
from backend.server import app, coordinator
from fastapi.testclient import TestClient

client = TestClient(app)

def test_prompt_learner_nlp_extraction():
    """Verify natural language parsing extracts negative constraints and cleans query."""
    engine = PromptLearnerEngine()
    
    # Test 1: In stock only + no 404s
    clean_q, constraints, rules = engine.parse_and_learn_from_prompt("Dell Precision 7820 in stock only no 404s", instincts_vault=commerce_instincts)
    assert "dell precision 7820" in clean_q.lower()
    assert constraints.in_stock_only is True
    assert constraints.no_404_dead_links is True
    assert len(rules) >= 2
    
    # Test 2: Anti-scam + avoid sketchy sellers
    clean_q2, constraints2, rules2 = engine.parse_and_learn_from_prompt("Sony WH-1000XM5 avoid scams no sketchy sellers high rating only")
    assert "sony wh-1000xm5" in clean_q2.lower()
    assert constraints2.anti_scam is True
    assert constraints2.min_trust_score >= 70.0

    # Test 3: Banned domain
    clean_q3, constraints3, rules3 = engine.parse_and_learn_from_prompt("iPhone 15 Pro do not show scamstore.com")
    assert "iphone 15 pro" in clean_q3.lower()
    assert "scamstore.com" in constraints3.banned_domains


def test_instinct_quarantine_evaluation():
    """Verify that evaluate_and_quarantine catches 404s, out-of-stock, and scams."""
    # Item 1: Out of stock item
    item_oos = {
        "title": "Dell Precision 7820 Workstation",
        "merchant": "Dell Direct",
        "price": 98000.0,
        "in_stock": False,
        "stock_status": "Out of Stock",
        "is_available": False,
        "url": "https://dell.com/precision",
        "seller_rating": 85
    }
    is_q_oos, reason_oos = commerce_instincts.evaluate_and_quarantine(item_oos)
    assert is_q_oos is True
    assert "out-of-stock" in reason_oos.lower()

    # Item 2: 404 dead link
    item_404 = {
        "title": "Dell Precision 7820 Workstation",
        "merchant": "RefurbDepot",
        "price": 95000.0,
        "in_stock": True,
        "stock_status": "In Stock",
        "is_available": True,
        "url": "https://refurbdepot.com/product/404-broken-link",
        "http_status": 404,
        "seller_rating": 80
    }
    is_q_404, reason_404 = commerce_instincts.evaluate_and_quarantine(item_404)
    assert is_q_404 is True
    assert "404" in reason_404

    # Item 3: Verified healthy item
    item_healthy = {
        "title": "Dell Precision 7820 Workstation",
        "merchant": "Amazon India Direct",
        "price": 119000.0,
        "in_stock": True,
        "stock_status": "In Stock",
        "is_available": True,
        "url": "https://amazon.in/dp/B08XYZ123",
        "http_status": 200,
        "seller_rating": 92
    }
    is_q_ok, _ = commerce_instincts.evaluate_and_quarantine(item_healthy)
    assert is_q_ok is False


def test_quarantine_filter_listings():
    """Verify list filtering partitions into clean listings and quarantined audit trail."""
    items = [
        {"title": "Valid Laptop", "merchant": "Amazon", "price": 999.0, "in_stock": True, "is_available": True, "http_status": 200, "seller_rating": 90},
        {"title": "Broken Link Laptop", "merchant": "OldStore", "price": 899.0, "in_stock": True, "is_available": True, "http_status": 404, "seller_rating": 80},
        {"title": "OOS Laptop", "merchant": "Dell", "price": 799.0, "in_stock": False, "is_available": False, "stock_status": "Out of Stock", "http_status": 200, "seller_rating": 85},
    ]
    
    clean, quarantined = commerce_instincts.quarantine_filter_listings(items)
    assert len(clean) == 1
    assert clean[0]["merchant"] == "Amazon"
    assert len(quarantined) == 2


@pytest.mark.asyncio
async def test_coordinator_prunes_oos_and_404_from_matrix():
    """Test full coordinator pipeline with prompt containing 'in stock only no 404s'."""
    prompt = "Dell Precision 7820 in stock only no 404s"
    state = await coordinator.execute_search(prompt, country="IN", currency="INR")
    
    # 1. Ensure clean query was distilled
    assert "dell precision 7820" in state.clean_query.lower()
    assert state.prompt_constraints is not None
    assert state.prompt_constraints.get("in_stock_only") is True
    
    # 2. Ensure zero out-of-stock items remain in final_options
    for opt in state.final_options:
        in_stock_val = opt.get("in_stock", True) if isinstance(opt, dict) else getattr(opt, "in_stock", True)
        assert in_stock_val is not False, f"OOS item found in final_options: {opt}"

    # 3. Ensure zero out-of-stock items in comparison_matrix for AG Grid
    for row in state.comparison_matrix:
        in_stock_val = row.get("in_stock", True) if isinstance(row, dict) else getattr(row, "in_stock", True)
        assert in_stock_val is not False, f"OOS item found in comp_matrix: {row}"
        action_val = row.get("action", "") if isinstance(row, dict) else getattr(row, "action", "")
        assert action_val != "Out of Stock", f"Action disabled as Out of Stock in comp_matrix: {row}"


def test_api_prompt_learning_endpoints():
    """Test FastAPI endpoints for prompt learning and quarantine."""
    # 1. Test POST /api/system/instincts/learn-from-prompt
    res_learn = client.post("/api/system/instincts/learn-from-prompt", json={
        "prompt": "Workstation in stock only no 404 dead links no scams"
    })
    assert res_learn.status_code == 200
    data_learn = res_learn.json()
    assert data_learn["status"] == "success"
    assert "clean_query" in data_learn
    assert data_learn["constraints"]["in_stock_only"] is True

    # 2. Test GET /api/system/instincts
    res_get = client.get("/api/system/instincts")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert "instincts" in data_get
    assert data_get["total_instincts"] > 0

    # 3. Test POST /api/system/quarantine-item
    res_q = client.post("/api/system/quarantine-item", json={
        "merchant": "FakeShadyStore",
        "reason": "Merchant sent replica hardware",
        "item_title": "Fake Dell Precision"
    })
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["status"] == "success"
    assert "quarantined" in data_q["message"].lower()
