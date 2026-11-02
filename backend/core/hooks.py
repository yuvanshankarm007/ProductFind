"""
Swarm Lifecycle Hooks for ProductFind.
Inspired by Everything Claude Code (ECC) lifecycle hooks architecture.
Intercepts swarm transitions (pre_search, post_scout, pre_render) to enforce
zero-trust data sanity, sanitize links, and log runtime metrics.
"""

from typing import List, Dict, Any, Optional
from .bus import EventBus
from .state import ScrapedListing, AnalyzedDealOption
from .agent_shield import commerce_agent_shield


class SwarmLifecycleHooks:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def pre_search(self, query: str, country: str, currency: str) -> Dict[str, Any]:
        """Lifecycle hook executed immediately before scouting dispatches."""
        calibration = {
            "query": query.strip(),
            "country": country.upper(),
            "currency": currency.upper(),
        }
        await self.bus.emit(
            source="LifecycleHook",
            target="Coordinator",
            event_type="LIFECYCLE_PRE_SEARCH",
            content=f"Calibrating swarm search parameters: query='{calibration['query']}', region={calibration['country']}, currency={calibration['currency']}.",
            payload=calibration,
        )
        return calibration

    async def post_scout(
        self,
        listings: List[ScrapedListing],
        query: str = "",
        dest_country: str = "IN",
    ) -> List[ScrapedListing]:
        """Lifecycle hook executed immediately after Tier 1 scouts return."""
        sanitized: List[ScrapedListing] = []
        for l in listings:
            commerce_agent_shield.validate_listing(l, query=query, dest_country=dest_country)
            sanitized.append(l)

        await self.bus.emit(
            source="LifecycleHook",
            target="ProcessingSwarm",
            event_type="LIFECYCLE_POST_SCOUT",
            content=f"AgentShield verified and sanitized {len(sanitized)} scraped listings against zero-trust criteria.",
            payload={"count": len(sanitized)},
        )
        return sanitized

    async def pre_render(
        self,
        final_options: List[AnalyzedDealOption],
        query: str = "",
        dest_country: str = "IN",
    ) -> List[AnalyzedDealOption]:
        """Lifecycle hook executed immediately before sending results to client."""
        for opt in final_options:
            commerce_agent_shield.validate_listing(opt.listing, query=query, dest_country=dest_country)

        await self.bus.emit(
            source="LifecycleHook",
            target="ClientUI",
            event_type="LIFECYCLE_PRE_RENDER",
            content=f"Pre-render audit complete: {len(final_options)} curated strategic deals sealed and ready for client display.",
            payload={"options_count": len(final_options)},
        )
        return final_options
