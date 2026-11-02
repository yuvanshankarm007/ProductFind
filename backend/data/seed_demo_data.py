"""
ProductFind Demo Seeder (demo-seeder skill).
Populates Google Cloud Firestore (or local persistence fallback) and exports
domain-specific rich mock data for judging demos.

Principles applied:
1. Domain Relevance: Real fintech (PayPal Section 13 claims, Pay in 4 schedules, Merkle trees)
   and real e-commerce stores (Amazon, IndiaMART, Croma, Flipkart, Best Buy, Newegg).
2. Timeline Spread: Recent timestamps spanning the past 90 days, 7 days, yesterday, and today.
3. Status Variety: 70% in-stock/verified, 20% in-progress/review, 10% out-of-stock/disputed/404.
4. Zero-Crash Integration: Populates GCP database layer and writes frontend/public/data/demo_seed.json.
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timedelta, timezone

# Ensure backend modules can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.core.gcp_db import gcp_db_service

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def generate_merkle_tree(elements: list) -> tuple:
    """Generates leaves and root hash for cryptographic dispute dossiers."""
    leaves = [sha256_hash(json.dumps(el, sort_keys=True)) for el in elements]
    if not leaves:
        return [], sha256_hash("EMPTY_DOSSIER")
    current_level = list(leaves)
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = sha256_hash(left + right)
            next_level.append(combined)
        current_level = next_level
    return leaves, current_level[0]

def build_demo_dataset():
    now = datetime.now(timezone.utc)

    # ==========================================
    # 1. AUTONOMOUS MERCHANT SKILLS (merchants_skills)
    # ==========================================
    merchant_skills = [
        {
            "skill_id": "skill_indiamart_v2",
            "merchant_domain": "indiamart.com",
            "merchant_name": "IndiaMART Certified Supplier",
            "learned_at": (now - timedelta(days=2)).isoformat(),
            "confidence_score": 0.96,
            "anti_bot_profile": "Chrome 124 TLS JA3 Fingerprint + Desktop Viewport",
            "selectors": {
                "price": ".bo-price, .price, .prod_price, [data-price]",
                "title": ".bo-title, h1.bo-heading, .prod_name",
                "stock": ".bo-avail, .stock_status, .instock",
                "warranty": ".bo-spec-warranty, .spec-table tr:contains('Warranty')"
            },
            "verified_in_stock": True,
            "cod_supported": True,
            "doorstep_openbox_verified": False,
            "sample_latency_ms": 420
        },
        {
            "skill_id": "skill_croma_v3",
            "merchant_domain": "croma.com",
            "merchant_name": "Croma Retail Direct",
            "learned_at": (now - timedelta(days=5)).isoformat(),
            "confidence_score": 0.98,
            "anti_bot_profile": "Standard HTTP/2 + Akamai Header Mimicry",
            "selectors": {
                "price": ".pdp-price, .amount, .new-price",
                "title": ".pdp-title, h1.product-title",
                "stock": ".btn-add-to-cart:not(:disabled)",
                "warranty": ".warranty-info, .brand-warranty"
            },
            "verified_in_stock": True,
            "cod_supported": True,
            "doorstep_openbox_verified": True,
            "sample_latency_ms": 310
        },
        {
            "skill_id": "skill_amazon_in_renewed",
            "merchant_domain": "amazon.in",
            "merchant_name": "Amazon Renewed (Verified Direct)",
            "learned_at": (now - timedelta(days=1)).isoformat(),
            "confidence_score": 0.99,
            "anti_bot_profile": "curl_cffi Chrome 124 Impersonate + Cookie Session",
            "selectors": {
                "price": ".a-price-whole, #priceblock_ourprice",
                "title": "#productTitle, .a-size-large.product-title-word-break",
                "stock": "#availability .a-color-success",
                "warranty": "#renewedWarrantyMessage, #RETURNS_POLICY"
            },
            "verified_in_stock": True,
            "cod_supported": True,
            "doorstep_openbox_verified": True,
            "sample_latency_ms": 280
        },
        {
            "skill_id": "skill_refurbishedpc_oos",
            "merchant_domain": "refurbishedpc.in",
            "merchant_name": "RefurbishedPC India",
            "learned_at": (now - timedelta(hours=6)).isoformat(),
            "confidence_score": 0.94,
            "anti_bot_profile": "Shopify Standard Webhook & DOM Gating",
            "selectors": {
                "price": ".price__regular .price-item--regular",
                "title": ".product__title h1",
                "stock": "button[name='add'][disabled] span:contains('Sold out')",
                "warranty": ".product__description"
            },
            "verified_in_stock": False,
            "stock_status": "Out of Stock (Sold Out)",
            "cod_supported": True,
            "doorstep_openbox_verified": False,
            "sample_latency_ms": 195
        },
        {
            "skill_id": "skill_newegg_global",
            "merchant_domain": "newegg.com",
            "merchant_name": "Newegg (Price Right Computers Store)",
            "learned_at": (now - timedelta(days=8)).isoformat(),
            "confidence_score": 0.97,
            "anti_bot_profile": "Cloudflare TLS Evasion + US Origin Gateway",
            "selectors": {
                "price": ".price-current strong, [itemprop='price']",
                "title": ".product-title",
                "stock": ".product-inventory strong:contains('In Stock')",
                "warranty": ".product-details-warranty"
            },
            "verified_in_stock": True,
            "cod_supported": False,
            "doorstep_openbox_verified": False,
            "sample_latency_ms": 520
        },
        {
            "skill_id": "skill_electronicsbazaar_404",
            "merchant_domain": "electronicsbazaar.com",
            "merchant_name": "Electronics Bazaar",
            "learned_at": (now - timedelta(days=12)).isoformat(),
            "confidence_score": 0.91,
            "anti_bot_profile": "Direct Scrape with 404 Discontinued SKU Gating",
            "selectors": {
                "price": ".price",
                "title": "h1.page-title",
                "stock": ".stock.unavailable",
                "warranty": ".warranty-tab"
            },
            "verified_in_stock": False,
            "stock_status": "Listing Expired / 404",
            "cod_supported": False,
            "doorstep_openbox_verified": False,
            "sample_latency_ms": 150
        }
    ]

    # ==========================================
    # 2. PAYPAL DISPUTE DOSSIERS (dispute_dossiers)
    # ==========================================
    dispute_dossiers = []

    # Case 1: Refurbished Grade Misrepresentation (SNAD)
    ev_case_1 = [
        {"type": "ORDER_RECEIPT", "item": "Dell Latitude 5511 (Grade A)", "amount": 26900.0, "currency": "INR", "date": (now - timedelta(days=4)).isoformat()},
        {"type": "UNBOXING_VIDEO_HASH", "sha256": "3fa85f647902ba9e77728d90c38493f4f8304930294801938501239850192841"},
        {"type": "INSPECTION_DIAGNOSTIC", "issue": "Deep chassis dents + battery health 68% (Violates Grade A guarantee)", "severity": "HIGH"},
        {"type": "SECTION_13_RULE", "policy": "Significantly Not As Described (SNAD) - Tier 1 Condition Misrepresentation"}
    ]
    leaves_1, root_1 = generate_merkle_tree(ev_case_1)
    dispute_dossiers.append({
        "dossier_id": "PP-DISP-8921-SNAD",
        "order_id": "ORD-DL-5511-901",
        "claimant_id": "user_rahul_m",
        "merchant": "IndiaMART Certified Supplier",
        "merchant_domain": "indiamart.com",
        "claim_reason": "SIGNIFICANTLY_NOT_AS_DESCRIBED",
        "claim_amount": 26900.0,
        "currency": "INR",
        "status": "REIMBURSEMENT_APPROVED",
        "underwriting_decision": "100% Full Refund issued under PayPal Buyer Protection Section 13. Pre-paid return shipping label generated.",
        "created_at": (now - timedelta(days=3)).isoformat(),
        "resolved_at": (now - timedelta(hours=14)).isoformat(),
        "merkle_root": root_1,
        "evidence_records": ev_case_1,
        "payout_status": "PAID"
    })

    # Case 2: Cross-Border Transit Damage without Open Box OTP
    ev_case_2 = [
        {"type": "CUSTOMS_DECLARATION", "carrier": "DHL Express", "origin": "US", "destination": "IN", "tracking": "DHL-9841289512"},
        {"type": "DAMAGE_REPORT", "carrier_timestamp": (now - timedelta(days=6)).isoformat(), "screen_shattered": True},
        {"type": "PAYPAL_SHIELD", "coverage": "Cross-Border Transit Damage Protection Section 13.4"}
    ]
    leaves_2, root_2 = generate_merkle_tree(ev_case_2)
    dispute_dossiers.append({
        "dossier_id": "PP-DISP-4102-XBORDER",
        "order_id": "ORD-NE-583-99",
        "claimant_id": "user_sarah_k",
        "merchant": "Newegg (Price Right Computers Store)",
        "merchant_domain": "newegg.com",
        "claim_reason": "DAMAGED_IN_TRANSIT",
        "claim_amount": 583.28,
        "currency": "USD",
        "status": "MERCHANT_INSPECTION_PENDING",
        "underwriting_decision": "Escalated to Newegg Verified Refurbisher. Funds held in PayPal Escrow pending carrier inspection.",
        "created_at": (now - timedelta(days=5)).isoformat(),
        "resolved_at": None,
        "merkle_root": root_2,
        "evidence_records": ev_case_2,
        "payout_status": "ESCROW_LOCKED"
    })

    # Case 3: Counterfeit Serial Number Detected (Pre-Emptive Claim Shield)
    ev_case_3 = [
        {"type": "SERIAL_CHECK", "serial": "SN-WH1000XM5-FAKE-091", "oem_database": "Sony Electronics", "match": "INVALID_CHECKSUM"},
        {"type": "SELLER_TRUST_FLAG", "domain": "shadytech-deals.biz", "risk_rating": 94}
    ]
    leaves_3, root_3 = generate_merkle_tree(ev_case_3)
    dispute_dossiers.append({
        "dossier_id": "PP-DISP-7719-FRAUD",
        "order_id": "ORD-SONY-FAKE-01",
        "claimant_id": "user_arjun_v",
        "merchant": "ShadyTech Liquidation Deals",
        "merchant_domain": "shadytech-deals.biz",
        "claim_reason": "COUNTERFEIT_MERCHANDISE",
        "claim_amount": 18500.0,
        "currency": "INR",
        "status": "IMMEDIATE_CHARGEBACK_SHIELD_ACTIVE",
        "underwriting_decision": "Pre-emptive refund authorized within 4 hours of payment. Seller blocked in Sentinel Swarm blackboard.",
        "created_at": (now - timedelta(days=1)).isoformat(),
        "resolved_at": (now - timedelta(hours=3)).isoformat(),
        "merkle_root": root_3,
        "evidence_records": ev_case_3,
        "payout_status": "PAID"
    })

    # ==========================================
    # 3. 90-DAY PRICE HISTORY & PREDICTIONS (price_cache)
    # ==========================================
    price_histories = {}

    # Dell Latitude 5511 (Renewed i7)
    dates_5511 = [(now - timedelta(days=d)).strftime("%b %d") for d in range(90, 0, -10)]
    prices_5511 = [36000, 35500, 34999, 34200, 33500, 32900, 31500, 32000, 26900]
    price_histories["renewed_dell_latitude_5511"] = {
        "product_name": "Dell Latitude 5511 15.6\" Business Laptop (i7-10850H / 16GB / 512GB)",
        "target_currency": "INR",
        "current_best_price": 26900.0,
        "all_time_low": 26000.0,
        "all_time_high": 38000.0,
        "avg_90d_price": 33100.0,
        "price_trend": "Dropping",
        "price_prediction_14d": "Slight Rebound Expected (+4%)",
        "predicted_price": 27900.0,
        "prediction_delta_pct": 3.7,
        "buy_verdict": "BUY NOW",
        "prediction_confidence": 92,
        "prediction_explanation": "IndiaMART supplier inventory at ₹26,900 is at a 90-day seasonal floor. Due to high enterprise demand and sold-out status on RefurbishedPC.in, secondary market prices are forecast to rebound within 14 days.",
        "history_points": [
            {"date": dates_5511[0], "price": prices_5511[0], "event_label": "Q3 Corporate Refresh"},
            {"date": dates_5511[2], "price": prices_5511[2], "event_label": "Pre-Festive High"},
            {"date": dates_5511[5], "price": prices_5511[5], "event_label": "Diwali Sale Offer"},
            {"date": dates_5511[7], "price": prices_5511[7], "event_label": "Batch Import Restock"},
            {"date": dates_5511[8], "price": prices_5511[8], "event_label": "Current Best In-Stock"}
        ]
    }

    # Sony WH-1000XM5
    dates_xm5 = [(now - timedelta(days=d)).strftime("%b %d") for d in range(90, 0, -10)]
    prices_xm5 = [32990, 31990, 29990, 28990, 26990, 29990, 27990, 28490, 26990]
    price_histories["sony_wh1000xm5"] = {
        "product_name": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
        "target_currency": "INR",
        "current_best_price": 26990.0,
        "all_time_low": 24990.0,
        "all_time_high": 34990.0,
        "avg_90d_price": 29400.0,
        "price_trend": "Stable",
        "price_prediction_14d": "Stable / Hold",
        "predicted_price": 26800.0,
        "prediction_delta_pct": -0.7,
        "buy_verdict": "GOOD DEAL",
        "prediction_confidence": 89,
        "prediction_explanation": "Prices are hovering within 2% of the Prime Day record low. Domestic bank card instant discounts (HDFC/ICICI) offer an additional ₹2,000 cash outlay reduction.",
        "history_points": [
            {"date": dates_xm5[0], "price": prices_xm5[0], "event_label": "MSRP Baseline"},
            {"date": dates_xm5[3], "price": prices_xm5[3], "event_label": "Festival Drop"},
            {"date": dates_xm5[4], "price": prices_xm5[4], "event_label": "Diwali Mega Sale"},
            {"date": dates_xm5[6], "price": prices_xm5[6], "event_label": "Post-Holiday Level"},
            {"date": dates_xm5[8], "price": prices_xm5[8], "event_label": "Current Best Deal"}
        ]
    }

    # ==========================================
    # 4. CUSTOMER ORDERS & PAY IN 4 SCHEDULES (orders)
    # ==========================================
    orders = [
        {
            "order_id": "ORD-2026-DL5511",
            "product_title": "Dell Latitude 5511 Business Laptop (Core i5 / 16GB / 512GB)",
            "merchant": "IndiaMART Certified Supplier",
            "total_amount": 26900.0,
            "currency": "INR",
            "payment_method": "PayPal Pay in 4",
            "pay_in_4_installments": [
                {"installment": 1, "due_date": "Today", "amount": 6725.0, "status": "PAID"},
                {"installment": 2, "due_date": (now + timedelta(days=14)).strftime("%d %b %Y"), "amount": 6725.0, "status": "UPCOMING"},
                {"installment": 3, "due_date": (now + timedelta(days=28)).strftime("%d %b %Y"), "amount": 6725.0, "status": "UPCOMING"},
                {"installment": 4, "due_date": (now + timedelta(days=42)).strftime("%d %b %Y"), "amount": 6725.0, "status": "UPCOMING"}
            ],
            "buyer_protection_active": True,
            "section_13_certificate_id": "CERT-PP-8819231",
            "shipping_carrier": "BlueDart Express",
            "tracking_number": "BD-982187319IN",
            "status": "DISPATCHED",
            "estimated_delivery": (now + timedelta(days=2)).strftime("%d %b %Y")
        },
        {
            "order_id": "ORD-2026-SONYXM5",
            "product_title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones (Silver)",
            "merchant": "Croma Retail Direct",
            "total_amount": 26990.0,
            "currency": "INR",
            "payment_method": "Cash on Delivery + Open Box Doorstep OTP",
            "buyer_protection_active": True,
            "section_13_certificate_id": "CERT-PP-7712903",
            "shipping_carrier": "Delhivery Surface",
            "tracking_number": "DEL-4109285012",
            "status": "DELIVERED_VERIFIED",
            "delivered_at": (now - timedelta(days=1)).strftime("%d %b %Y, %I:%M %p")
        }
    ]

    return {
        "merchant_skills": merchant_skills,
        "dispute_dossiers": dispute_dossiers,
        "price_histories": price_histories,
        "orders": orders
    }

def seed_all():
    print("🚀 Initializing ProductFind Demo Data Seeder...")
    dataset = build_demo_dataset()

    # 1. Seed Merchant Skills into GCP Database
    print(f"📦 Seeding {len(dataset['merchant_skills'])} Autonomous Merchant Skills...")
    for skill in dataset["merchant_skills"]:
        gcp_db_service.save_skill(skill["merchant_domain"], skill)
    print("   ✅ Merchant skills seeded.")

    # 2. Seed Dispute Dossiers into GCP Database
    print(f"📦 Seeding {len(dataset['dispute_dossiers'])} Cryptographic PayPal Dispute Dossiers...")
    for dos in dataset["dispute_dossiers"]:
        gcp_db_service.save_dossier(dos["order_id"], dos)
    print("   ✅ Dispute dossiers seeded.")

    # 3. Seed Price History Cache into GCP Database
    print(f"📦 Seeding {len(dataset['price_histories'])} 90-Day Price Trajectory Caches...")
    for key, hist in dataset["price_histories"].items():
        gcp_db_service.cache_prediction(key, hist)
    print("   ✅ Price trajectory cache seeded.")

    # 4. Seed Orders into GCP Database
    print(f"📦 Seeding {len(dataset['orders'])} Orders with PayPal Pay in 4 Schedules...")
    for ord_item in dataset["orders"]:
        gcp_db_service.save_order(ord_item["order_id"], ord_item)
    print("   ✅ Orders seeded.")

    # 5. Export Frontend Static JSON Seed for Zero-Latency First-Render
    frontend_data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "frontend", "public", "data", "demo_seed.json"
    )
    with open(frontend_data_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"   ✅ Exported frontend demo dataset to: {frontend_data_path}")

    # Database Status Report
    status = gcp_db_service.get_status()
    print("\n📊 Database Status Post-Seeding:")
    print(f"   Mode: {status['mode']}")
    print(f"   Cached Skills: {status['cached_skills_count']}")
    print(f"   Cached Dossiers: {status['cached_dossiers_count']}")
    print(f"   Active Collections: {status['active_collections']}")
    print(f"   Zero Crash Guarantee: {status['zero_crash_guarantee']}")
    print("\n🎉 Demo seeding completed successfully!")

if __name__ == "__main__":
    seed_all()
