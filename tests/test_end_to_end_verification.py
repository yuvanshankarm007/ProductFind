"""
Full-Story End-to-End Verification Test Suite for ProductFind Rebuild.
Tests all system boundaries via FastAPI TestClient:
1. Static files & Demo Seed Dataset (/data/demo_seed.json, /, /vendor/ag-grid-community.min.js)
2. Core REST APIs (/api/health, /api/preferences, /api/database/status, /api/skills)
3. Autonomous Self-Healer & Instincts APIs (/api/system/health, /api/system/instincts)
4. PayPal Orders v2 & Merkle Dispute Dossier APIs
5. Full Swarm Search HTTP API with dynamic risk preferences
6. WebSocket Session-Isolated Negotiation Gateway
"""

import pytest
import json
from fastapi.testclient import TestClient
from backend.server import app
from backend.paypal_service import PayPalEvidenceSentinel

client = TestClient(app)


def test_static_assets_and_demo_seed():
    """Verify frontend index, local vendored AG Grid, and demo seed data."""
    # 1. Frontend entry point
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "ProductFind" in res_root.text
    assert "vendor/ag-grid-community.min.js" in res_root.text

    # 2. Demo seed dataset
    res_seed = client.get("/data/demo_seed.json")
    assert res_seed.status_code == 200
    data = res_seed.json()
    assert "merchant_skills" in data
    assert len(data["merchant_skills"]) >= 5


def test_core_platform_apis():
    """Verify health check, preferences, database status, and skills endpoints."""
    # 1. Health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    health = res_health.json()
    assert health["status"] == "healthy"
    assert "database" in health

    # 2. Preferences
    res_pref = client.get("/api/preferences")
    assert res_pref.status_code == 200
    prefs = res_pref.json()
    assert "languages" in prefs
    assert "currencies" in prefs
    assert "USD" in prefs["currencies"]
    assert "INR" in prefs["currencies"]

    # 3. Database status
    res_db = client.get("/api/database/status")
    assert res_db.status_code == 200
    db = res_db.json()
    assert db["zero_crash_guarantee"] is True

    # 4. Skills
    res_skills = client.get("/api/skills")
    assert res_skills.status_code == 200
    skills = res_skills.json()
    assert skills["count"] > 0


def test_self_healer_and_instincts_apis():
    """Verify autonomous self-healer diagnostics and instincts endpoints."""
    # 1. Self-healer health
    res_h = client.get("/api/system/health")
    assert res_h.status_code == 200
    h = res_h.json()
    assert "overall_health_score" in h
    assert "overall_status" in h

    # 2. Instincts list
    res_i = client.get("/api/system/instincts")
    assert res_i.status_code == 200
    inst = res_i.json()
    assert inst["status"] == "success"
    assert inst["total_instincts"] >= 0


def test_paypal_order_and_dossier_flow():
    """Verify PayPal v2 Orders creation, capture, and Section 13 Merkle dossier generation."""
    # 1. Create Order
    order_payload = {"amount": 349.99, "currency": "USD", "item_name": "Sony WH-1000XM5"}
    res_ord = client.post("/api/paypal/create-order", json=order_payload)
    assert res_ord.status_code == 200
    order = res_ord.json()
    assert "id" in order
    order_id = order["id"]

    # 2. Capture Order
    res_cap = client.post("/api/paypal/capture-order", json={"order_id": order_id})
    assert res_cap.status_code == 200
    cap = res_cap.json()
    assert cap["status"] == "COMPLETED"

    # 3. Create Dispute Dossier
    dossier_payload = {
        "order_id": order_id,
        "item_title": "Sony WH-1000XM5 Premium Headphones",
        "platform": "Best Buy",
        "agreed_tco": 349.99,
        "condition": "Brand New",
        "open_box_verified": True,
        "seller_name": "Best Buy Official",
        "seller_rating": 4.8,
        "warranty_claims": "1-Year OEM Coverage",
        "display_currency": "USD"
    }
    res_dos = client.post("/api/paypal/create-dossier", json=dossier_payload)
    assert res_dos.status_code == 200
    dossier = res_dos.json()
    assert dossier["paypal_order_id"] == order_id
    assert len(dossier["cryptographic_hash"]) == 64
    assert len(dossier["merkle_spec_hash"]) == 64

    # 4. Fetch Dossier by Order ID
    res_get_dos = client.get(f"/api/paypal/dossiers/{order_id}")
    assert res_get_dos.status_code == 200
    assert res_get_dos.json()["dossier_id"] == dossier["dossier_id"]


def test_search_api_with_risk_preferences():
    """Verify /api/search with dual currency and dynamic risk weighting."""
    payload = {
        "query": "Sony WH-1000XM5",
        "language": "en",
        "country": "US",
        "currency": "USD",
        "preferred_payment": "all",
        "session_id": "test-e2e-session",
        "warranty_priority": 0.8,
        "speed_priority": 0.3,
        "trust_tolerance": 0.9
    }
    res_search = client.post("/api/search", json=payload)
    assert res_search.status_code == 200
    state = res_search.json()
    assert state["is_complete"] is True
    assert len(state["final_options"]) == 3
    assert len(state["comparison_matrix"]) > 0

    # Ensure all 3 options have distinct recommendation tiers
    tiers = [opt["recommendation_tier"] for opt in state["final_options"]]
    assert "OPTIMAL_VALUE" in tiers
    assert "MAX_PROTECTION" in tiers
    assert "BUDGET_STICKER" in tiers


def test_websocket_negotiation_session_isolated():
    """Verify full-duplex WebSocket session isolation and real-time streaming."""
    session_id = "test-ws-e2e-sess"
    with client.websocket_connect(f"/ws/negotiate?session_id={session_id}") as ws:
        # Send search request over WebSocket
        ws.send_json({
            "action": "search",
            "query": "Sony WH-1000XM5",
            "country": "US",
            "currency": "USD",
            "session_id": session_id,
            "warranty_priority": 0.5,
            "speed_priority": 0.5,
            "trust_tolerance": 0.7
        })

        # Receive streamed agent events and final result
        received_event = False
        received_final = False

        for _ in range(50):
            data = ws.receive_json()
            if data.get("type") == "AGENT_EVENT":
                received_event = True
                ev = data.get("event", {})
                assert ev.get("session_id") == session_id
            elif data.get("type") == "FINAL_RESULT":
                received_final = True
                state = data.get("state", {})
                assert state.get("is_complete") is True
                assert state.get("session_id") == session_id
                break

        assert received_event, "Must receive live AGENT_EVENT during negotiation"
        assert received_final, "Must receive FINAL_RESULT concluding negotiation"
