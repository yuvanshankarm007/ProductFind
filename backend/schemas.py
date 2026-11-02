"""
Strict Pydantic v2 Data Contracts for ProductFind Sentinel.
Enforces type safety across all agent tiers: Scout → Processor → Compiler.
Prevents runtime KeyError / AttributeError crashes from missing or malformed fields.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# User Preference Vector
# ---------------------------------------------------------------------------

class RiskPreferences(BaseModel):
    """
    Dynamic preference weights that control TCO ranking.
    warranty_priority: 0 = ignore warranty, 1 = max weight on full warranty
    speed_priority:    0 = slow delivery is fine, 1 = penalise slow delivery heavily
    trust_tolerance:   0 = accept any seller, 1 = only high-trust authorised resellers
    """
    warranty_priority: float = Field(default=0.5, ge=0.0, le=1.0)
    speed_priority: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_tolerance: float = Field(default=0.7, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Scout-tier output (Tier 1)
# ---------------------------------------------------------------------------

class ProductCandidate(BaseModel):
    id: str
    title: str
    platform: str           # Amazon, Best Buy, Walmart, Flipkart …
    base_price: float
    currency: str = "USD"
    shipping_cost: float = 0.0
    estimated_tax: float = 0.0
    delivery_days: int = 3
    condition: str = "New"  # New, Refurbished, Open Box, Grey Market
    seller_name: str
    seller_rating: float = Field(default=4.5, ge=0.0, le=5.0)
    has_cod: bool = False
    cod_fee: float = 0.0
    open_box_verified: bool = False
    exchange_offer_available: bool = False
    exchange_max_discount: float = 0.0
    product_url: str = ""
    origin_country: str = "US"
    supported_payments: List[str] = Field(
        default_factory=lambda: ["PayPal", "Credit Card", "Pay in 4"]
    )
    is_mock: bool = False   # True when circuit-breaker substituted synthetic data


# ---------------------------------------------------------------------------
# Price Predictor output (Tier 2 — PricePredictorAgent)
# ---------------------------------------------------------------------------

class SparklineData(BaseModel):
    """11-point series: 10 historical samples + 1 predicted value, for AG Grid."""
    points: List[float] = Field(default_factory=list)
    predicted_14d: float = 0.0
    label: str = "14-Day Trend"


class PricePredictionResult(BaseModel):
    current_price: float
    claimed_msrp: float
    is_fake_discount: bool = False
    true_discount_pct: float = 0.0
    advertised_discount_pct: float = 0.0
    predicted_14d_price: float
    recommendation: str          # e.g. 'BUY NOW', 'WAIT', 'ALERT: Inflated MSRP'
    buy_verdict: str             # Short badge label
    prediction_confidence: int = Field(default=80, ge=0, le=100)
    sparkline: SparklineData = Field(default_factory=SparklineData)


# ---------------------------------------------------------------------------
# TCO Compiler output (Tier 3)
# ---------------------------------------------------------------------------

class TCOBreakdown(BaseModel):
    candidate_id: str
    title: str
    platform: str
    condition: str
    landed_cost: float          # base + shipping + tax, converted to display currency
    deductible_risk: float = 0.0
    restocking_risk: float = 0.0
    grey_market_penalty: float = 0.0
    trust_penalty: float = 0.0
    speed_penalty: float = 0.0
    warranty_benefit: float = 0.0
    open_box_reduction: float = 0.0
    cross_border_duty: float = 0.0
    paypal_discount: float = 0.0
    final_tco: float            # Sum of all components
    display_currency: str = "USD"
    trust_score: int = 85
    paypal_protected: bool = True
    badges: List[str] = Field(default_factory=list)
    prediction: Optional[PricePredictionResult] = None


# ---------------------------------------------------------------------------
# Dispute Evidence Dossier (PayPal Protection)
# ---------------------------------------------------------------------------

class DisputeDossier(BaseModel):
    dossier_id: str
    paypal_order_id: Optional[str] = None
    timestamp: str
    protection_policy: str = (
        "PayPal Buyer Protection — Item Significantly Not As Described / Item Not Received"
    )
    statutory_claim_reference: str = (
        "PayPal User Agreement § 13.2 (Significantly Not As Described) & § 13.1 (Item Not Received)"
    )
    item_title: str
    platform: str
    agreed_tco: float
    advertised_condition: str
    open_box_verified: bool
    seller_name: str
    seller_rating: float
    warranty_claims_evidence: str
    merkle_spec_hash: Optional[str] = None
    merkle_terms_hash: Optional[str] = None
    merkle_pricing_hash: Optional[str] = None
    cryptographic_hash: str
    evidence_status: str = "SEALED_AND_READY_FOR_DISPUTE"
    resolution_instructions: str = (
        "Submit this cryptographic dossier in the PayPal Resolution Center as "
        "unforgeable proof of the advertised condition and seller warranty terms."
    )


# ---------------------------------------------------------------------------
# Circuit-Breaker Scout Fallback Envelope
# ---------------------------------------------------------------------------

class ScoutResult(BaseModel):
    candidates: List[ProductCandidate] = Field(default_factory=list)
    live_scrape_succeeded: bool = True
    fallback_reason: Optional[str] = None
    scrape_duration_ms: float = 0.0
