"""
Swarm Lifecycle Hooks for ProductFind.
Inspired by Everything Claude Code (ECC) lifecycle hooks architecture.
Intercepts swarm transitions (pre_search, post_scout, pre_render) to enforce
zero-trust data sanity, sanitize links, apply learned prompt instincts, and log runtime metrics.
"""

from typing import List, Dict, Any, Optional
from .bus import EventBus
from .state import ScrapedListing, AnalyzedDealOption
from .agent_shield import commerce_agent_shield
from .instincts import commerce_instincts


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
        constraints: Optional[Any] = None
    ) -> List[ScrapedListing]:
        """Lifecycle hook executed immediately after Tier 1 scouts return."""
        sanitized: List[ScrapedListing] = []
        for l in listings:
            commerce_agent_shield.validate_listing(l, query=query, dest_country=dest_country)
            sanitized.append(l)

        # Apply Learned Prompt Instincts & Reflex Quarantine Engine
        verified_listings, quarantined = commerce_instincts.quarantine_filter_listings(sanitized, constraints=constraints)

        if quarantined:
            reasons_summary = ", ".join(f"{q['merchant']}: {q['reason']}" for q in quarantined[:3])
            await self.bus.emit(
                source="SelfHealer",
                target="ScoutSwarm",
                event_type="QUARANTINE_PRUNED",
                content=f"Self-Healer quarantined {len(quarantined)} listings based on learned instincts ({reasons_summary}).",
                payload={"quarantined_count": len(quarantined), "records": quarantined}
            )

        await self.bus.emit(
            source="LifecycleHook",
            target="ProcessingSwarm",
            event_type="LIFECYCLE_POST_SCOUT",
            content=f"AgentShield verified and quarantined listings: {len(verified_listings)} in-stock deals retained ({len(quarantined)} pruned).",
            payload={"verified_count": len(verified_listings), "quarantined_count": len(quarantined)},
        )
        return verified_listings

    async def pre_render(
        self,
        final_options: List[AnalyzedDealOption],
        query: str = "",
        dest_country: str = "IN",
        constraints: Optional[Any] = None
    ) -> List[AnalyzedDealOption]:
        """Lifecycle hook executed immediately before sending results to client."""
        retained: List[AnalyzedDealOption] = []
        quarantined: List[Dict[str, Any]] = []

        for opt in final_options:
            commerce_agent_shield.validate_listing(opt.listing, query=query, dest_country=dest_country)
            is_dead = getattr(opt.listing, "is_dead_link", False) or getattr(opt.listing, "http_status", 200) in (404, 410)
            is_oos = (not opt.listing.in_stock) or (not getattr(opt.listing, "is_available", True)) or ("out of stock" in str(opt.listing.stock_status).lower()) or ("notify me" in str(opt.listing.stock_status).lower())
            from ..agents.tier1_scouts import check_listing_hardware_compatibility
            is_hw_ok = check_listing_hardware_compatibility(query, opt.listing.product_title, opt.listing.listing_url)
            if is_dead:
                quarantined.append({"merchant": opt.listing.merchant, "reason": "Dead Link 404"})
            elif is_oos:
                quarantined.append({"merchant": opt.listing.merchant, "reason": "Out of Stock (Notify Me)"})
            elif not is_hw_ok:
                quarantined.append({"merchant": opt.listing.merchant, "reason": "Hardware Spec Mismatch"})
            else:
                is_q, reason = commerce_instincts.evaluate_and_quarantine(opt.listing, constraints=constraints)
                if is_q:
                    quarantined.append({"merchant": opt.listing.merchant, "reason": reason})
                else:
                    retained.append(opt)

        if quarantined:
            await self.bus.emit(
                source="SelfHealer",
                target="ClientUI",
                event_type="FINAL_QUARANTINE",
                content=f"Pre-render quarantine removed {len(quarantined)} strategic options violating learned rules.",
                payload={"count": len(quarantined), "quarantined": quarantined}
            )

        await self.bus.emit(
            source="LifecycleHook",
            target="ClientUI",
            event_type="LIFECYCLE_PRE_RENDER",
            content=f"Pre-render audit complete: {len(retained)} curated strategic deals verified in-stock, zero 404s, and sealed for display.",
            payload={"options_count": len(retained)},
        )
        return retained
