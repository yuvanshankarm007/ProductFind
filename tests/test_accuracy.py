import sys
import pytest
import asyncio
import json
import hashlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.agents.price_predictor import SentinelPricePredictor
from backend.agents.fx_service import FXService
from backend.agents.web_scout_engine import LiveWebScoutEngine
from backend.paypal_service import PayPalEvidenceSentinel
from backend.core.bus import EventBus
from backend.coordinator import SentinelCoordinator
from backend.schemas import RiskPreferences

@pytest.mark.asyncio
async def test_econometric_price_prediction_accuracy():
    """Validates Z-Score fake-discount detection and FTC/Omnibus compliance."""
    # Case 1: Honest retail discount
    res_honest = SentinelPricePredictor.analyze_price_integrity(
        candidate_price=349.99,
        claimed_msrp=399.99,
        seed=100
    )
    assert not res_honest.is_fake_discount, "Honest $399 MSRP should not be flagged as fake"
    assert res_honest.advertised_discount_pct > 0.0

    # Case 2: Inflated Deceptive MSRP
    res_fake = SentinelPricePredictor.analyze_price_integrity(
        candidate_price=349.99,
        claimed_msrp=699.99,
        seed=100
    )
    assert res_fake.is_fake_discount, "Inflated $699 MSRP must be flagged as fake discount"
    assert res_fake.buy_verdict == "AVOID FAKE DISCOUNT"
    assert "ALERT: Inflated Reference MSRP Detected" in res_fake.recommendation

    # Case 3: 11-point Sparkline Verification
    assert len(res_honest.sparkline.points) == 11, "Sparkline must contain exactly 11 points (10 history + 1 forecast)"
    assert res_honest.sparkline.predicted_14d == res_honest.predicted_14d_price

@pytest.mark.asyncio
async def test_cross_border_cif_and_de_minimis_accuracy():
    """Validates WTO/CIF landed cost valuation and statutory de minimis rules."""
    fx = FXService()

    # Case 1: US Import under Section 321 De Minimis ($800) -> 0% Duty
    analysis_us = fx.calculate_cross_border_analysis(
        base_price=350.0,
        merchant_country="IN",
        destination_country="US",
        original_currency="USD",
        target_currency="USD",
        shipping_cost=25.0
    )
    assert analysis_us.is_cross_border
    assert analysis_us.estimated_import_duty_pct == 0.0, "US Import under $800 CIF must be duty-free under Section 321"
    assert analysis_us.estimated_import_duty_amount == 0.0

    # Case 2: India Import with BCD & SWS
    analysis_in = fx.calculate_cross_border_analysis(
        base_price=300.0,
        merchant_country="US",
        destination_country="IN",
        original_currency="USD",
        target_currency="INR",
        shipping_cost=30.0
    )
    assert analysis_in.is_cross_border
    assert analysis_in.estimated_import_duty_pct == 18.5
    assert analysis_in.estimated_import_duty_amount > 0.0

    # Case 3: UK Import under £135 threshold
    analysis_gb = fx.calculate_cross_border_analysis(
        base_price=90.0,
        merchant_country="US",
        destination_country="GB",
        original_currency="USD",
        target_currency="GBP",
        shipping_cost=15.0
    )
    assert analysis_gb.is_cross_border
    assert analysis_gb.estimated_import_duty_pct == 20.0, "UK import under £135 incurs 20% Import VAT and 0% tariff"

@pytest.mark.asyncio
async def test_semantic_query_spec_parsing_accuracy():
    """Validates deep hardware specification and exact MSRP extraction."""
    engine = LiveWebScoutEngine()

    # Case 1: iPhone 16 Pro 256GB
    sem_iphone = engine.get_semantic_profile("iPhone 16 Pro 256GB")
    assert sem_iphone["brand"] == "Apple"
    assert "256GB" in sem_iphone["title"]
    assert sem_iphone["base_usd"] >= 1099.0

    # Case 2: Sony WH-1000XM5
    sem_sony = engine.get_semantic_profile("Sony WH-1000XM5")
    assert sem_sony["brand"] == "Sony"
    assert "WH-1000XM5" in sem_sony["title"]
    assert sem_sony["base_usd"] == 399.99
    assert sem_sony["inr_baseline"] == 29990.00

    # Case 3: PlayStation 5 Slim Digital
    sem_ps5 = engine.get_semantic_profile("PlayStation 5 Slim Digital Edition")
    assert "Sony PlayStation" in sem_ps5["brand"]
    assert "Digital" in sem_ps5["title"]
    assert sem_ps5["base_usd"] == 449.99
    assert sem_ps5["inr_baseline"] == 44990.00

@pytest.mark.asyncio
async def test_merkle_cryptographic_dossier_accuracy():
    """Validates Merkle tree leaf hashing, root digest, and PayPal Section 13 citation."""
    dossier = PayPalEvidenceSentinel.create_dispute_dossier(
        order_id="ORD-TEST-9988-USD",
        item_title="Sony WH-1000XM5",
        platform="Best Buy",
        agreed_tco=349.99,
        condition="Brand New",
        open_box_verified=True,
        seller_name="Best Buy Official",
        seller_rating=4.8,
        warranty_claims="1 Year Official Sony Warranty + 2-Year GeekSquad ADP",
        display_currency="USD"
    )

    # Verify Merkle sub-hashes
    assert len(dossier.merkle_spec_hash) == 64
    assert len(dossier.merkle_terms_hash) == 64
    assert len(dossier.merkle_pricing_hash) == 64
    assert len(dossier.cryptographic_hash) == 64

    # Verify root hash matches the hash of the leaves + order_id + timestamp
    expected_root_payload = {
        "spec_hash": dossier.merkle_spec_hash,
        "terms_hash": dossier.merkle_terms_hash,
        "pricing_hash": dossier.merkle_pricing_hash,
        "order_id": dossier.paypal_order_id,
        "timestamp": dossier.timestamp
    }
    expected_root_hash = hashlib.sha256(json.dumps(expected_root_payload, sort_keys=True).encode("utf-8")).hexdigest()
    assert dossier.cryptographic_hash == expected_root_hash, "Root cryptographic hash must match Merkle leaf chaining"

    # Verify statutory claim reference
    assert "PayPal User Agreement § 13" in dossier.statutory_claim_reference

@pytest.mark.asyncio
async def test_multi_currency_tco_scaling_accuracy():
    """Validates multi-currency purchasing power parity and dynamic risk vector sensitivity."""
    bus = EventBus()
    coordinator = SentinelCoordinator(bus)

    state_usd = await coordinator.execute_search(
        query="Sony WH-1000XM5",
        country="US",
        currency="USD",
        risk_prefs=RiskPreferences(warranty_priority=0.5, speed_priority=0.5, trust_tolerance=0.7)
    )
    assert len(state_usd.final_options) > 0
    tco_usd = state_usd.final_options[0].risk_adjusted_tco

    state_usd_max_warranty = await coordinator.execute_search(
        query="Sony WH-1000XM5",
        country="US",
        currency="USD",
        risk_prefs=RiskPreferences(warranty_priority=1.0, speed_priority=0.0, trust_tolerance=0.5)
    )
    tco_max_warr = state_usd_max_warranty.final_options[0].risk_adjusted_tco
    opt1_by_id = {o.id: o for o in state_usd.final_options}
    matching_in_s2 = next((o for o in state_usd_max_warranty.final_options if o.id in opt1_by_id), None)
    if matching_in_s2:
        assert matching_in_s2.risk_adjusted_tco <= opt1_by_id[matching_in_s2.id].risk_adjusted_tco
    else:
        assert tco_max_warr <= tco_usd

    state_inr = await coordinator.execute_search(
        query="Sony WH-1000XM5",
        country="IN",
        currency="INR",
        risk_prefs=RiskPreferences(warranty_priority=0.5, speed_priority=0.5, trust_tolerance=0.7)
    )
    assert len(state_inr.final_options) > 0
    tco_inr = state_inr.final_options[0].risk_adjusted_tco
    assert tco_inr > 15000.0, f"Expected realistic INR TCO in >15,000 INR, got {tco_inr}"
