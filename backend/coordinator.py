"""
Coordinator / Orchestration Engine for PayPal Sentinel Swarm.
Executes the bidirectional multi-agent graph with real-time state management.
"""

import asyncio
from typing import Dict, Any, List
from .core.state import (
    BlackboardState,
    ScrapedListing,
    WarrantyAdpAnalysis,
    MerchantTrustRating,
    PayPalProtectionAssessment,
    AnalyzedDealOption
)
from .core.bus import EventBus
from .agents.tier1_scouts import ScoutSwarm
from .agents.tier2_processors import ProcessingSwarm
from .agents.tier3_compilers import StrategyCompiler
from .paypal_service import PayPalService

class SentinelCoordinator:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.paypal_svc = PayPalService()
        self.scouts = ScoutSwarm(bus)
        self.processors = ProcessingSwarm(bus, self.scouts, self.paypal_svc)
        self.compiler = StrategyCompiler(bus)

    async def execute_search(self, query: str, session_id: str = "sess-default") -> BlackboardState:
        """Executes the complete bidirectional multi-agent loop."""
        state = BlackboardState(search_query=query, session_id=session_id)

        await self.bus.emit(
            source="Coordinator",
            target="Swarm",
            event_type="DISPATCH",
            content=f"Initiating Bidirectional Agent Swarm for user query: '{query}'..."
        )

        # 1. Tier 1: Scout Swarm
        listings = await self.scouts.search(query)
        state.raw_listings = listings

        # 2. Tier 2: Parallel Specialist Processing with Feedback Loops
        warranties: Dict[str, WarrantyAdpAnalysis] = {}
        trust_ratings: Dict[str, MerchantTrustRating] = {}
        paypal_evals: Dict[str, PayPalProtectionAssessment] = {}

        for listing in listings:
            # Process warranty (includes back-loop if ambiguous)
            w_analysis = await self.processors.analyze_warranty_and_adp(listing)
            warranties[listing.id] = w_analysis

            # Process merchant trust
            t_rating = await self.processors.evaluate_merchant_trust(listing)
            trust_ratings[listing.merchant] = t_rating

            # Process PayPal protection synergy
            p_eval = await self.processors.evaluate_paypal_synergy(listing, w_analysis, t_rating)
            paypal_evals[listing.id] = p_eval

        state.warranty_analyses = warranties
        state.trust_ratings = trust_ratings
        state.paypal_evaluations = paypal_evals

        # 3. Tier 3: Strategy Compilation & Arbitration
        final_options = await self.compiler.compile_and_curate(
            listings=listings,
            warranties=warranties,
            trust_ratings=trust_ratings,
            paypal_evals=paypal_evals
        )
        state.final_options = final_options
        state.is_complete = True
        state.events = self.bus.get_logs()

        await self.bus.emit(
            source="Coordinator",
            target="ClientUI",
            event_type="RESOLVED",
            content=f"Bidirectional negotiation concluded successfully. Formulated {len(final_options)} strategic options."
        )

        return state
