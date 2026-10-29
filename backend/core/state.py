"""
State and Data Models for PayPal Sentinel Multi-Agent Graph.
Represents the Shared Blackboard where bidirectional agents read, challenge, and update data.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

class ScrapedListing(BaseModel):
    id: str
    merchant: str
    merchant_domain: str
    product_title: str
    base_price: float
    shipping_cost: float = 0.0
    estimated_tax: float = 0.0
    condition: str = "Brand New"  # Brand New, Refurbished - Grade A, Open Box, Grey Market
    seller_name: str
    is_third_party: bool = False
    raw_warranty_text: str = ""
    raw_adp_text: str = ""
    raw_return_policy: str = ""
    listing_url: str = ""

class WarrantyAdpAnalysis(BaseModel):
    listing_id: str
    oem_warranty_months: int = 12
    warranty_type: str = "Standard Manufacturer" # OEM, Seller-Only, None
    has_adp: bool = False  # Accidental Damage Protection
    adp_provider: Optional[str] = None  # e.g., AppleCare+, GeekSquad, Allstate/SquareTrade
    adp_cost_included: bool = False
    adp_addon_price: float = 0.0
    covers_drops: bool = False
    covers_spills: bool = False
    deductible_per_claim: float = 0.0
    fine_print_warning: Optional[str] = None
    confidence_score: float = 1.0  # If < 0.8, triggers back-loop query
    needs_deep_scrape: bool = False
    deep_scrape_query: Optional[str] = None

class MerchantTrustRating(BaseModel):
    merchant: str
    overall_score: int = Field(default=85, ge=0, le=100) # 0 to 100
    trust_tier: str = "High"  # Verified Trusted, Reliable, Caution, High Risk
    public_rating: float = 4.5  # 1.0 to 5.0
    review_count: int = 1500
    is_authorized_reseller: bool = True
    return_window_days: int = 30
    restocking_fee_pct: float = 0.0
    dispute_risk_factor: str = "Low"  # Low, Moderate, High, Critical
    recurring_complaints: List[str] = Field(default_factory=list)
    positive_highlights: List[str] = Field(default_factory=list)

class PayPalProtectionAssessment(BaseModel):
    listing_id: str
    recommend_paypal: bool = True
    headline: str = "PayPal Buyer Protection Shield Recommended"
    explanation: str = ""
    buyer_protection_tier: str = "Full Reimbursement Shield" # Full Reimbursement, Dispute Concierge, Standard
    mitigated_risks: List[str] = Field(default_factory=list)
    pay_later_eligible: bool = True
    pay_in_4_biweekly: float = 0.0
    total_financed_with_adp: float = 0.0

class AnalyzedDealOption(BaseModel):
    id: str
    listing: ScrapedListing
    warranty: WarrantyAdpAnalysis
    trust: MerchantTrustRating
    paypal: PayPalProtectionAssessment
    total_cash_outlay: float
    risk_adjusted_tco: float  # Mathematical TCO factoring in failure rates + deductibles + dispute risks
    recommendation_tier: str  # "BUDGET_STICKER", "MAX_PROTECTION", "OPTIMAL_VALUE"
    rank: int = 1

class AgentNegotiationEvent(BaseModel):
    id: str
    timestamp: float = Field(default_factory=time.time)
    source_agent: str
    target_agent: str
    event_type: str  # DISPATCH, CHALLENGE, BACKPROPAGATION_REQUEST, VERIFIED, RESOLVED, SYNTHESIZED
    content: str
    payload: Optional[Dict[str, Any]] = None

class BlackboardState(BaseModel):
    search_query: str
    session_id: str
    is_complete: bool = False
    events: List[AgentNegotiationEvent] = Field(default_factory=list)
    raw_listings: List[ScrapedListing] = Field(default_factory=list)
    warranty_analyses: Dict[str, WarrantyAdpAnalysis] = Field(default_factory=dict)
    trust_ratings: Dict[str, MerchantTrustRating] = Field(default_factory=dict)
    paypal_evaluations: Dict[str, PayPalProtectionAssessment] = Field(default_factory=dict)
    final_options: List[AnalyzedDealOption] = Field(default_factory=list)
