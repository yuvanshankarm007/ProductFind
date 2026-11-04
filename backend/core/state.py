"""
State and Data Models for ProductFind / PayPal Sentinel Multi-Agent Graph.
Represents the Shared Blackboard where bidirectional agents read, challenge, and update data.
Includes international cross-border FX, COD, Open Box delivery, price history/prediction, and multi-currency support.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import time


class UserPreferences(BaseModel):
    language: str = "en"  # en, hi, es, de, fr, ja
    country: str = "US"   # US, IN, GB, DE, CA, JP, AU
    currency: str = "USD" # USD, INR, EUR, GBP, CAD, JPY, AUD
    preferred_payment: str = "all"  # all, paypal, cod, card, upi


class ScrapedListing(BaseModel):
    id: str
    merchant: str
    merchant_domain: str
    product_title: str
    base_price: float
    shipping_cost: float = 0.0
    estimated_tax: float = 0.0
    currency: str = "USD"
    origin_country: str = "US"
    condition: str = "Brand New"  # Brand New, Refurbished - Grade A, Open Box, Grey Market
    seller_name: str
    is_third_party: bool = False
    in_stock: bool = True
    stock_status: str = "In Stock"  # "In Stock", "Out of Stock", "Pre-order", "Listing Expired / 404"
    is_dead_link: bool = False
    http_status: int = 200
    is_available: bool = True

    # Delivery & Transit Speed
    estimated_delivery_days: int = 2
    estimated_delivery_text: str = "2-3 business days"
    shipping_speed_tier: str = "Express"  # Next Day, Express, Standard, Cross-Border

    # Cash on Delivery (COD) & Doorstep Open Box Inspection
    cod_available: bool = False
    cod_fee: float = 0.0
    cod_terms: str = ""
    open_box_delivery: bool = False
    open_box_details: str = ""

    # Exchange & Trade-in policies
    exchange_offer_available: bool = False
    exchange_max_discount: float = 0.0
    exchange_terms: str = ""

    # Supported payment channels
    supported_payments: List[str] = Field(default_factory=lambda: ["PayPal", "Credit Card", "Pay in 4"])

    # Raw policy strings
    raw_warranty_text: str = ""
    raw_adp_text: str = ""
    raw_return_policy: str = ""
    listing_url: str = ""
    listing_url_type: str = "product"  # "product" (direct page) or "search" (search results page)

    # Autonomous Adaptive Skill Acquisition metadata
    is_auto_learned_skill: bool = False
    skill_id: Optional[str] = None
    skill_confidence: Optional[float] = None
    is_mock: bool = False


class WarrantyAdpAnalysis(BaseModel):
    listing_id: str
    oem_warranty_months: int = 12
    warranty_type: str = "Standard Manufacturer"  # OEM, Seller-Only, None, Grey Market
    has_adp: bool = False  # Accidental Damage Protection
    adp_provider: Optional[str] = None  # e.g., AppleCare+, GeekSquad, Allstate, Retail Partner
    adp_cost_included: bool = False
    adp_addon_price: float = 0.0
    covers_drops: bool = False
    covers_spills: bool = False
    deductible_per_claim: float = 0.0
    fine_print_warning: Optional[str] = None
    confidence_score: float = 1.0  # If < 0.8, triggers bidirectional back-propagation
    needs_deep_scrape: bool = False
    deep_scrape_query: Optional[str] = None


class MerchantTrustRating(BaseModel):
    merchant: str
    overall_score: int = Field(default=85, ge=0, le=100)  # 0 to 100
    trust_tier: str = "High"  # Verified Trusted, Reliable, Moderate Caution, High Risk
    public_rating: float = 4.5  # 1.0 to 5.0
    review_count: int = 1500
    is_authorized_reseller: bool = True
    return_window_days: int = 30
    restocking_fee_pct: float = 0.0
    dispute_risk_factor: str = "Low"  # Low, Moderate, High, Critical
    recurring_complaints: List[str] = Field(default_factory=list)
    positive_highlights: List[str] = Field(default_factory=list)


class CrossBorderFxDutyAnalysis(BaseModel):
    is_cross_border: bool = False
    merchant_country: str = "US"
    destination_country: str = "US"
    original_currency: str = "USD"
    target_currency: str = "USD"
    fx_rate: float = 1.0
    converted_base_price: float = 0.0
    estimated_import_duty_pct: float = 0.0
    estimated_import_duty_amount: float = 0.0
    foreign_card_surcharge_pct: float = 3.5
    foreign_card_surcharge_amount: float = 0.0
    card_foreign_fee_pct: float = 3.5
    card_foreign_fee_amount: float = 0.0
    paypal_conversion_rate: float = 1.0
    paypal_conversion_total: float = 0.0
    card_total_estimated: float = 0.0
    savings_with_paypal: float = 0.0
    paypal_fx_savings_or_shield: str = "No cross-border risk (domestic order)."
    recommendation: str = "Domestic order within destination country."


class PriceHistoryPoint(BaseModel):
    date: str
    price: float
    event_label: Optional[str] = None


class PricePredictionSparkline(BaseModel):
    points: List[float] = Field(default_factory=list)
    predicted_14d: float = 0.0


class PriceAnalytics(BaseModel):
    product_name: str = ""
    base_currency: str = "USD"
    target_currency: str = "USD"
    current_best_price: float = 0.0
    all_time_low: float = 0.0
    all_time_high: float = 0.0
    avg_90d_price: float = 0.0
    price_trend: str = "Stable"
    price_prediction_14d: str = "Stable"
    predicted_price: float = 0.0
    prediction_delta_pct: float = 0.0
    buy_verdict: str = "BUY NOW"
    prediction_confidence: int = 85
    prediction_explanation: str = ""
    history_points: List[PriceHistoryPoint] = Field(default_factory=list)
    sparkline: Union[List[float], PricePredictionSparkline] = Field(default_factory=list)
    is_fake_discount: bool = False
    claimed_msrp: Optional[float] = None


class PayPalProtectionAssessment(BaseModel):
    listing_id: str
    recommend_paypal: bool = True
    headline: str = "PayPal 180-Day Buyer Protection Active"
    explanation: str = ""
    buyer_protection_tier: str = "Full Restocking & Defect Shield"
    mitigated_risks: List[str] = Field(default_factory=list)
    pay_later_eligible: bool = True
    pay_in_4_biweekly: float = 0.0
    total_financed_with_adp: float = 0.0
    currency: str = "USD"


class AnalyzedDealOption(BaseModel):
    id: str
    listing: ScrapedListing
    warranty: WarrantyAdpAnalysis
    trust: MerchantTrustRating
    paypal: PayPalProtectionAssessment

    # Financials in original and user currency
    original_currency: str = "USD"
    display_currency: str = "USD"
    exchange_rate: float = 1.0
    total_cash_outlay: float = 0.0
    converted_cash_outlay: float = 0.0
    risk_adjusted_tco: float = 0.0

    # Enriched feature evaluations
    delivery_summary: str = ""
    cod_summary: str = ""
    open_box_summary: str = ""
    exchange_summary: str = ""
    cross_border: Optional[CrossBorderFxDutyAnalysis] = None

    # Payment preference matching
    matches_preferred_payment: bool = True
    payment_match_badge: Optional[str] = None

    recommendation_tier: str = "OPTIMAL_VALUE"  # "BUDGET_STICKER", "MAX_PROTECTION", "OPTIMAL_VALUE"
    tier_reason: str = ""
    rank: int = 1

    # Autonomous Adaptive Skill Acquisition
    is_auto_learned_skill: bool = False
    skill_id: Optional[str] = None
    skill_confidence: Optional[float] = None


class AgentNegotiationEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"EVT-{int(time.time()*1000)}")
    timestamp: Union[float, str] = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    source_agent: str
    target_agent: str
    event_type: str
    content: str
    payload: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class BlackboardState(BaseModel):
    search_query: str = ""
    clean_query: Optional[str] = None
    prompt_constraints: Optional[Dict[str, Any]] = None
    session_id: str = "sess-default"
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)
    is_complete: bool = False
    events: List[AgentNegotiationEvent] = Field(default_factory=list)
    raw_listings: List[ScrapedListing] = Field(default_factory=list)
    warranty_analyses: Dict[str, WarrantyAdpAnalysis] = Field(default_factory=dict)
    trust_ratings: Dict[str, MerchantTrustRating] = Field(default_factory=dict)
    paypal_evaluations: Dict[str, PayPalProtectionAssessment] = Field(default_factory=dict)
    cross_border_analyses: Dict[str, CrossBorderFxDutyAnalysis] = Field(default_factory=dict)
    price_analytics: Optional[PriceAnalytics] = None
    final_options: List[AnalyzedDealOption] = Field(default_factory=list)
    comparison_matrix: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @property
    def query(self) -> str:
        return self.search_query

    @property
    def warranties(self) -> Dict[str, WarrantyAdpAnalysis]:
        return self.warranty_analyses
