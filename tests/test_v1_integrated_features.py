"""
Comprehensive Integration Tests for V1 Features in ProductFind:
1. Multi-Item Combinatorial Knapsack Cart Arbitrageur
2. Pure-Python Section 13 Legal PDF Dispute Dossier Generator
3. Visual Truth & Holographic Packaging Counterfeit Shield
4. Temporal Price Volatility & Pre-Authorized Snipe Lock Engine
5. FastAPI REST API endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient

from backend.server import app
from backend.core.cart_arbitrage import CartArbitrageurAgent, ProductListing
from backend.core.arbitrage_catalogue import WORKFLOW_PRESETS, CATALOGUE, get_listings_for_workflow
from backend.core.pdf_generator import Section13PDFGenerator
from backend.core.visual_shield import VisualTruthShieldAgent
from backend.core.temporal_volatility import TemporalVolatilityEngine
from backend.paypal_service import PayPalEvidenceSentinel


client = TestClient(app)


# ===========================================================================
# 1. Knapsack Multi-Retailer Cart Splitter Tests
# ===========================================================================

def test_knapsack_cart_arbitrage_optimality():
    agent = CartArbitrageurAgent()
    
    # Create candidate pool across Amazon, Flipkart, OEM Direct for Monitor & Keyboard
    candidates = [
        ProductListing(
            id="mon-amz",
            title="LG 27 Monitor",
            brand="LG",
            model="27UP650",
            category="Monitor",
            retailer="Amazon",
            base_price=24000.0,
            current_price=22000.0,
            original_mrp=30000.0,
            shipping_cost=0.0,
            in_stock=True,
            rating=4.5,
            review_count=1000,
            seller_name="Amazon Retail",
            card_offers=["₹1,500 Instant Discount on HDFC Cards (Subtotal > ₹20k)"]
        ),
        ProductListing(
            id="mon-fk",
            title="LG 27 Monitor",
            brand="LG",
            model="27UP650",
            category="Monitor",
            retailer="Flipkart",
            base_price=25000.0,
            current_price=23000.0,
            original_mrp=30000.0,
            shipping_cost=0.0,
            in_stock=True,
            rating=4.4,
            review_count=800,
            seller_name="RetailNet",
            card_offers=[]
        ),
        ProductListing(
            id="kb-amz",
            title="Keychron K2 Keyboard",
            brand="Keychron",
            model="K2",
            category="Mechanical Keyboard",
            retailer="Amazon",
            base_price=8000.0,
            current_price=7500.0,
            original_mrp=9000.0,
            shipping_cost=0.0,
            in_stock=True,
            rating=4.6,
            review_count=500,
            seller_name="Amazon Retail",
            card_offers=[]
        ),
        ProductListing(
            id="kb-fk",
            title="Keychron K2 Keyboard",
            brand="Keychron",
            model="K2",
            category="Mechanical Keyboard",
            retailer="Flipkart",
            base_price=7800.0,
            current_price=6900.0,
            original_mrp=9000.0,
            shipping_cost=0.0,
            in_stock=True,
            rating=4.6,
            review_count=600,
            seller_name="TechArena",
            card_offers=["Special Bank Offer ₹300 Off"]
        )
    ]

    result = agent.optimize_cart_split("WFH Setup", candidates)

    assert result.optimized_total > 0
    assert len(result.sub_carts) >= 1
    assert result.workflow_id.startswith("wf-")
    # Total should beat buying everything at full price
    subtotal_sum = sum(sc.items_subtotal for sc in result.sub_carts)
    assert result.optimized_total <= subtotal_sum
    # Monopoly alternatives computed
    assert "Amazon" in result.monopoly_alternatives
    assert "Flipkart" in result.monopoly_alternatives


def test_knapsack_empty_and_single_item_edges():
    agent = CartArbitrageurAgent()
    empty_res = agent.optimize_cart_split("Empty Query", [])
    assert empty_res.optimized_total == 0.0
    assert len(empty_res.sub_carts) == 0

    single_item = [
        ProductListing(
            id="item-1",
            title="USB Cable",
            brand="Anker",
            model="C-to-C",
            category="Cable",
            retailer="Amazon",
            base_price=400.0,
            current_price=350.0,
            original_mrp=600.0,
            shipping_cost=40.0,
            in_stock=True,
            rating=4.8,
            review_count=100,
            seller_name="Anker Direct"
        )
    ]
    res_single = agent.optimize_cart_split("Single Cable", single_item)
    assert res_single.optimized_total > 0
    # Under 499 threshold, shipping fee is added (350 + 40 = 390)
    assert res_single.sub_carts[0].shipping_fee == 40.0
    assert res_single.optimized_total == 390.0


# ===========================================================================
# 2. Pure-Python Legal Section 13 PDF Dispute Dossier Generator Tests
# ===========================================================================

def test_section13_pdf_generation_format_and_integrity():
    generator = Section13PDFGenerator()
    
    dossier = PayPalEvidenceSentinel.create_dispute_dossier(
        order_id="ORD-TEST-9921",
        item_title="Sony WH-1000XM5 Wireless Headphones",
        platform="Amazon Prime / Authorized Partner",
        agreed_tco=26990.0,
        condition="Brand New",
        open_box_verified=True,
        seller_name="Appario Retail Direct",
        seller_rating=4.8,
        warranty_claims="1-Year OEM Domestic Warranty",
        display_currency="INR"
    )
    
    dossier_data = dossier.model_dump()
    pdf_bytes = generator.generate(dossier_data)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes
    assert b"/Root 1 0 R" in pdf_bytes
    assert b"xref" in pdf_bytes
    assert len(pdf_bytes) > 500  # Valid PDF size


# ===========================================================================
# 3. Visual Truth & Holographic Packaging Shield Tests
# ===========================================================================

def test_visual_shield_tampered_seal_and_counterfeit():
    shield = VisualTruthShieldAgent()

    # Case 1: Tampered packaging
    tampered_listing = {
        "id": "item-tampered-01",
        "title": "Sony WH-1000XM5 Headphones",
        "brand": "Sony",
        "seller_name": "MegaDiscount Global Traders",
        "packaging_seal_intact": False,
        "is_refurbished": False,
        "rating": 2.5,
        "review_count": 12,
        "current_price": 7999.0,
        "original_mrp": 34990.0
    }
    res_tampered = shield.verify_listing_visuals(tampered_listing)
    assert res_tampered.seal_integrity == "BROKEN_SEAL"
    assert res_tampered.counterfeit_risk_score >= 0.65
    assert res_tampered.authenticity_grade == "COUNTERFEIT_DETECTED"
    assert any(a.anomaly_type == "tampered_seal" for a in res_tampered.anomalies)

    # Case 2: Factory sealed genuine item
    genuine_listing = {
        "id": "item-genuine-01",
        "title": "Sony WH-1000XM5 Headphones Official",
        "brand": "Sony",
        "seller_name": "Appario Retail Direct",
        "packaging_seal_intact": True,
        "is_refurbished": False,
        "rating": 4.7,
        "review_count": 5200,
        "current_price": 26990.0,
        "original_mrp": 34990.0
    }
    res_genuine = shield.verify_listing_visuals(genuine_listing)
    assert res_genuine.seal_integrity == "FACTORY_SEALED"
    assert res_genuine.authenticity_grade == "GRADE_A_GENUINE"
    assert res_genuine.counterfeit_risk_score < 0.35


# ===========================================================================
# 4. Temporal Volatility & 1-Click Snipe Engine Tests
# ===========================================================================

def test_temporal_volatility_and_snipe_deal_lock():
    engine = TemporalVolatilityEngine()
    
    item = {
        "id": "sony-xm5-amz",
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "current_price": 26990.0,
        "original_mrp": 34990.0,
        "retailer": "Amazon"
    }
    
    vol = engine.analyze_item_volatility(item)
    assert vol.listing_id == "sony-xm5-amz"
    assert len(vol.history) == 31  # 30 days history + 1 current
    assert vol.all_time_low <= vol.current_price or vol.all_time_low <= vol.all_time_high
    assert vol.volatility_index >= 0.0

    # Lock in snipe deal
    snipe_res = engine.lock_snipe_deal("sony-xm5-amz", 22000.0, auto_execute_seconds=600)
    assert snipe_res.lock_id.startswith("LOCK-")
    assert snipe_res.status == "SECURED_LOCKED"
    assert len(snipe_res.receipt_hash) == 64  # SHA-256
    assert snipe_res.lock_id in engine.active_locks


# ===========================================================================
# 5. FastAPI Endpoints Integration Tests
# ===========================================================================

def test_api_workflow_presets():
    res = client.get("/api/workflow/presets")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["presets"]) >= 4
    preset_ids = [p["id"] for p in data["presets"]]
    assert "wfh-50k" in preset_ids
    assert "podcast-pro" in preset_ids


def test_api_workflow_arbitrate():
    payload = {
        "query": "WFH Setup under ₹50,000",
        "budget_limit": 50000.0
    }
    res = client.post("/api/workflow/arbitrate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "optimized_total" in data
    assert "sub_carts" in data
    assert len(data["sub_carts"]) >= 1
    assert data["net_arbitrage_savings"] >= 0.0


def test_api_arbitrage_split():
    items = [
        {
            "id": "mon-1",
            "title": "Monitor 27",
            "brand": "LG",
            "model": "27UP",
            "category": "Monitor",
            "retailer": "Amazon",
            "base_price": 20000.0,
            "current_price": 18000.0,
            "original_mrp": 25000.0,
            "shipping_cost": 0.0,
            "in_stock": True,
            "rating": 4.5,
            "review_count": 500,
            "seller_name": "Appario"
        }
    ]
    res = client.post("/api/arbitrage/split", json=items)
    assert res.status_code == 200
    data = res.json()
    assert data["optimized_total"] > 0


def test_api_paypal_dossier_pdf_download():
    # 1. Create a dossier first
    create_res = client.post("/api/paypal/create-dossier", json={
        "order_id": "ORD-INTEGRATION-7711",
        "item_title": "MacBook Pro M3 Max",
        "platform": "Apple Official Store",
        "agreed_tco": 2499.00,
        "condition": "Brand New Factory Sealed",
        "open_box_verified": True,
        "seller_name": "Apple Certified Partner",
        "seller_rating": 4.9,
        "warranty_claims": "1-Year AppleCare Coverage",
        "display_currency": "USD"
    })
    assert create_res.status_code == 200
    
    # 2. Download via .pdf endpoint
    pdf_res1 = client.get("/api/paypal/dossiers/ORD-INTEGRATION-7711/download.pdf")
    assert pdf_res1.status_code == 200
    assert pdf_res1.headers["content-type"] == "application/pdf"
    assert pdf_res1.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_res1.content

    # 3. Download via /download/pdf endpoint
    pdf_res2 = client.get("/api/paypal/dossiers/ORD-INTEGRATION-7711/download/pdf")
    assert pdf_res2.status_code == 200
    assert pdf_res2.content.startswith(b"%PDF-1.4")

    # 4. On-demand synthetic download for unseeded order
    pdf_res3 = client.get("/api/paypal/dossiers/ORD-SYNTHETIC-8822/download.pdf")
    assert pdf_res3.status_code == 200
    assert pdf_res3.content.startswith(b"%PDF-1.4")

    # Clean up test artifact
    from backend.core.gcp_db import gcp_db_service
    gcp_db_service.delete_dossier("ORD-INTEGRATION-7711")
    gcp_db_service.delete_dossier("ORD-SYNTHETIC-8822")


def test_api_visual_verify():
    req = {
        "listing_id": "mon-lg-27-amz",
        "title": "LG 27UP650-W 4K UHD Monitor",
        "seller_name": "Appario Retail Direct",
        "packaging_seal_intact": True,
        "is_refurbished": False
    }
    res = client.post("/api/visual-verify", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["authenticity_grade"] == "GRADE_A_GENUINE"
    assert data["seal_integrity"] == "FACTORY_SEALED"


def test_api_volatility_and_snipe_lock():
    # Volatility
    vol_res = client.get("/api/volatility/mon-lg-27-amz")
    assert vol_res.status_code == 200
    vol_data = vol_res.json()
    assert vol_data["listing_id"] == "mon-lg-27-amz"
    assert len(vol_data["history"]) > 0

    # Snipe Lock
    lock_req = {
        "listing_id": "mon-lg-27-amz",
        "target_price": 21000.0,
        "auto_execute_within_seconds": 600
    }
    lock_res = client.post("/api/snipe/lock", json=lock_req)
    assert lock_res.status_code == 200
    lock_data = lock_res.json()
    assert lock_data["status"] == "SECURED_LOCKED"
    assert len(lock_data["receipt_hash"]) == 64


# ===========================================================================
# 6. Advanced Edge Cases & Hardening Tests
# ===========================================================================

def test_knapsack_unfulfilled_category_shortfall():
    agent = CartArbitrageurAgent()
    
    # 2 items in Monitor (available), 2 items in Webcam (BOTH OUT OF STOCK)
    candidates = [
        ProductListing(
            id="mon-1",
            title="LG 27 Monitor",
            brand="LG",
            model="27UP650",
            category="Monitor",
            retailer="Amazon",
            base_price=22000.0,
            current_price=20000.0,
            original_mrp=25000.0,
            shipping_cost=0.0,
            in_stock=True,
            rating=4.5,
            review_count=100,
            seller_name="Amazon Retail"
        ),
        ProductListing(
            id="cam-amz",
            title="Logitech Brio 4K",
            brand="Logitech",
            model="Brio",
            category="Webcam",
            retailer="Amazon",
            base_price=18000.0,
            current_price=16000.0,
            original_mrp=20000.0,
            shipping_cost=0.0,
            in_stock=False,  # OUT OF STOCK
            rating=4.3,
            review_count=80,
            seller_name="Amazon Retail"
        ),
        ProductListing(
            id="cam-fk",
            title="Logitech Brio 4K",
            brand="Logitech",
            model="Brio",
            category="Webcam",
            retailer="Flipkart",
            base_price=18500.0,
            current_price=16500.0,
            original_mrp=20000.0,
            shipping_cost=0.0,
            in_stock=False,  # OUT OF STOCK
            rating=4.2,
            review_count=50,
            seller_name="RetailNet"
        )
    ]

    res = agent.optimize_cart_split("Monitor and Webcam Setup", candidates)

    assert "Webcam" in res.unfulfilled_categories
    assert res.optimized_total > 0  # Monitor fulfilled
    assert len(res.sub_carts) == 1
    assert res.sub_carts[0].items[0].category == "Monitor"


def test_section13_pdf_generator_multiline_and_overflow_leaves():
    generator = Section13PDFGenerator()
    
    # Create 20 leaves and multiline descriptions with \r\n
    dossier_data = {
        "dossier_id": "DOSSIER-MULTI-9999",
        "order_id": "ORD-MULTI-9999",
        "item_title": "MacBook Pro M3 Max 16-inch Space Black with 128GB Unified Memory and 8TB SSD\nLine 2 Description\rLine 3 Extra",
        "agreed_tco": 4999.0,
        "advertised_condition": "Brand New\nSealed",
        "warranty_claims_evidence": "3-Year AppleCare+ with Theft and Loss Protection\nWorldwide Coverage",
        "leaves": [
            {
                "leaf_index": i,
                "leaf_type": f"SPEC_ASSERTION_{i}",
                "leaf_hash": f"abcdef{i:02d}" + "0" * 56,
                "summary": f"Leaf assertion proof index {i}\nwith multiline info"
            }
            for i in range(20)
        ]
    }

    pdf_bytes = generator.generate(dossier_data)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes
    assert b"additional Merkle leaves" in pdf_bytes
    # No unescaped carriage returns or raw newlines inside literal strings
    assert b"\r" not in pdf_bytes.split(b"stream\n")[1].split(b"\nendstream")[0]


@pytest.mark.asyncio
async def test_stealth_browser_empty_and_fallback():
    from backend.agents.stealth_browser import ExternalStealthBotBrowser
    res_empty = await ExternalStealthBotBrowser.verify_url_live("")
    assert res_empty["is_valid"] is False
    assert res_empty["reason"] == "Empty URL"
