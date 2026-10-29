"""
Tier 3: Compiler & Strategy Swarm.
Calculates Risk-Adjusted Total Cost of Ownership (TCO), handles arbitration,
and synthesizes the final 3 curated options for the user.
"""

from typing import List, Dict, Any
from ..core.state import (
    ScrapedListing,
    WarrantyAdpAnalysis,
    MerchantTrustRating,
    PayPalProtectionAssessment,
    AnalyzedDealOption
)
from ..core.bus import EventBus

class StrategyCompiler:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def compile_and_curate(
        self,
        listings: List[ScrapedListing],
        warranties: Dict[str, WarrantyAdpAnalysis],
        trust_ratings: Dict[str, MerchantTrustRating],
        paypal_evals: Dict[str, PayPalProtectionAssessment]
    ) -> List[AnalyzedDealOption]:
        """
        Synthesizes raw listings and analyses into final options.
        Performs mathematical TCO ranking with risk adjustments.
        """
        await self.bus.emit(
            source="StrategyCompiler",
            target="StrategyCompiler",
            event_type="DISPATCH",
            content="Aggregating processing outputs. Computing Risk-Adjusted Total Cost of Ownership (TCO)..."
        )

        analyzed_options: List[AnalyzedDealOption] = []

        for listing in listings:
            w = warranties.get(listing.id)
            t = trust_ratings.get(listing.merchant)
            p = paypal_evals.get(listing.id)

            if not w or not t or not p:
                continue

            # Calculate Landed Cash Outlay
            cash_outlay = round(listing.base_price + listing.shipping_cost + listing.estimated_tax, 2)

            # Risk-Adjusted TCO Calculation
            # 1. Deductible exposure:
            deductible_risk = w.deductible_per_claim * 0.25 if w.has_adp else 80.0 # $80 uninsured risk if no ADP
            # 2. Restocking fee penalty risk:
            restocking_risk = (listing.base_price * (t.restocking_fee_pct / 100.0)) * 0.15
            # 3. Grey market / unauthorized dealer penalty:
            grey_market_penalty = 60.0 if not t.is_authorized_reseller else 0.0
            # 4. Merchant untrustworthiness multiplier:
            trust_penalty = max(0.0, (85.0 - t.overall_score) * 1.2)

            # PayPal Mitigation Discount:
            # Having PayPal Buyer Protection cuts dispute/restocking risk exposure by 70%
            paypal_discount = (restocking_risk + trust_penalty) * 0.70

            tco = round(cash_outlay + deductible_risk + restocking_risk + grey_market_penalty + trust_penalty - paypal_discount, 2)

            analyzed_options.append(
                AnalyzedDealOption(
                    id=listing.id,
                    listing=listing,
                    warranty=w,
                    trust=t,
                    paypal=p,
                    total_cash_outlay=cash_outlay,
                    risk_adjusted_tco=tco,
                    recommendation_tier="STANDARD",
                    rank=1
                )
            )

        # Sort by base price to identify cheapest sticker
        by_price = sorted(analyzed_options, key=lambda x: x.listing.base_price)
        # Sort by TCO to identify best true value
        by_tco = sorted(analyzed_options, key=lambda x: x.risk_adjusted_tco)
        # Sort by protection (has ADP + highest trust)
        by_protection = sorted(
            analyzed_options,
            key=lambda x: (not x.warranty.has_adp, not x.warranty.covers_drops, -x.trust.overall_score)
        )

        # Assign Distinct Curated Roles
        curated: List[AnalyzedDealOption] = []

        # 1. OPTIMAL VALUE CHAMPION (Lowest TCO & High Trust)
        optimal = by_tco[0]
        optimal.recommendation_tier = "OPTIMAL_VALUE"
        optimal.rank = 1
        curated.append(optimal)

        # 2. MAXIMUM PROTECTION (Full ADP + Best Warranty)
        # Pick best protection that isn't identical to optimal if possible
        max_protect = next((opt for opt in by_protection if opt.id != optimal.id), by_protection[0])
        max_protect.recommendation_tier = "MAX_PROTECTION"
        max_protect.rank = 2
        curated.append(max_protect)

        # 3. BUDGET STICKER (Lowest Initial Cash Outlay - Requires Caution)
        budget = next((opt for opt in by_price if opt.id != optimal.id and opt.id != max_protect.id), by_price[0])
        budget.recommendation_tier = "BUDGET_STICKER"
        budget.rank = 3
        curated.append(budget)

        await self.bus.emit(
            source="StrategyCompiler",
            target="ClientUI",
            event_type="SYNTHESIZED",
            content=f"Curated 3 strategic options: 1) Optimal Value ({optimal.listing.merchant}), 2) Max Protection ({max_protect.listing.merchant}), 3) Budget Sticker ({budget.listing.merchant}).",
            payload={"count": len(curated)}
        )

        return curated
