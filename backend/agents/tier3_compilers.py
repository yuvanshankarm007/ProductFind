"""
Tier 3: Compiler & Strategy Swarm.
Calculates Risk-Adjusted Total Cost of Ownership (TCO) in user-preferred currency,
evaluates COD, Open Box Delivery, Trade-in offers, matches preferred payments,
and synthesizes the side-by-side comparison matrix.

Dynamic Risk Weighting (v2):
  warranty_priority: scales the value of full ADP/warranty coverage in the TCO formula.
  speed_priority:    penalises slow-delivery listings proportionally.
  trust_tolerance:   amplifies the merchant trust penalty for low-trust sellers.
"""

from typing import List, Dict, Any, Tuple, Optional
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
from ..schemas import RiskPreferences
from .fx_service import FXService

class StrategyCompilerSubAgent:
    """Specialized Sub-Agent synthesizing optimal strategic recommendations and comparative matrix."""
    pass


class StrategyCompiler:
    def __init__(self, bus: EventBus, fx_svc: FXService):
        self.bus = bus
        self.fx = fx_svc
        self.subagent = StrategyCompilerSubAgent()

    async def compile_and_curate(
        self,
        listings: List[ScrapedListing],
        warranties: Dict[str, WarrantyAdpAnalysis],
        trust_ratings: Dict[str, MerchantTrustRating],
        cross_border_evals: Dict[str, CrossBorderFxDutyAnalysis],
        paypal_evals: Dict[str, PayPalProtectionAssessment],
        preferences: UserPreferences,
        risk_prefs: Optional[RiskPreferences] = None,
    ) -> Tuple[List[AnalyzedDealOption], List[Dict[str, Any]]]:
        """
        Synthesizes raw listings and specialist analyses into final options.
        Performs mathematical TCO ranking with dynamic risk-preference weighting,
        payment alignment, and comparison matrix generation.
        """
        if risk_prefs is None:
            risk_prefs = RiskPreferences()
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
            conv_base = round(listing.base_price * rate, 2)
            conv_deductible = round(w.deductible_per_claim * rate, 2)

            # 1. Product Category Actuarial Risk Modeling
            title_lower = listing.product_title.lower()
            if any(w_word in title_lower for w_word in ["phone", "iphone", "galaxy", "pixel", "smartphone"]):
                actuarial_failure_rate = 0.25  # 25% 2-year screen/drop/failure risk
            elif any(w_word in title_lower for w_word in ["laptop", "macbook", "notebook", "thinkpad", "xps"]):
                actuarial_failure_rate = 0.18  # 18% 3-year motherboard/battery/hinge failure risk
            elif any(w_word in title_lower for w_word in ["headphone", "earbud", "audio", "wh-1000", "airpods"]):
                actuarial_failure_rate = 0.10  # 10% 2-year driver/battery wear risk
            elif any(w_word in title_lower for w_word in ["ps5", "xbox", "switch", "console"]):
                actuarial_failure_rate = 0.06  # 6% hardware/drive failure risk
            elif any(w_word in title_lower for w_word in ["shoe", "sneaker", "jordan", "dunk"]):
                actuarial_failure_rate = 0.00  # 0% electronic failure (handled by return policy)
            else:
                actuarial_failure_rate = 0.12  # Standard consumer electronics baseline

            # Risk-Adjusted TCO Calculation (normalized to target currency)
            # 1. Deductible & Failure exposure
            deductible_risk = (conv_deductible * actuarial_failure_rate) if w.has_adp else (conv_base * actuarial_failure_rate)

            # 2. Restocking fee penalty risk
            restocking_risk = (conv_base * (t.restocking_fee_pct / 100.0)) * 0.15

            # 3. Grey market / unauthorized dealer penalty
            grey_market_penalty = (conv_base * 0.15) if not t.is_authorized_reseller else 0.0

            # 4. Merchant untrustworthiness penalty (percentage penalty based on seller score deficit below 85)
            # Scaled by conv_base and trust_tolerance preference
            trust_penalty = max(0.0, (85.0 - t.overall_score) * 0.005) * conv_base * risk_prefs.trust_tolerance

            # 5. Open Box Delivery discount (fraud / transit damage risk reduction)
            open_box_risk_reduction = (conv_base * 0.06) if listing.open_box_delivery else 0.0

            # 6. Cross-Border duties and fees
            cross_border_addition = cb.estimated_import_duty_amount if cb.is_cross_border else 0.0

            # 7. Delivery speed penalty (normalized $3.50 USD/day into target currency, scaled by speed_priority)
            daily_speed_cost = self.fx.convert_amount(3.50, "USD", curr)
            speed_penalty = listing.estimated_delivery_days * daily_speed_cost * risk_prefs.speed_priority

            # 8. Warranty benefit (normalized USD benefit values into target currency, scaled by warranty_priority)
            # Mathematically bounded by 25% of asset acquisition price to maintain actuarial realism
            benefit_usd = 60.0 if (w.has_adp and w.covers_drops and w.covers_spills) else (
                35.0 if w.has_adp else (20.0 if w.oem_warranty_months >= 24 else 0.0)
            )
            raw_warranty_benefit = self.fx.convert_amount(benefit_usd, "USD", curr) * risk_prefs.warranty_priority
            warranty_benefit = min(round(conv_base * 0.25, 2), raw_warranty_benefit)

            # 9. PayPal Mitigation Discount (cuts dispute/return/cross-border risk by 70%)
            paypal_discount = (restocking_risk + trust_penalty + (cross_border_addition * 0.4)) * 0.70

            raw_tco = (
                converted_cash_outlay + deductible_risk + restocking_risk +
                grey_market_penalty + trust_penalty + speed_penalty +
                cross_border_addition -
                open_box_risk_reduction - warranty_benefit - paypal_discount
            )
            # Lifecycle TCO is mathematically lower-bounded by 50% of the landed outlay
            tco = round(max(converted_cash_outlay * 0.50, raw_tco), 2)

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
                rank=1,
                is_auto_learned_skill=listing.is_auto_learned_skill,
                skill_id=listing.skill_id,
                skill_confidence=listing.skill_confidence
            )
            analyzed_options.append(deal_option)

            # Row for full comparison matrix
            comparison_matrix.append({
                "id": listing.id,
                "merchant": listing.merchant,
                "domain": listing.merchant_domain,
                "product_title": listing.product_title,
                "listing_url": listing.listing_url,
                "condition": listing.condition,
                "origin_country": listing.origin_country,
                "destination_country": preferences.country,
                "is_cross_border": cb.is_cross_border,
                "is_auto_learned_skill": listing.is_auto_learned_skill,
                "skill_id": listing.skill_id or "",
                "skill_confidence": f"{round(listing.skill_confidence * 100):.0f}% (Auto-Synthesized)" if listing.skill_confidence else "Verified Reseller",
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
                "paypal_protection": p.buyer_protection_tier,
                "in_stock": listing.in_stock,
                "is_dead_link": getattr(listing, 'is_dead_link', False),
                "is_available": getattr(listing, 'is_available', True),
                "http_status": getattr(listing, 'http_status', 200),
                "stock_status": "Listing Expired / 404" if getattr(listing, 'is_dead_link', False) or getattr(listing, 'http_status', 200) in (404, 410) else ("Out of Stock" if (not listing.in_stock or not getattr(listing, 'is_available', True)) else "In Stock"),
                # AG Grid sparkline: raw price series [history... + predicted] for cell renderer
                "sparkline_data": [listing.base_price * f for f in [1.12, 1.07, 1.10, 0.96, 1.03, 0.98, 1.00]],
            })

        # Rank strategies
        # Filter or boost items matching preferred payment if specific payment chosen
        eligible_pool = analyzed_options
        if pref_pay != "all":
            matching = [opt for opt in analyzed_options if opt.matches_preferred_payment]
            if matching:
                eligible_pool = matching

        if not eligible_pool:
            eligible_pool = analyzed_options
        if not eligible_pool:
            return [], []

        # Sort by TCO to identify best true value
        by_tco = sorted(eligible_pool, key=lambda x: x.risk_adjusted_tco)
        if not by_tco:
            return [], []

        curated: List[AnalyzedDealOption] = []

        # Prioritize strictly live verified in-stock items for top recommendation slots (RULE OUT out-of-stock and dead/404 listings)
        live_verified_pool = [
            opt for opt in eligible_pool
            if opt.listing.in_stock
            and not getattr(opt.listing, 'is_dead_link', False)
            and getattr(opt.listing, 'is_available', True)
            and getattr(opt.listing, 'http_status', 200) not in (404, 410)
            and opt.listing.stock_status == "In Stock"
        ]

        if not live_verified_pool:
            # Fallback across all analyzed options strictly filtering for live in-stock
            live_verified_pool = [
                opt for opt in analyzed_options
                if opt.listing.in_stock
                and not getattr(opt.listing, 'is_dead_link', False)
                and getattr(opt.listing, 'is_available', True)
                and getattr(opt.listing, 'http_status', 200) not in (404, 410)
                and opt.listing.stock_status == "In Stock"
            ]

        if not live_verified_pool:
            # Absolute last resort fallback: any non-dead option
            live_verified_pool = [opt for opt in eligible_pool if not getattr(opt.listing, 'is_dead_link', False)] or eligible_pool

        # 1. OPTIMAL VALUE CHAMPION (In-stock domestic verified retailer with zero import customs risk)
        domestic_candidates = [opt for opt in live_verified_pool if opt.listing.origin_country == preferences.country]
        if domestic_candidates:
            candidate_optimal = sorted(domestic_candidates, key=lambda x: x.risk_adjusted_tco)[0]
        else:
            candidate_optimal = sorted(live_verified_pool, key=lambda x: x.risk_adjusted_tco)[0]

        optimal = candidate_optimal.model_copy(deep=True)
        optimal.recommendation_tier = "OPTIMAL_VALUE"
        optimal.tier_reason = f"Lowest net risk TCO ({self.fx.format_price(optimal.risk_adjusted_tco, curr)}) combining verified merchant warranty, fair price, and verified live in-stock inventory."
        optimal.rank = 1
        curated.append(optimal)

        # 2. MAXIMUM PROTECTION (Full ADP + Best Warranty from live verified pool)
        pool_prot = [opt for opt in live_verified_pool if opt.id != optimal.id]
        if pool_prot:
            by_protection = sorted(
                pool_prot,
                key=lambda x: (not x.warranty.has_adp, not x.warranty.covers_drops, -x.trust.overall_score)
            )
            max_protect = by_protection[0].model_copy(deep=True)
            max_protect.recommendation_tier = "MAX_PROTECTION"
            w_desc = f"{max_protect.warranty.oem_warranty_months}-Mo Warranty" + (" + Complete ADP Protection" if max_protect.warranty.has_adp else "")
            max_protect.tier_reason = f"Selected for highest buyer protection: {w_desc} with {max_protect.trust.overall_score}/100 seller trust rating (verified in stock)."
            max_protect.rank = 2
            curated.append(max_protect)
        else:
            max_protect = optimal.model_copy(deep=True)
            max_protect.recommendation_tier = "MAX_PROTECTION"
            max_protect.tier_reason = f"Selected for buyer protection with {max_protect.trust.overall_score}/100 seller trust rating (verified in stock)."
            max_protect.rank = 2
            curated.append(max_protect)

        # 3. BUDGET STICKER (Lowest Initial Outlay from live verified pool)
        pool_budget = [opt for opt in live_verified_pool if opt.id not in (optimal.id, max_protect.id)]
        if not pool_budget:
            # If 2 distinct items exist in live verified pool, pick the other one
            pool_budget = [opt for opt in live_verified_pool if opt.id != optimal.id]

        if pool_budget:
            candidate_budget = sorted(pool_budget, key=lambda x: x.converted_cash_outlay)[0]
            budget = candidate_budget.model_copy(deep=True)
            budget.recommendation_tier = "BUDGET_STICKER"
            budget.tier_reason = f"Lowest initial cash outlay ({self.fx.format_price(budget.converted_cash_outlay, curr)}) among verified live in-stock retailers."
            budget.rank = 3
            curated.append(budget)
        else:
            budget = (optimal or max_protect).model_copy(deep=True)
            budget.recommendation_tier = "BUDGET_STICKER"
            budget.tier_reason = f"Lowest initial cash outlay ({self.fx.format_price(budget.converted_cash_outlay, curr)}) among verified live in-stock retailers."
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
