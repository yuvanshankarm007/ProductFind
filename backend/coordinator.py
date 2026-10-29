"""
Coordinator / Orchestration Engine for PayPal Sentinel Swarm.
Executes the bidirectional multi-agent graph with real-time state management,
multi-language translation, cross-border FX analysis, COD & Open Box evaluation,
and AI price history prediction.
"""

import asyncio
from typing import Dict, Any, List
from .core.state import (
    BlackboardState,
    ScrapedListing,
    WarrantyAdpAnalysis,
    MerchantTrustRating,
    PayPalProtectionAssessment,
    CrossBorderFxDutyAnalysis,
    AnalyzedDealOption,
    UserPreferences,
    PriceAnalytics
)
from .core.bus import EventBus
from .core.i18n import translate
from .agents.fx_service import FXService
from .agents.price_predictor import PricePredictorAgent
from .agents.tier1_scouts import ScoutSwarm
from .agents.tier2_processors import ProcessingSwarm
from .agents.tier3_compilers import StrategyCompiler
from .paypal_service import PayPalService

class SentinelCoordinator:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.fx_svc = FXService()
        self.paypal_svc = PayPalService()
        self.scouts = ScoutSwarm(bus)
        self.processors = ProcessingSwarm(bus, self.scouts, self.fx_svc, self.paypal_svc)
        self.compiler = StrategyCompiler(bus, self.fx_svc)
        self.predictor = PricePredictorAgent(self.fx_svc)

    async def execute_search(
        self,
        query: str,
        language: str = "en",
        country: str = "US",
        currency: str = "USD",
        preferred_payment: str = "all",
        session_id: str = "sess-default"
    ) -> BlackboardState:
        """Executes the complete bidirectional multi-agent loop with full user preferences."""
        preferences = UserPreferences(
            language=language,
            country=country,
            currency=currency,
            preferred_payment=preferred_payment
        )

        state = BlackboardState(
            search_query=query,
            session_id=session_id,
            user_preferences=preferences
        )

        await self.bus.emit(
            source="Coordinator",
            target="Swarm",
            event_type="DISPATCH",
            content=f"Initiating Agent Swarm for '{query}' | Destination: {country} | Currency: {currency} | Lang: {language} | Payment: {preferred_payment}."
        )

        # 1. Tier 1: Scout Swarm (collect listings with delivery, COD, Open Box, Exchange offers)
        listings = await self.scouts.search(
            query=query,
            destination_country=preferences.country,
            language=preferences.language
        )
        state.raw_listings = listings

        # 2. Tier 2: Parallel Specialist Processing with Feedback Loops
        warranties: Dict[str, WarrantyAdpAnalysis] = {}
        trust_ratings: Dict[str, MerchantTrustRating] = {}
        cross_border_evals: Dict[str, CrossBorderFxDutyAnalysis] = {}
        paypal_evals: Dict[str, PayPalProtectionAssessment] = {}

        for listing in listings:
            # Analyze warranty & accidental damage (includes back-loop deep-scraping if ambiguous)
            w_analysis = await self.processors.analyze_warranty_and_adp(listing, language=preferences.language)
            warranties[listing.id] = w_analysis

            # Merchant trust, return policy, and restocking fees
            t_rating = await self.processors.evaluate_merchant_trust(listing, language=preferences.language)
            trust_ratings[listing.merchant] = t_rating

            # Cross-border FX, import duties, and card foreign transaction fee (3.5%) audit
            cb_analysis = await self.processors.evaluate_cross_border_fx_and_duties(listing, preferences)
            cross_border_evals[listing.id] = cb_analysis

            # PayPal protection synergy with 180-day guarantee and Pay in 4 terms
            p_eval = await self.processors.evaluate_paypal_synergy(
                listing,
                w_analysis,
                t_rating,
                cb_analysis,
                preferences
            )
            paypal_evals[listing.id] = p_eval

        state.warranty_analyses = warranties
        state.trust_ratings = trust_ratings
        state.cross_border_analyses = cross_border_evals
        state.paypal_evaluations = paypal_evals

        # 3. Price History and AI Prediction Swarm
        min_price = min((l.base_price for l in listings), default=300.0)
        converted_min_price = self.fx_svc.convert_amount(min_price, "USD", preferences.currency)
        price_analysis = self.predictor.analyze_price_history_and_predict(
            product_title=query,
            current_best_price=converted_min_price,
            target_currency=preferences.currency
        )
        state.price_analytics = price_analysis

        await self.bus.emit(
            source="PricePredictorAgent",
            target="CompilerSwarm",
            event_type="PRICE_PREDICT",
            content=translate(
                "price_prediction_log",
                lang=preferences.language,
                trend=price_analysis.price_trend,
                delta=price_analysis.prediction_delta_pct,
                verdict=price_analysis.buy_verdict,
                confidence=price_analysis.prediction_confidence
            ),
            payload=price_analysis.model_dump()
        )

        # 4. Tier 3: Strategy Compilation, Preferred Payment Alignment & Comparison Matrix
        final_options, comp_matrix = await self.compiler.compile_and_curate(
            listings=listings,
            warranties=warranties,
            trust_ratings=trust_ratings,
            cross_border_evals=cross_border_evals,
            paypal_evals=paypal_evals,
            preferences=preferences
        )
        state.final_options = final_options
        state.comparison_matrix = comp_matrix
        state.is_complete = True
        state.events = self.bus.get_logs()

        await self.bus.emit(
            source="Coordinator",
            target="ClientUI",
            event_type="RESOLVED",
            content=f"Bidirectional negotiation concluded. Synthesized {len(final_options)} curated options and comprehensive comparison matrix."
        )

        return state
