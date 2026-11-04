import pytest
import asyncio
from backend.core.bus import EventBus
from backend.coordinator import SentinelCoordinator
from backend.schemas import RiskPreferences

@pytest.mark.asyncio
async def test_horizontal_vertical_division_of_labour_flow():
    bus = EventBus()
    coord = SentinelCoordinator(bus)

    # 1. Vertical Execution Downward & Upward
    state = await coord.execute_search(
        query="renewed dell latitude 5511 core i7-10850h 16gb 512g",
        language="en",
        country="IN",
        currency="INR",
        preferred_payment="all"
    )

    assert state.is_complete is True
    assert len(state.raw_listings) >= 3
    assert len(state.final_options) >= 2

    # Check horizontal challenge and resolution events
    events = bus.get_logs()
    event_types = {e.event_type for e in events}
    sources = {e.source_agent for e in events}

    # Verify presence of Vertical and Horizontal Sub-Agents
    assert "DomesticScoutSubAgent" in sources
    assert "RefurbishedSpecialistSubAgent" in sources
    assert "StrategyCompiler" in sources or "StrategyCompilerSubAgent" in sources
    assert "CHALLENGE" in event_types

    # 2. Horizontal Re-arbitration & Dynamic Re-ranking
    # Boost warranty to 100% and drop speed to 0%
    re_ranked = await coord.re_rank_current_state(RiskPreferences(
        warranty_priority=1.0,
        speed_priority=0.0,
        trust_tolerance=0.9
    ))
    assert re_ranked is not None
    assert len(re_ranked.final_options) >= 2

    # 3. Targeted Bidirectional Challenge from Client
    target_id = state.raw_listings[0].id
    challenged_state = await coord.challenge_listing(target_id, "VERIFY_STOCK")
    assert challenged_state is not None

    challenged_warranty_state = await coord.challenge_listing(target_id, "AUDIT_WARRANTY")
    assert challenged_warranty_state is not None

    challenged_paypal_state = await coord.challenge_listing(target_id, "PAYPAL_SHIELD")
    assert challenged_paypal_state is not None

    challenged_spec_state = await coord.challenge_listing(target_id, "AUDIT_SPECS")
    assert challenged_spec_state is not None
