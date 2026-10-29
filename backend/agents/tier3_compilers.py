"""
Tier 3: Compiler & Strategy Swarm.
Calculates Risk-Adjusted Total Cost of Ownership (TCO) in user-preferred currency,
evaluates COD, Open Box Delivery, Trade-in offers, matches preferred payments,
and synthesizes the side-by-side comparison matrix.
"""

from typing import List, Dict, Any, Tuple
from ..core.state import (
    ScrapedListing,
    WarrantyAdpAnalysis,
    MerchantTrustRating,
    PayPalProtectionAssessment,
    CrossBorderFxDutyAnalysis,
    AnalyzedDealOption,
    UserPreferences
)
from ..core.bus import EventBus
from ..core.i18n import translate
from .fx_service import FXService

class StrategyCompiler:
    def __init__(self, bus: EventBus, fx_svc: FXService):
        self.bus = bus
        self.fx = fx_svc

    async def compile_and_curate(
        self,
        listings: List[ScrapedListing],
        warranties: Dict[str, WarrantyAdpAnalysis],
        trust_ratings: Dict[str, MerchantTrustRating],
        cross_border_evals: Dict[str, CrossBorderFxDutyAnalysis],
        paypal_evals: Dict[str, PayPalProtectionAssessment],
        preferences: UserPreferences
    ) -> Tuple[List[AnalyzedDealOption], List[Dict[str, Any]]]:
        """
        Synthesizes raw listings and specialist analyses into final options.
        Performs mathematical TCO ranking with risk adjustments, payment alignment, and comparison matrix.
        """
        curr = preferences.currency.upper()
        lang = preferences.language

        await self.bus.emit(
            source="StrategyCompiler",
            target="StrategyCompiler",
            event_type="DISPATCH",
            content=f"Aggregating specialist agent outputs. Computing Multi-Currency Risk-Adjusted TCO in {curr}..."
        )

        analyzed_options: List[AnalyzedDealOption] = []
        comparison_matrix: List[Dict[str, Any]] = []

        pref_pay = preferences.preferred_payment.lower()

        for listing in listings:
            w = warranties.get(listing.id)
            t = trust_ratings.get(listing.merchant)
            p = paypal_evals.get(listing.id)
            cb = cross_border_evals.get(listing.id)

            if not w or not t or not p or not cb:
                continue

            # Original Landed Outlay in merchant currency
            orig_cash_outlay = round(listing.base_price + listing.shipping_cost + listing.estimated_tax, 2)
            
            # Converted Landed Outlay in target currency
            rate = self.fx.convert_amount(1.0, listing.currency, curr)
            converted_cash_outlay = round(orig_cash_outlay * rate, 2)

            # Risk-Adjusted TCO Calculation (calculated in target currency)
            # 1. Deductible exposure
            conv_deductible = round(w.deductible_per_claim * rate, 2)
            conv_base = round(listing.base_price * rate, 2)
            deductible_risk = conv_deductible * 0.25 if w.has_adp else (conv_base * 0.20)

            # 2. Restocking fee penalty risk
            restocking_risk = (conv_base * (t.restocking_fee_pct / 100.0)) * 0.15

            # 3. Grey market / unauthorized dealer penalty
            grey_market_penalty = (conv_base * 0.15) if not t.is_authorized_reseller else 0.0

            # 4. Merchant untrustworthiness penalty
            trust_penalty = max(0.0, (85.0 - t.overall_score) * 1.5 * (conv_base / 300.0))

            # 5. Open Box Delivery discount:
            # Having doorstep Open Box inspection cuts fraud / transit damage risk by $30 (or equivalent)
            open_box_risk_reduction = (conv_base * 0.06) if listing.open_box_delivery else 0.0

            # 6. Cross-Border duties and fees
            cross_border_addition = cb.estimated_import_duty_amount if cb.is_cross_border else 0.0

            # 7. PayPal Mitigation Discount:
            # Having PayPal Buyer Protection cuts dispute, return penalty, and cross-border risk exposure by 70%
            paypal_discount = (restocking_risk + trust_penalty + (cross_border_addition * 0.4)) * 0.70

            tco = round(
                converted_cash_outlay + deductible_risk + restocking_risk + 
                grey_market_penalty + trust_penalty + cross_border_addition - 
                open_box_risk_reduction - paypal_discount,
                2
            )

            # Payment match evaluation
            matches_payment = True
            payment_badge = None

            if pref_pay == "paypal":
                matches_payment = "PayPal" in listing.supported_payments or "Pay in 4" in listing.supported_payments
                if matches_payment:
                    payment_badge = "PayPal 180-Day Protection Ready"
            elif pref_pay == "cod":
                matches_payment = listing.cod_available
                if matches_payment:
                    payment_badge = "Cash on Delivery Available"
            elif pref_pay == "card":
                matches_payment = "Credit Card" in listing.supported_payments
                if matches_payment:
                    payment_badge = "Credit/Debit Card Accepted"
            elif pref_pay == "upi":
                matches_payment = "UPI" in listing.supported_payments
                if matches_payment:
                    payment_badge = "UPI Instant Doorstep Pay"

            # Formulate text summaries
            deliv_sum = f"{listing.estimated_delivery_text} ({listing.shipping_speed_tier})"
            cod_sum = "✅ Available at Doorstep" if listing.cod_available else "❌ Prepaid Online Only"
            open_box_sum = "✅ Doorstep Inspection Verified (OTP gating)" if listing.open_box_delivery else "❌ Standard Sealed Courier"
            
            ex_sum = "None"
            if listing.exchange_offer_available:
                conv_ex = round(listing.exchange_max_discount * rate, 2)
                ex_sum = f"✅ Up to {self.fx.format_price(conv_ex, curr)} Trade-In Bonus"

            deal_option = AnalyzedDealOption(
                id=listing.id,
                listing=listing,
                warranty=w,
                trust=t,
                paypal=p,
                original_currency=listing.currency,
                display_currency=curr,
                exchange_rate=rate,
                total_cash_outlay=orig_cash_outlay,
                converted_cash_outlay=converted_cash_outlay,
                risk_adjusted_tco=tco,
                delivery_summary=deliv_sum,
                cod_summary=cod_sum,
                open_box_summary=open_box_sum,
                exchange_summary=ex_sum,
                cross_border=cb,
                matches_preferred_payment=matches_payment,
                payment_match_badge=payment_badge,
                recommendation_tier="STANDARD",
                rank=1
            )
            analyzed_options.append(deal_option)

            # Row for full comparison matrix
            comparison_matrix.append({
                "id": listing.id,
                "merchant": listing.merchant,
                "domain": listing.merchant_domain,
                "condition": listing.condition,
                "origin_country": listing.origin_country,
                "destination_country": preferences.country,
                "is_cross_border": cb.is_cross_border,
                "sticker_price_orig": self.fx.format_price(listing.base_price, listing.currency),
                "sticker_price_conv": self.fx.format_price(conv_base, curr),
                "tco_conv": self.fx.format_price(tco, curr),
                "trust_score": f"{t.overall_score}/100 ({t.trust_tier})",
                "estimated_delivery": listing.estimated_delivery_text,
                "cod_available": listing.cod_available,
                "open_box_delivery": listing.open_box_delivery,
                "warranty_months": f"{w.oem_warranty_months} Mo. ({w.warranty_type})",
                "has_adp": w.has_adp,
                "adp_deductible": self.fx.format_price(conv_deductible, curr) if w.has_adp else "N/A",
                "return_window": f"{t.return_window_days} Days ({t.restocking_fee_pct}% restocking)",
                "exchange_offer": ex_sum,
                "supported_payments": listing.supported_payments,
                "matches_preferred_payment": matches_payment,
                "import_duty": f"{cb.estimated_import_duty_pct}% ({self.fx.format_price(cb.estimated_import_duty_amount, curr)})" if cb.is_cross_border else "0% (Domestic)",
                "paypal_protection": p.buyer_protection_tier
            })

        # Rank strategies
        # Filter or boost items matching preferred payment if specific payment chosen
        eligible_pool = analyzed_options
        if pref_pay != "all":
            matching = [opt for opt in analyzed_options if opt.matches_preferred_payment]
            if matching:
                eligible_pool = matching

        # Sort by TCO to identify best true value
        by_tco = sorted(eligible_pool, key=lambda x: x.risk_adjusted_tco)
        # Sort by protection (has ADP + highest trust)
        by_protection = sorted(
            eligible_pool,
            key=lambda x: (not x.warranty.has_adp, not x.warranty.covers_drops, -x.trust.overall_score)
        )
        # Sort by base price for sticker budget
        by_price = sorted(eligible_pool, key=lambda x: x.converted_cash_outlay)

        curated: List[AnalyzedDealOption] = []

        # 1. OPTIMAL VALUE CHAMPION (Lowest TCO & High Trust)
        optimal = by_tco[0]
        optimal.recommendation_tier = "OPTIMAL_VALUE"
        optimal.rank = 1
        curated.append(optimal)

        # 2. MAXIMUM PROTECTION (Full ADP + Best Warranty)
        max_protect = next((opt for opt in by_protection if opt.id != optimal.id), by_protection[0])
        max_protect.recommendation_tier = "MAX_PROTECTION"
        max_protect.rank = 2
        curated.append(max_protect)

        # 3. BUDGET STICKER (Lowest Initial Outlay)
        budget = next((opt for opt in by_price if opt.id != optimal.id and opt.id != max_protect.id), by_price[0])
        budget.recommendation_tier = "BUDGET_STICKER"
        budget.rank = 3
        curated.append(budget)

        await self.bus.emit(
            source="StrategyCompiler",
            target="ClientUI",
            event_type="SYNTHESIZED",
            content=f"Curated strategic options in {curr}: 1) Optimal Value ({optimal.listing.merchant}), 2) Max Protection ({max_protect.listing.merchant}), 3) Budget Sticker ({budget.listing.merchant}). Comparison matrix compiled for {len(comparison_matrix)} listings.",
            payload={"count": len(curated), "currency": curr}
        )

        return curated, comparison_matrix
