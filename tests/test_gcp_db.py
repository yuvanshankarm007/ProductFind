"""
Unit and Integration Tests for Google Cloud Firestore Persistence & Caching.
Validates:
1. Zero-Crash local fallback initialization when GCP credentials are not present.
2. Skill persistence, retrieval, and listing in merchants_skills.
3. Cryptographic dispute dossier persistence and retrieval under PayPal Section 13.
4. Memorystore / Firestore price trajectory prediction caching and TTL verification.
5. Order state persistence.
6. API routes for dispute dossiers and database status.
"""

import pytest
import os
import time
from backend.core.gcp_db import FirestorePersistenceService
from backend.server import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_gcp_db_initialization():
    """Verify that FirestorePersistenceService starts cleanly without crashing."""
    service = FirestorePersistenceService()
    status = service.get_status()
    assert "mode" in status
    assert status["zero_crash_guarantee"] is True
    assert "active_collections" in status
    assert "merchants_skills" in status["active_collections"]
    assert "dispute_dossiers" in status["active_collections"]


def test_merchant_skill_persistence():
    """Verify skill storage, retrieval, listing, and deletion."""
    service = FirestorePersistenceService()
    test_domain = "test-store-onboarding.com"
    skill_data = {
        "skill_id": "skill_test_store_v1",
        "merchant_name": "Test Store",
        "merchant_domain": test_domain,
        "origin_country": "US",
        "currency": "USD",
        "confidence": 0.95,
        "policy_rules": {
            "return_window_days": 30,
            "restocking_fee_pct": 0.0,
            "warranty_type": "Brand Warranty",
            "warranty_months": 12,
            "cod_supported": True,
            "open_box_inspection": True
        },
        "paypal_shield_required": False
    }

    # Save
    saved = service.save_skill(test_domain, skill_data)
    assert saved is True

    # Retrieve
    retrieved = service.get_skill(test_domain)
    assert retrieved is not None
    assert retrieved["merchant_name"] == "Test Store"
    assert retrieved["policy_rules"]["return_window_days"] == 30

    # List
    all_skills = service.list_skills()
    domains = [s.get("merchant_domain") for s in all_skills]
    assert test_domain in domains

    # Delete
    deleted = service.delete_skill(test_domain)
    assert deleted is True
    assert service.get_skill(test_domain) is None


def test_dispute_dossier_persistence():
    """Verify cryptographic dispute dossier persistence under PayPal Section 13."""
    service = FirestorePersistenceService()
    order_id = "ORDER-GCP-TEST-001"
    dossier_data = {
        "dossier_id": "DOSSIER-ORDER-GC-A1B2C3",
        "paypal_order_id": order_id,
        "timestamp": "2026-11-01T12:00:00Z",
        "item_title": "Dell XPS 15 9530",
        "platform": "Best Buy",
        "agreed_tco": 1899.99,
        "advertised_condition": "Brand New",
        "open_box_verified": True,
        "seller_name": "Best Buy Official",
        "seller_rating": 4.8,
        "warranty_claims_evidence": "1-Year OEM Coverage",
        "merkle_spec_hash": "a1b2c3d4e5f6",
        "merkle_terms_hash": "b2c3d4e5f6a1",
        "merkle_pricing_hash": "c3d4e5f6a1b2",
        "cryptographic_hash": "d4e5f6a1b2c3"
    }

    # Save
    saved = service.save_dossier(order_id, dossier_data)
    assert saved is True

    # Get
    retrieved = service.get_dossier(order_id)
    assert retrieved is not None
    assert retrieved["paypal_order_id"] == order_id
    assert retrieved["cryptographic_hash"] == "d4e5f6a1b2c3"

    # List
    dossiers = service.list_dossiers(limit=10)
    order_ids = [d.get("paypal_order_id") for d in dossiers]
    assert order_id in order_ids


def test_price_cache_and_ttl():
    """Verify trajectory prediction caching and expiration."""
    service = FirestorePersistenceService()
    query_hash = "hash_ps5_slim_usd"
    prediction_data = {
        "product_name": "PS5 Slim",
        "current_best_price": 449.99,
        "buy_verdict": "BUY NOW",
        "sparkline": [499, 489, 479, 469, 449.99]
    }

    # Cache with 5 second TTL
    cached = service.cache_prediction(query_hash, prediction_data, ttl_seconds=5)
    assert cached is True

    # Retrieve valid cache
    result = service.get_prediction(query_hash)
    assert result is not None
    assert result["buy_verdict"] == "BUY NOW"

    # Expired cache test
    expired_hash = "hash_expired_item"
    service.cache_prediction(expired_hash, prediction_data, ttl_seconds=-1)
    assert service.get_prediction(expired_hash) is None


def test_order_session_persistence():
    """Verify order session persistence."""
    service = FirestorePersistenceService()
    order_id = "ORDER-SESSION-999"
    order_data = {
        "id": order_id,
        "status": "CREATED",
        "amount": 129.50,
        "currency": "EUR"
    }
    assert service.save_order(order_id, order_data) is True
    retrieved = service.get_order(order_id)
    assert retrieved is not None
    assert retrieved["amount"] == 129.50


def test_api_database_status_endpoint():
    """Verify GET /api/database/status and GET /api/health."""
    res = client.get("/api/database/status")
    assert res.status_code == 200
    data = res.json()
    assert "mode" in data
    assert data["zero_crash_guarantee"] is True

    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert "database" in health_data
    assert "Google Cloud Firestore Native Persistence" in health_data["features"]


def test_api_dossier_lifecycle():
    """Verify POST /api/paypal/create-dossier, GET /api/paypal/dossiers, and GET /api/paypal/dossiers/{id}."""
    order_id = "ORDER-LIFE-777"
    payload = {
        "order_id": order_id,
        "item_title": "MacBook Pro M3 Max",
        "platform": "Apple Direct",
        "agreed_tco": 3199.00,
        "condition": "Brand New",
        "open_box_verified": False,
        "seller_name": "Apple Inc",
        "seller_rating": 4.9,
        "warranty_claims": "1-Year AppleCare Coverage",
        "display_currency": "USD"
    }

    # 1. Create dossier
    post_res = client.post("/api/paypal/create-dossier", json=payload)
    assert post_res.status_code == 200
    dossier = post_res.json()
    assert dossier["paypal_order_id"] == order_id
    assert "cryptographic_hash" in dossier

    # 2. Query specific dossier
    get_res = client.get(f"/api/paypal/dossiers/{order_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["dossier_id"] == dossier["dossier_id"]

    # 3. List all dossiers
    list_res = client.get("/api/paypal/dossiers")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["count"] >= 1
    found = any(d["paypal_order_id"] == order_id for d in list_data["dossiers"])
    assert found is True

    # 4. 404 on unknown order
    not_found = client.get("/api/paypal/dossiers/NON-EXISTENT-ORDER-999")
    assert not_found.status_code == 404
