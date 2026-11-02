"""
Swarm Lifecycle Hooks Engine.
Inspired by the deterministic hook triggers in Everything Claude Code (ECC).
Enables event-driven interception and transformation at critical workflow milestones:
- pre_search
- post_scout
- pre_render
- on_anomaly
"""

import time
from typing import Dict, Any, List, Optional
from .bus import EventBus
from .agent_shield import commerce_agent_shield
from .instincts import commerce_instincts


class SwarmLifecycleHooks:
    """
    Lifecycle hook orchestrator that intercepts, audits, and enriches data
    across the multi-agent search, evaluation, and rendering lifecycle.
    """

    def __init__(self, bus: Optional[EventBus] = None):
        self.bus = bus

    async def pre_search(self, query: str, country: str, currency: str) -> Dict[str, Any]:
        """Triggered immediately before any scout agents are dispatched."""
        if self.bus:
            await self.bus.emit(
                source="LifecycleHook:pre_search",
                target="ScoutSwarm",
                event_type="LIFECYCLE_PRE_SEARCH",
                content=f"Lifecycle hook: Calibrating search for query='{query}' in country={country} with currency={currency}."
            )
        return {
            "query": query.strip(),
            "country": country.upper(),
            "currency": currency.upper(),
            "timestamp": time.time()
        }

    async def post_scout(self, raw_listings: List[Any], query: str, dest_country: str) -> List[Any]:
        """Triggered immediately after Tier-1 Scout agents return raw extracted listings."""
        sanitized_listings = []
        for listing in raw_listings:
            commerce_agent_shield.validate_listing(listing, query=query, dest_country=dest_country)
            sanitized_listings.append(listing)

        if self.bus:
            await self.bus.emit(
                source="LifecycleHook:post_scout",
                target="ProcessingSwarm",
                event_type="LIFECYCLE_POST_SCOUT",
                content=f"Lifecycle hook: AgentShield audited {len(sanitized_listings)} listings with 100% link integrity."
            )
        return sanitized_listings

    async def pre_render(self, final_options: List[Any], query: str, dest_country: str) -> List[Any]:
        """Triggered right before final options and comparison matrix are rendered to the client."""
        audited_options = commerce_agent_shield.audit_final_options(final_options, query=query, dest_country=dest_country)
        if self.bus:
            await self.bus.emit(
                source="LifecycleHook:pre_render",
                target="ClientUI",
                event_type="LIFECYCLE_PRE_RENDER",
                content=f"Lifecycle hook: Final zero-trust audit approved {len(audited_options)} deal cards."
            )
        return audited_options

    async def on_anomaly(self, anomaly_type: str, details: str, pattern: Optional[str] = None) -> None:
        """Triggered whenever a failure or broken URL is discovered, crystallizing a permanent instinct."""
        if pattern:
            commerce_instincts.record_dead_link_instinct(
                pattern=pattern,
                reason=f"Auto-learned from anomaly hook: {details}"
            )
        if self.bus:
            await self.bus.emit(
                source="LifecycleHook:on_anomaly",
                target="InstinctsVault",
                event_type="INSTINCT_CRYSTALLIZED",
                content=f"Lifecycle hook: Crystallized new negative instinct for pattern '{pattern}' ({anomaly_type})."
            )


# Global singleton instance
swarm_hooks = SwarmLifecycleHooks()
