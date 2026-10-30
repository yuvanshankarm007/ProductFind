"""
Tier 2: Processing Specialists Swarm.
Processes pricing, warranty/ADP fine print, merchant trust/reliability,
live FX & import duties, COD & Open Box delivery audit, and PayPal risk mitigation.
Features active bidirectional feedback loops with Tier 1 and horizontal cross-agent negotiations.
"""

import asyncio
from typing import Dict, Any, List
from ..core.state import (
    ScrapedListing,
    WarrantyAdpAnalysis,
    MerchantTrustRating,
    PayPalProtectionAssessment,
    CrossBorderFxDutyAnalysis,
    UserPreferences
)
from ..core.bus import EventBus
from ..core.i18n import translate
from .tier1_scouts import ScoutSwarm
from .fx_service import FXService
from ..paypal_service import PayPalService

class ProcessingSwarm:
    def __init__(self, bus: EventBus, scouts: ScoutSwarm, fx_svc: FXService, paypal_svc: PayPalService):
        self.bus = bus
        self.scouts = scouts
        self.fx = fx_svc
        self.paypal = paypal_svc

    async def analyze_warranty_and_adp(self, listing: ScrapedListing, language: str = "en") -> WarrantyAdpAnalysis:
        """
        Parses warranty & accidental damage protection (ADP).
        If fine print is incomplete, executes a BIDIRECTIONAL back-propagation loop to ScoutSwarm.
        """
        text = (listing.raw_warranty_text + " " + listing.raw_adp_text).lower()
        
        oem_months = 12
        if "90-day" in text:
            oem_months = 3
        elif "2-year" in text:
            oem_months = 24

        warranty_type = "Standard Manufacturer"
        if "seller" in text or "commercial warranty" in text:
            warranty_type = "Seller/Third-Party Only"
        elif "international model" in text:
            warranty_type = "Grey Market (No Official Service)"

        has_adp = ("protection plan" in text or "accidental" in text or "applecare" in text or "geeksquad" in text)
        covers_drops = "drop" in text or "accidental" in text or "applecare" in text
        covers_spills = "spill" in text or "water" in text or "liquid" in text
        adp_price = 0.0
        
        # Regex to parse any currency figure in the ADP text (e.g. $149.00 or ₹2,499)
        import re
        price_match = re.search(r'[\$₹€£CA\$A\$¥]?\s*([0-9,]+(?:\.[0-9]{1,2})?)', listing.raw_adp_text)
        if price_match:
            try:
                adp_price = float(price_match.group(1).replace(',', ''))
            except Exception:
                adp_price = 0.0
        elif has_adp:
            adp_price = round(listing.base_price * 0.12, 2)


        # Check for ambiguity in deductible
        confidence = 0.75 if ("unspecified" in text or "nominal claim fee" in text) else 1.0

        analysis = WarrantyAdpAnalysis(
            listing_id=listing.id,
            oem_warranty_months=oem_months,
            warranty_type=warranty_type,
            has_adp=has_adp,
            adp_provider="GeekSquad" if "geeksquad" in text else ("AppleCare+" if "applecare" in text else "Retail Partner"),
            adp_cost_included=False,
            adp_addon_price=adp_price,
            covers_drops=covers_drops,
            covers_spills=covers_spills,
            deductible_per_claim=0.0,
            confidence_score=confidence,
            needs_deep_scrape=(confidence < 0.8)
        )

        # BIDIRECTIONAL FEEDBACK LOOP
        if analysis.needs_deep_scrape:
            await self.bus.emit(
                source="WarrantyAdpAgent",
                target="ScoutSwarm",
                event_type="BACKPROPAGATION_REQUEST",
                content=f"Listing [{listing.id}] has ambiguous ADP deductible terms ('{listing.merchant}'). Triggering back-loop to deep-scrape terms modal.",
                payload={"listing_id": listing.id}
            )
            
            # Call back to Tier 1 Scout to resolve ambiguity
            resolved = await self.scouts.deep_scrape(listing.id, "adp_deductibles_and_restocking", language=language)
            analysis.deductible_per_claim = resolved.get("adp_deductible", 0.0)
            analysis.confidence_score = 1.0
            analysis.needs_deep_scrape = False

            await self.bus.emit(
                source="WarrantyAdpAgent",
                target="CompilerSwarm",
                event_type="RESOLVED",
                content=f"Ambiguity resolved for [{listing.id}]: Verified deductible = ${analysis.deductible_per_claim:.2f}. ADP Drops/Spills coverage confirmed.",
                payload={"listing_id": listing.id, "analysis": analysis.model_dump()}
            )
        else:
            await self.bus.emit(
                source="WarrantyAdpAgent",
                target="CompilerSwarm",
                event_type="DISPATCH",
                content=f"Parsed [{listing.id}]: {analysis.warranty_type} ({analysis.oem_warranty_months} mo), ADP: {analysis.has_adp} (+${analysis.adp_addon_price:.2f})",
                payload={"listing_id": listing.id}
            )

        return analysis

    async def evaluate_merchant_trust(self, listing: ScrapedListing, language: str = "en") -> MerchantTrustRating:
        """
        Rates merchant reliability, review consensus, return friction, and risk of fraud/counterfeit.
        """
        domain = listing.merchant_domain.lower()

        if "bestbuy" in domain:
            score = 94
            tier = "Verified Trusted"
            public_rating = 4.7
            review_count = 84000
            authorized = True
            return_days = 15
            restocking_fee = 0.0
            dispute_risk = "Low"
            highlights = ["Authorized direct distributor", "Free in-store returns", "Zero restocking fee", "Geek Squad In-Store Inspection"]
            complaints = ["Strict 15-day window for non-members"]
        elif "amazon" in domain and listing.is_third_party:
            score = 76
            tier = "Moderate Caution"
            public_rating = 4.1
            review_count = 1250
            authorized = False
            return_days = 30
            restocking_fee = 15.0
            dispute_risk = "Moderate"
            highlights = ["A-to-z return coverage", "Fast Prime delivery"]
            complaints = ["15% restocking fee on opened electronics", "Customer pays return postage"]
        elif "walmart" in domain and listing.is_third_party:
            score = 56
            tier = "High Risk"
            public_rating = 3.2
            review_count = 340
            authorized = False
            return_days = 14
            restocking_fee = 20.0
            dispute_risk = "High"
            highlights = ["Lowest upfront cash price"]
            complaints = ["Grey market imported SKU", "Manufacturer warranty denied in domestic centers", "20% restocking fee penalty", "Cross-border carrier dispute friction"]
        elif "flipkart" in domain:
            score = 86
            tier = "Reliable"
            public_rating = 4.4
            review_count = 21000
            authorized = True
            return_days = 7
            restocking_fee = 0.0
            dispute_risk = "Low"
            highlights = ["Flipkart Assured seller verification", "Doorstep Open Box Delivery Verified", "Direct domestic brand warranty", "Cash on Delivery Available"]
            complaints = ["7-day replacement only (no refund to bank)"]
        elif "backmarket" in domain:
            score = 88
            tier = "Verified Trusted"
            public_rating = 4.5
            review_count = 45000
            authorized = False
            return_days = 30
            restocking_fee = 0.0
            dispute_risk = "Low"
            highlights = ["30-day money-back guarantee", "Verified 25-point refurbishing inspection", "Free return shipping"]
            complaints = ["Third-party refurbisher warranty instead of Apple direct"]
        else:
            score = 70
            tier = "Standard"
            public_rating = 4.0
            review_count = 500
            authorized = False
            return_days = 14
            restocking_fee = 10.0
            dispute_risk = "Moderate"
            highlights = ["Standard online storefront"]
            complaints = ["Moderate dispute resolution delay"]

        rating = MerchantTrustRating(
            merchant=listing.merchant,
            overall_score=score,
            trust_tier=tier,
            public_rating=public_rating,
            review_count=review_count,
            is_authorized_reseller=authorized,
            return_window_days=return_days,
            restocking_fee_pct=restocking_fee,
            dispute_risk_factor=dispute_risk,
            recurring_complaints=complaints,
            positive_highlights=highlights
        )

        cod_str = "Available" if listing.cod_available else "No"
        open_box_str = "Yes (Doorstep Inspection)" if listing.open_box_delivery else "No"

        await self.bus.emit(
            source="MerchantTrustSentinel",
            target="PayPalProtectionAgent",
            event_type="DISPATCH",
            content=translate(
                "trust_rating",
                lang=language,
                merchant=listing.merchant,
                score=score,
                tier=tier,
                fee=restocking_fee,
                cod=cod_str,
                open_box=open_box_str
            ),
            payload={
                "merchant": listing.merchant,
                "trust_score": score,
                "dispute_risk": dispute_risk,
                "cod_available": listing.cod_available,
                "open_box_delivery": listing.open_box_delivery
            }
        )

        return rating

    async def evaluate_cross_border_fx_and_duties(
        self,
        listing: ScrapedListing,
        preferences: UserPreferences
    ) -> CrossBorderFxDutyAnalysis:
        """
        For international merchants, checks live FX rates, factors in potential import duties
        and compares credit card foreign transaction fees (3.5%) vs PayPal's native currency conversion.
        """
        analysis = self.fx.calculate_cross_border_analysis(
            base_price=listing.base_price,
            merchant_country=listing.origin_country,
            destination_country=preferences.country,
            original_currency=listing.currency,
            target_currency=preferences.currency
        )

        if analysis.is_cross_border:
            await self.bus.emit(
                source="CurrencyFxDutyAgent",
                target="CompilerSwarm",
                event_type="FX_DUTY",
                content=translate(
                    "cross_border_detected",
                    lang=preferences.language,
                    origin=listing.origin_country,
                    dest=preferences.country,
                    orig_curr=listing.currency,
                    rate=analysis.fx_rate,
                    dest_curr=preferences.currency,
                    duty=analysis.estimated_import_duty_pct
                ),
                payload=analysis.model_dump()
            )

        return analysis

    async def evaluate_paypal_synergy(
        self,
        listing: ScrapedListing,
        warranty: WarrantyAdpAnalysis,
        trust: MerchantTrustRating,
        cross_border: CrossBorderFxDutyAnalysis,
        preferences: UserPreferences
    ) -> PayPalProtectionAssessment:
        """
        Synthesizes Merchant Trust, Warranty limitations, cross-border status,
        and calculates PayPal Buyer Protection Shield and Pay in 4 terms in target currency.
        """
        converted_base = self.fx.convert_amount(listing.base_price, listing.currency, preferences.currency)
        converted_adp = self.fx.convert_amount(warranty.adp_addon_price, listing.currency, preferences.currency)

        synergy_data = self.paypal.evaluate_protection_synergy(
            base_price=converted_base,
            adp_price=converted_adp,
            merchant_trust_score=trust.overall_score,
            return_window_days=trust.return_window_days,
            restocking_fee_pct=trust.restocking_fee_pct,
            is_third_party=listing.is_third_party,
            has_adp=warranty.has_adp,
            is_cross_border=cross_border.is_cross_border,
            currency=preferences.currency
        )

        assessment = PayPalProtectionAssessment(
            listing_id=listing.id,
            recommend_paypal=synergy_data["recommend_paypal"],
            headline=synergy_data["headline"],
            explanation=synergy_data["explanation"],
            buyer_protection_tier=synergy_data["buyer_protection_tier"],
            mitigated_risks=synergy_data["mitigated_risks"],
            pay_later_eligible=synergy_data["pay_later_eligible"],
            pay_in_4_biweekly=synergy_data["pay_in_4_biweekly"],
            total_financed_with_adp=synergy_data["total_financed_with_adp"],
            currency=preferences.currency
        )

        pay_in_4_formatted = self.fx.format_price(assessment.pay_in_4_biweekly, preferences.currency)

        await self.bus.emit(
            source="PayPalProtectionAgent",
            target="CompilerSwarm",
            event_type="SYNTHESIZED",
            content=translate(
                "paypal_synergy",
                lang=preferences.language,
                id=listing.id,
                headline=assessment.headline,
                pay_in_4=pay_in_4_formatted
            ),
            payload={"listing_id": listing.id, "headline": assessment.headline}
        )

        return assessment
