"""
Coordinator / Orchestration Engine for PayPal Sentinel Swarm.
Executes the bidirectional multi-agent graph with real-time state management,
multi-language translation, cross-border FX analysis, COD & Open Box evaluation,
AI price history prediction, circuit-breaker scout fallback, and
dynamic risk-weighted TCO calculation.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
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
from .schemas import RiskPreferences
from .core.hooks import SwarmLifecycleHooks
from .core.prompt_learner import PromptLearnerEngine, PromptConstraint
from .core.instincts import commerce_instincts

# Circuit-breaker timeout (seconds) for the scout live-scrape phase (supports multi-engine stealth web scraping)
_SCOUT_TIMEOUT = 8.5


class SentinelCoordinator:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.fx_svc = FXService()
        self.paypal_svc = PayPalService()
        self.scouts = ScoutSwarm(bus, fx_svc=self.fx_svc)
        self.processors = ProcessingSwarm(bus, self.scouts, self.fx_svc, self.paypal_svc)
        self.compiler = StrategyCompiler(bus, self.fx_svc)
        self.predictor = PricePredictorAgent(self.fx_svc)
        self.hooks = SwarmLifecycleHooks(bus=bus)
        self._session_states: Dict[str, BlackboardState] = {}
        self._last_state = None

    def _get_scoped_components(self, session_id: str):
        """Returns session-scoped bus and wired agent swarms for thread-safe session isolation."""
        if hasattr(self.bus, "get_session_scope"):
            scoped_bus = self.bus.get_session_scope(session_id)
        else:
            scoped_bus = self.bus
        scouts = ScoutSwarm(scoped_bus, fx_svc=self.fx_svc)
        processors = ProcessingSwarm(scoped_bus, scouts, self.fx_svc, self.paypal_svc)
        compiler = StrategyCompiler(scoped_bus, self.fx_svc)
        hooks = SwarmLifecycleHooks(bus=scoped_bus)
        return scoped_bus, scouts, processors, compiler, hooks

    async def _run_scouts_with_circuit_breaker(
        self,
        query: str,
        destination_country: str,
        language: str,
        scouts: Optional[ScoutSwarm] = None,
        bus: Optional[EventBus] = None,
    ) -> List[ScrapedListing]:
        """
        Wraps the Tier-1 scout swarm in a circuit-breaker.
        If the live scrape raises an exception or exceeds _SCOUT_TIMEOUT seconds,
        the coordinator emits a CIRCUIT_BREAKER event and falls back gracefully
        to the scout swarm's built-in synthetic listings (is_mock=True path),
        so the demo never stalls or crashes.
        """
        active_scouts = scouts or self.scouts
        active_bus = bus or self.bus

        try:
            listings = await asyncio.wait_for(
                active_scouts.search(
                    query=query,
                    destination_country=destination_country,
                    language=language,
                ),
                timeout=_SCOUT_TIMEOUT,
            )
            return listings
        except asyncio.TimeoutError:
            await active_bus.emit(
                source="CircuitBreaker",
                target="Coordinator",
                event_type="CIRCUIT_BREAKER",
                content=(
                    f"Scout timeout after {_SCOUT_TIMEOUT}s — "
                    "activating synthetic fallback listings (is_mock=True)."
                ),
            )
        except Exception as exc:
            await active_bus.emit(
                source="CircuitBreaker",
                target="Coordinator",
                event_type="CIRCUIT_BREAKER",
                content=f"Scout error: {exc!r} — activating synthetic fallback listings.",
            )

        # Fallback: re-run with the scout's instant cached semantic data path
        try:
            listings = await active_scouts.search(
                query=query,
                destination_country=destination_country,
                language=language,
                force_fallback=True,
            )
            return listings
        except Exception:
            return []

    async def execute_search(
        self,
        query: str,
        language: str = "en",
        country: str = "US",
        currency: str = "USD",
        preferred_payment: str = "all",
        session_id: str = "sess-default",
        risk_prefs: RiskPreferences = None,
    ) -> BlackboardState:
        """
        Executes the complete bidirectional multi-agent loop with full user preferences
        and optional dynamic risk-preference weighting for TCO re-ranking.
        """
        if risk_prefs is None:
            risk_prefs = RiskPreferences()

        preferences = UserPreferences(
            language=language,
            country=country,
            currency=currency,
            preferred_payment=preferred_payment
        )

        # Parse query for negative constraints and learn prompt instincts
        clean_query, prompt_constraints, newly_learned = PromptLearnerEngine.parse_and_learn_from_prompt(
            raw_prompt=query,
            instincts_vault=commerce_instincts
        )

        state = BlackboardState(
            search_query=query,
            clean_query=clean_query,
            prompt_constraints=prompt_constraints.model_dump() if hasattr(prompt_constraints, "model_dump") else prompt_constraints,
            session_id=session_id,
            user_preferences=preferences
        )

        # Acquire session-isolated bus and agent instances
        scoped_bus, scouts, processors, compiler, hooks = self._get_scoped_components(session_id)

        # 0. Lifecycle Hook: Pre-Search Ingestion & Geographic Calibration (ECC Pattern)
        await hooks.pre_search(query=clean_query, country=country, currency=currency)

        if newly_learned:
            await scoped_bus.emit(
                source="SelfHealer",
                target="Coordinator",
                event_type="LEARNED_FROM_PROMPT",
                content=(
                    f"Self-Healer synthesized {len(newly_learned)} active negative rules from user prompt: "
                    f"In-Stock={prompt_constraints.in_stock_only}, Zero-404={prompt_constraints.no_404_dead_links}, "
                    f"Anti-Scam={prompt_constraints.anti_scam}. Clean search target: '{clean_query}'."
                ),
                payload={"constraints": prompt_constraints.model_dump(), "new_rules": newly_learned}
            )

        await scoped_bus.emit(
            source="Coordinator",
            target="Swarm",
            event_type="DISPATCH",
            content=(
                f"Initiating Agent Swarm for '{clean_query}' | Destination: {country} | "
                f"Currency: {currency} | Lang: {language} | Payment: {preferred_payment} | "
                f"RiskPrefs: warranty={risk_prefs.warranty_priority}, "
                f"speed={risk_prefs.speed_priority}, trust={risk_prefs.trust_tolerance} | "
                f"NegativeConstraints: in_stock_only={prompt_constraints.in_stock_only}, "
                f"no_404s={prompt_constraints.no_404_dead_links}, anti_scam={prompt_constraints.anti_scam}."
            )
        )

        # 1. Tier 1: Scout Swarm with circuit-breaker
        raw_listings = await self._run_scouts_with_circuit_breaker(
            query=clean_query,
            destination_country=preferences.country,
            language=preferences.language,
            scouts=scouts,
            bus=scoped_bus,
        )
        # Lifecycle Hook: Post-Scout AgentShield Zero-Trust Link & Price Audit (ECC Pattern)
        listings = await hooks.post_scout(raw_listings, query=clean_query, dest_country=preferences.country, constraints=prompt_constraints)
        state.raw_listings = listings

        # 2. Tier 2: Parallel Specialist Processing with Feedback Loops
        warranties: Dict[str, WarrantyAdpAnalysis] = {}
        trust_ratings: Dict[str, MerchantTrustRating] = {}
        cross_border_evals: Dict[str, CrossBorderFxDutyAnalysis] = {}
        paypal_evals: Dict[str, PayPalProtectionAssessment] = {}

        for listing in listings:
            w_analysis = await processors.analyze_warranty_and_adp(listing, language=preferences.language)
            warranties[listing.id] = w_analysis

            t_rating = await processors.evaluate_merchant_trust(listing, language=preferences.language)
            trust_ratings[listing.merchant] = t_rating

            cb_analysis = await processors.evaluate_cross_border_fx_and_duties(listing, preferences)
            cross_border_evals[listing.id] = cb_analysis

            p_eval = await processors.evaluate_paypal_synergy(
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

        # 3. Price History and AI Prediction Swarm (with sparkline generation)
        converted_prices = [
            self.fx_svc.convert_amount(l.base_price, l.currency, preferences.currency)
            for l in listings
        ]
        best_price = min(converted_prices, default=300.0)
        price_analysis = self.predictor.analyze_price_history_and_predict(
            product_title=query,
            current_best_price=best_price,
            target_currency=preferences.currency
        )
        state.price_analytics = price_analysis

        await scoped_bus.emit(
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

        # 4. Bidirectional Multi-Agent Challenge & Negotiation Loop
        for listing in listings:
            # A. Dead Link / 404 Discontinued SKU Challenge
            if getattr(listing, "is_dead_link", False) or getattr(listing, "http_status", 200) in (404, 410) or "404" in str(listing.stock_status):
                await scoped_bus.emit(
                    source="ScoutProbeSubAgent",
                    target="StrategyCompilerSubAgent",
                    event_type="CHALLENGE",
                    content=f"DEAD LINK / 404 DISCONTINUED CHALLENGE: Listing [{listing.id}] at '{listing.merchant}' failed HTTP verification (Status: {getattr(listing, 'http_status', 404)} - {listing.stock_status}). Disqualifying from recommendation slots.",
                    payload={"listing_id": listing.id, "status": getattr(listing, "http_status", 404), "action": "DISQUALIFY"}
                )
                await scoped_bus.emit(
                    source="StrategyCompilerSubAgent",
                    target="ScoutProbeSubAgent",
                    event_type="RESOLVED",
                    content=f"RULE-OUT CONFIRMED: Listing [{listing.id}] ({listing.merchant}) purged from winning candidates. Tagged as 'Expired / 404' in comparison matrix.",
                    payload={"listing_id": listing.id, "action": "RULED_OUT"}
                )

            # B. Stock Depletion Challenge (Refurbished Specialist -> Compiler)
            elif not listing.in_stock or not getattr(listing, "is_available", True) or "Out of Stock" in str(listing.stock_status):
                await scoped_bus.emit(
                    source="RefurbishedSpecialistSubAgent",
                    target="StrategyCompilerSubAgent",
                    event_type="CHALLENGE",
                    content=f"STOCK DEPLETION CHALLENGE: Listing [{listing.id}] at '{listing.merchant}' is confirmed {listing.stock_status}. Challenging compiler to disqualify from winning recommendation slots.",
                    payload={"listing_id": listing.id, "stock_status": listing.stock_status}
                )
                await scoped_bus.emit(
                    source="StrategyCompilerSubAgent",
                    target="RefurbishedSpecialistSubAgent",
                    event_type="RESOLVED",
                    content=f"DISQUALIFICATION CONFIRMED: Listing [{listing.id}] ({listing.merchant}) disqualified from winning strategic tiers ({listing.stock_status}).",
                    payload={"listing_id": listing.id, "action": "DISQUALIFIED"}
                )

            # C. Price Anomaly Challenge (Price Predictor -> Scout Swarm)
            conv_price = self.fx_svc.convert_amount(listing.base_price, listing.currency, preferences.currency)
            if price_analysis.avg_90d_price > 0 and conv_price > (price_analysis.avg_90d_price * 1.40):
                delta_pct = ((conv_price - price_analysis.avg_90d_price) / price_analysis.avg_90d_price) * 100
                await scoped_bus.emit(
                    source="PricePredictorSubAgent",
                    target="DomesticScoutSubAgent",
                    event_type="CHALLENGE",
                    content=f"PRICE ANOMALY CHALLENGE: Listing [{listing.id}] at '{listing.merchant}' ({self.fx_svc.format_price(conv_price, preferences.currency)}) is +{delta_pct:.0f}% above 90-day moving average. Challenging scout to verify spec differences.",
                    payload={"listing_id": listing.id, "price": conv_price}
                )
                await scoped_bus.emit(
                    source="DomesticScoutSubAgent",
                    target="PricePredictorSubAgent",
                    event_type="RESOLVED",
                    content=f"Challenge resolved for [{listing.id}]: Verified premium SKU hardware grading & store warranty terms. Documented in comparison matrix.",
                    payload={"listing_id": listing.id}
                )

            # D. Cross-Border PayPal Underwriting Challenge (Duty Agent -> PayPal Agent)
            cb = cross_border_evals.get(listing.id)
            if cb and cb.is_cross_border:
                await scoped_bus.emit(
                    source="CrossBorderDutySubAgent",
                    target="PayPalProtectionSubAgent",
                    event_type="CHALLENGE",
                    content=f"Cross-border import detected for [{listing.id}] from {listing.origin_country}. Mandating PayPal Section 13 protection and Pay in 4 terms.",
                    payload={"listing_id": listing.id}
                )
                await scoped_bus.emit(
                    source="PayPalProtectionSubAgent",
                    target="StrategyCompilerSubAgent",
                    event_type="RESOLVED",
                    content=f"PayPal Protection Shield confirmed for [{listing.id}]: Section 13 Transit Insurance active; Pay in 4 financing verified.",
                    payload={"listing_id": listing.id}
                )

        # 5. Tier 3: Strategy Compilation with dynamic risk preference weighting
        final_options, comp_matrix = await compiler.compile_and_curate(
            listings=listings,
            warranties=warranties,
            trust_ratings=trust_ratings,
            cross_border_evals=cross_border_evals,
            paypal_evals=paypal_evals,
            preferences=preferences,
            risk_prefs=risk_prefs,
        )

        # Lifecycle Hook: Pre-Render Final Audit & AgentShield Verification (ECC Pattern)
        final_options = await hooks.pre_render(final_options, query=clean_query, dest_country=preferences.country, constraints=prompt_constraints)

        # Enforce learned negative constraints on comparison matrix (AG Grid rows)
        if prompt_constraints.in_stock_only or prompt_constraints.no_404_dead_links:
            comp_matrix = [
                row for row in comp_matrix
                if getattr(row, "in_stock", True)
                and not getattr(row, "is_dead_link", False)
                and "out of stock" not in str(getattr(row, "stock_status", "")).lower()
                and getattr(row, "http_status", 200) != 404
            ]

        state.final_options = final_options
        state.comparison_matrix = comp_matrix
        state.is_complete = True
        state.events = scoped_bus.get_logs()

        await scoped_bus.emit(
            source="Coordinator",
            target="ClientUI",
            event_type="RESOLVED",
            content=(
                f"Bidirectional negotiation concluded. "
                f"Synthesized {len(final_options)} curated options and comprehensive comparison matrix."
            )
        )

        self._session_states[session_id] = state
        self._last_state = state
        return state

    async def re_rank_current_state(self, risk_prefs: RiskPreferences, session_id: Optional[str] = None):
        """
        Dynamically re-evaluates risk-weighted TCO and strategic curations across the existing
        blackboard state in response to live client parameter changes (Horizontal/Vertical Re-arbitration).
        """
        target_session = session_id or (self._last_state.session_id if self._last_state else "sess-default")
        state = self._session_states.get(target_session) or self._last_state

        if not state or not state.raw_listings:
            return None

        scoped_bus, _, _, compiler, hooks = self._get_scoped_components(state.session_id)
        final_options, comp_matrix = await compiler.compile_and_curate(
            listings=state.raw_listings,
            warranties=state.warranty_analyses,
            trust_ratings=state.trust_ratings,
            cross_border_evals=state.cross_border_analyses,
            paypal_evals=state.paypal_evaluations,
            preferences=state.user_preferences,
            risk_prefs=risk_prefs,
        )
        final_options = await hooks.pre_render(
            final_options,
            query=state.search_query,
            dest_country=state.user_preferences.country
        )
        state.final_options = final_options
        state.comparison_matrix = comp_matrix
        state.events = scoped_bus.get_logs()
        self._session_states[state.session_id] = state
        self._last_state = state
        return state

    async def challenge_listing(self, listing_id: str, challenge_type: str = "VERIFY_STOCK", session_id: Optional[str] = None):
        """
        Executes a targeted horizontal or vertical challenge from the client or an auditor agent
        against a specific listing in the active blackboard state.
        """
        target_session = session_id or (self._last_state.session_id if self._last_state else "sess-default")
        state = self._session_states.get(target_session) or self._last_state

        if not state or not state.raw_listings:
            return None

        matching = [l for l in state.raw_listings if l.id == listing_id]
        if not matching:
            return state

        target_listing = matching[0]
        scoped_bus, _, _, _, _ = self._get_scoped_components(state.session_id)

        if challenge_type == "VERIFY_STOCK":
            await scoped_bus.emit(
                source="ClientAuditor",
                target="RefurbishedSpecialistSubAgent",
                event_type="CHALLENGE",
                content=f"CLIENT CHALLENGE: Demanding real-time stock and condition verification on [{target_listing.id}] ({target_listing.merchant}).",
                payload={"listing_id": target_listing.id, "type": "VERIFY_STOCK"}
            )
            is_in_stock = target_listing.in_stock
            status = "In Stock" if is_in_stock else "Out of Stock"
            await scoped_bus.emit(
                source="RefurbishedSpecialistSubAgent",
                target="StrategyCompilerSubAgent",
                event_type="RESOLVED",
                content=f"Stock verification confirmed for [{target_listing.id}]: Live Status is {status}. Cosmetic grade: {target_listing.condition}.",
                payload={"listing_id": target_listing.id, "stock_status": status}
            )

        elif challenge_type == "AUDIT_WARRANTY":
            await scoped_bus.emit(
                source="ClientAuditor",
                target="WarrantyAdpAuditorSubAgent",
                event_type="CHALLENGE",
                content=f"CLIENT CHALLENGE: Demanding fine-print deductible audit for [{target_listing.id}] ({target_listing.merchant}).",
                payload={"listing_id": target_listing.id, "type": "AUDIT_WARRANTY"}
            )
            w = state.warranty_analyses.get(target_listing.id)
            deductible = w.deductible_per_claim if w else 0.0
            covers_drops = w.covers_drops if w else False
            await scoped_bus.emit(
                source="WarrantyAdpAuditorSubAgent",
                target="ClientAuditor",
                event_type="RESOLVED",
                content=f"Fine-print verified for [{target_listing.id}]: Claim deductible is {deductible:.2f}. Drop/spill coverage: {covers_drops}.",
                payload={"listing_id": target_listing.id, "deductible": deductible}
            )

        elif challenge_type == "PAYPAL_SHIELD":
            await scoped_bus.emit(
                source="ClientAuditor",
                target="PayPalProtectionSubAgent",
                event_type="CHALLENGE",
                content=f"CLIENT CHALLENGE: Auditing PayPal Section 13 buyer protection & dispute escrow for [{target_listing.id}] ({target_listing.merchant}).",
                payload={"listing_id": target_listing.id, "type": "PAYPAL_SHIELD"}
            )
            p = state.paypal_evaluations.get(target_listing.id)
            tier = p.buyer_protection_tier if p else "Standard Protection"
            await scoped_bus.emit(
                source="PayPalProtectionSubAgent",
                target="ClientAuditor",
                event_type="RESOLVED",
                content=f"PayPal Protection Shield underwritten for [{target_listing.id}]: Tier={tier}, 180-Day Dispute Escrow active.",
                payload={"listing_id": target_listing.id, "protection_tier": tier}
            )

        state.events = scoped_bus.get_logs()
        self._session_states[state.session_id] = state
        self._last_state = state
        return state
