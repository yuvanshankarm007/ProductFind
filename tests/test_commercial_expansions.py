"""
Comprehensive Unit & Integration Test Suite for ProductFind Commercial Expansions:
1. Price Drop Watchdog & Automated Notifications
2. Head-to-Head "Versus" Arbitrator Engine
3. "My Wallet" Card & Bank Offer Stacker
4. 1-Click Legal Dispute Assistant & PDF Dossier
5. FastAPI Endpoints & Session Integration
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend.core.price_watchdog import watchdog_service
from backend.core.versus_engine import versus_engine
from backend.core.wallet_stacker import wallet_stacker_service
from backend.core.dispute_assistant import dispute_assistant_service, DisputeFilingRequest


@pytest.fixture
def test_client():
    return TestClient(app)


def test_price_watchdog_subscription_and_dispatch():
    """Verify price watchdog records threshold, detects drops, and simulates triggers."""
    alert = watchdog_service.subscribe(
        product_title="Sony WH-1000XM5 Headphones",
        target_price=24000.0,
        current_price=26990.0,
        currency="INR",
        user_contact="tester@sentinel.ai",
        channel="telegram"
    )
    assert alert.id.startswith("alert-")
    assert alert.status == "ACTIVE"
    assert alert.target_price == 24000.0

    # Simulate price drop trigger
    triggered = watchdog_service.simulate_price_drop(alert.id, simulated_price=23490.0)
    assert triggered is not None
    assert triggered.status == "TRIGGERED"
    assert triggered.last_scouted_price == 23490.0
    assert "PRICE DROP" in triggered.notification_log or "SIMULATED" in triggered.notification_log


def test_versus_engine_query_and_benchmarks():
    """Verify versus query detection, benchmark matching, and arbitration verdict."""
    assert versus_engine.is_versus_query("Sony WH-1000XM5 vs Bose QC Ultra") is True
    assert versus_engine.is_versus_query("MacBook Pro 16 M3 versus Dell Precision 7820") is True
    assert versus_engine.is_versus_query("Samsung S24 Ultra or iPhone 16 Pro") is True
    assert versus_engine.is_versus_query("Sony WH-1000XM5 standalone") is False

    # Arbitrate known matchup
    result = versus_engine.arbitrate_versus("Sony WH-1000XM5 vs Bose QC Ultra", currency="INR")
    assert result.winner == "Sony WH-1000XM5"
    assert result.product_a.name == "Sony WH-1000XM5"
    assert result.product_b.name == "Bose QuietComfort Ultra"
    assert len(result.spec_comparison_table) >= 5
    assert len(result.swarm_verdict_rationale) >= 2
    assert result.value_difference_pct > 0


def test_wallet_stacker_discounts():
    """Verify bank card rules, discount caps, and universal cashback stacking."""
    cards = wallet_stacker_service.get_supported_cards()
    assert len(cards) >= 5

    # HDFC Regalia on Amazon (10% up to ₹1,500 on orders > ₹5,000)
    calc = wallet_stacker_service.calculate_best_wallet_discount(
        base_price=25000.0,
        merchant="Amazon",
        user_card_ids=["hdfc_regalia", "icici_amazon_pay"],
        currency="INR"
    )
    assert calc.best_card_id == "hdfc_regalia"
    assert calc.net_savings == 1500.0  # Max cap reached
    assert calc.effective_price == 23500.0
    assert calc.pay_in_4_biweekly == round(23500.0 / 4, 2)


def test_dispute_assistant_filing_and_merkle_pdf():
    """Verify Section 13 dispute filing, SHA-256 Merkle proof, and binary PDF generation."""
    req = DisputeFilingRequest(
        order_id="ORD-PYTEST-7788",
        merchant="Flipkart",
        product_title="Sony WH-1000XM5 Wireless Headphones",
        amount=26990.0,
        currency="INR",
        issue_type="OPEN_BOX_VIOLATION",
        incident_description="Courier refused doorstep unboxing and ran away after demanding delivery OTP.",
        buyer_name="Unit Tester",
        buyer_email="tester@sentinel.ai"
    )
    case = dispute_assistant_service.file_dispute(req)
    assert case.case_id.startswith("DISPUTE-")
    assert case.status == "DOSSIER_COMPILED"
    assert len(case.evidence_hash) == 64
    assert case.pdf_filename.endswith(".pdf")

    # Verify generated PDF file exists and is standard binary PDF/1.4
    pdf_path = os.path.join(dispute_assistant_service.dossiers_dir, case.pdf_filename)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


def test_fastapi_commercial_endpoints(test_client):
    """Verify HTTP integration for alerts, versus, wallet, and dispute downloads."""
    # Alerts
    res = test_client.get("/api/alerts")
    assert res.status_code == 200

    # Versus Benchmarks
    res = test_client.get("/api/versus/benchmarks")
    assert res.status_code == 200
    benchmarks = res.json()
    assert len(benchmarks) >= 3

    # Versus Arbitrate POST
    res = test_client.post("/api/versus/arbitrate", json={"query": "MacBook Pro M3 vs Dell Precision 7820", "currency": "INR"})
    assert res.status_code == 200
    assert "winner" in res.json()

    # Wallet Cards
    res = test_client.get("/api/wallet/cards")
    assert res.status_code == 200
    assert len(res.json()) >= 5

    # Wallet Calculate POST
    res = test_client.post("/api/wallet/calculate", json={
        "wallet_card_ids": ["sbi_cashback"],
        "retailer": "Flipkart",
        "order_amount": 10000.0
    })
    assert res.status_code == 200
    assert res.json()["net_savings"] == 500.0  # 5% of 10,000

    # Dispute Filing POST
    res = test_client.post("/api/dispute/file", json={
        "order_id": "ORD-FASTAPI-1234",
        "merchant": "Amazon",
        "product_title": "MacBook Pro 16 M3 Max",
        "amount": 349900.0,
        "issue_type": "COUNTERFEIT",
        "incident_description": "Serial number did not match Apple GSX database and chassis had non-OEM screws."
    })
    assert res.status_code == 200
    data = res.json()
    pdf_fn = data["pdf_filename"]

    # Dispute PDF Download GET
    res = test_client.get(f"/api/dispute/download/{pdf_fn}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 1000
