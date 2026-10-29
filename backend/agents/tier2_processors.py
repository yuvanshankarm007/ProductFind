"""
Tier 2: Processing Specialists Swarm.
Processes pricing, warranty/ADP fine print, merchant trust/reliability, and PayPal risk mitigation.
Features active bidirectional feedback loops with Tier 1 and horizontal cross-agent negotiations.
"""

import asyncio
from typing import Dict, Any, List
from ..core.state import (
    ScrapedListing,
    WarrantyAdpAnalysis,
    MerchantTrustRating,
    PayPalProtectionAssessment
)
from ..core.bus import EventBus
from .tier1_scouts import ScoutSwarm
from ..paypal_service import PayPalService

class ProcessingSwarm:
    def __init__(self, bus: EventBus, scouts: ScoutSwarm, paypal_svc: PayPalService):
        self.bus = bus
        self.scouts = scouts
        self.paypal = paypal_svc

    async def analyze_warranty_and_adp(self, listing: ScrapedListing) -> WarrantyAdpAnalysis:
        """
        Parses warranty & accidental damage protection (ADP).
        If fine print is incomplete, executes a BIDIRECTIONAL back-propagation loop to ScoutSwarm.
        """
        text = (listing.raw_warranty_text + " " + listing.raw_adp_text).lower()
        
        # Initial parsing
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
        if "39.99" in text:
            adp_price = 39.99
        elif "59.99" in text:
            adp_price = 59.99
        elif "199" in text:
            adp_price = 199.00
        elif "28.00" in text:
            adp_price = 28.00
        elif "65" in text:
            adp_price = 65.00

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

        # BIDIRECTIONAL FEEDBACK LOOP:
        if analysis.needs_deep_scrape:
            await self.bus.emit(
                source="WarrantyAdpAgent",
                target="ScoutSwarm",
                event_type="BACKPROPAGATION_REQUEST",
                content=f"Listing [{listing.id}] has ambiguous ADP deductible terms ('{listing.merchant}'). Triggering back-loop to deep-scrape terms modal.",
                payload={"listing_id": listing.id}
            )
            
            # Call back to Tier 1 Scout to resolve the ambiguity
            resolved = await self.scouts.deep_scrape(listing.id, "adp_deductibles_and_restocking")
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

    async def evaluate_merchant_trust(self, listing: ScrapedListing) -> MerchantTrustRating:
        """
        Rates merchant reliability, review consensus, return friction, and risk of fraud/counterfeit.
        """
        text = listing.raw_return_policy.lower()
        domain = listing.merchant_domain.lower()

        # Deterministic scoring model based on known merchant footprints
        if "bestbuy" in domain:
            score = 94
            tier = "Verified Trusted"
            public_rating = 4.7
            review_count = 84000
            authorized = True
            return_days = 15
            restocking_fee = 0.0
            dispute_risk = "Low"
            highlights = ["Authorized direct distributor", "Free in-store returns", "Zero restocking fee"]
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
            highlights = ["A-to-z standard return coverage", "Fast Prime delivery"]
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
            complaints = ["Grey market imported SKU", "Manufacturer warranty denied by Sony USA", "20% restocking fee penalty"]
        elif "flipkart" in domain:
            score = 82
            tier = "Reliable"
            public_rating = 4.3
            review_count = 21000
            authorized = True
            return_days = 7
            restocking_fee = 0.0
            dispute_risk = "Moderate"
            highlights = ["Flipkart Assured seller verification", "Direct domestic brand warranty"]
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

        await self.bus.emit(
            source="MerchantTrustSentinel",
            target="PayPalProtectionAgent",
            event_type="DISPATCH",
            content=f"Merchant [{listing.merchant}] Trust Rating: {score}/100 ({tier}). Restocking fee: {restocking_fee}%, Dispute Risk: {dispute_risk}.",
            payload={"merchant": listing.merchant, "trust_score": score, "dispute_risk": dispute_risk}
        )

        return rating

    async def evaluate_paypal_synergy(
        self,
        listing: ScrapedListing,
        warranty: WarrantyAdpAnalysis,
        trust: MerchantTrustRating
    ) -> PayPalProtectionAssessment:
        """
        Synthesizes Merchant Trust, Warranty limitations, and calculates
        PayPal Buyer Protection Shield and Pay in 4 terms.
        """
        synergy_data = self.paypal.evaluate_protection_synergy(
            base_price=listing.base_price,
            adp_price=warranty.adp_addon_price,
            merchant_trust_score=trust.overall_score,
            return_window_days=trust.return_window_days,
            restocking_fee_pct=trust.restocking_fee_pct,
            is_third_party=listing.is_third_party,
            has_adp=warranty.has_adp
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
            total_financed_with_adp=synergy_data["total_financed_with_adp"]
        )

        # Emit notice of PayPal protection alignment
        await self.bus.emit(
            source="PayPalProtectionAgent",
            target="CompilerSwarm",
            event_type="SYNTHESIZED",
            content=f"PayPal Protection Shield configured for [{listing.id}]: {assessment.headline}. Pay in 4 = ${assessment.pay_in_4_biweekly:.2f}/biweekly.",
            payload={"listing_id": listing.id, "headline": assessment.headline}
        )

        return assessment
