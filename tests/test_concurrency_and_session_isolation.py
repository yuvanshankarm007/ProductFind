"""
Concurrency and Session-Scoped EventBus Isolation Test Suite.
Verifies that concurrent users running simultaneous searches or subscriptions do not
wipe, leak, or cross-contaminate each other's live negotiation logs.
"""

import pytest
import asyncio
from backend.core.bus import EventBus
from backend.coordinator import SentinelCoordinator

@pytest.mark.asyncio
async def test_session_scoped_eventbus_isolation():
    bus = EventBus()

    # Create two separate session scopes
    scope_a = bus.get_session_scope("session-alice-123")
    scope_b = bus.get_session_scope("session-bob-456")

    # Subscribe to each session
    queue_a = scope_a.subscribe()
    queue_b = scope_b.subscribe()

    # Emit on Session A
    await scope_a.emit(
        source="AliceAgent",
        target="AliceUI",
        event_type="DISPATCH",
        content="Alice is searching for Headphones"
    )

    # Emit on Session B
    await scope_b.emit(
        source="BobAgent",
        target="BobUI",
        event_type="DISPATCH",
        content="Bob is searching for Laptops"
    )

    # Queue A should receive Alice's event and NOT Bob's
    assert not queue_a.empty()
    ev_a = await queue_a.get()
    assert ev_a.source_agent == "AliceAgent"
    assert ev_a.content == "Alice is searching for Headphones"
    assert queue_a.empty(), "Session A should not receive any events from Session B"

    # Queue B should receive Bob's event and NOT Alice's
    assert not queue_b.empty()
    ev_b = await queue_b.get()
    assert ev_b.source_agent == "BobAgent"
    assert ev_b.content == "Bob is searching for Laptops"
    assert queue_b.empty(), "Session B should not receive any events from Session A"

    # Clear Session A only
    scope_a.clear()
    assert len(scope_a.get_logs()) == 0
    assert len(scope_b.get_logs()) == 1, "Clearing Session A must never clear Session B logs"

    # Unsubscribe
    scope_a.unsubscribe(queue_a)
    scope_b.unsubscribe(queue_b)

@pytest.mark.asyncio
async def test_concurrent_searches_session_isolation():
    """Verifies that two coordinators run concurrently without event collision."""
    bus = EventBus()
    coord_a = SentinelCoordinator(bus.get_session_scope("user-session-1"))
    coord_b = SentinelCoordinator(bus.get_session_scope("user-session-2"))

    # Execute concurrent searches
    task_a = coord_a.execute_search(query="Sony WH-1000XM5", session_id="user-session-1")
    task_b = coord_b.execute_search(query="Dell Latitude 5511", session_id="user-session-2")

    state_a, state_b = await asyncio.gather(task_a, task_b)

    assert state_a.is_complete is True
    assert state_b.is_complete is True
    assert "Sony" in state_a.search_query
    assert "Dell" in state_b.search_query

    # Verify session logs are segregated
    logs_a = [e.content for e in state_a.events]
    logs_b = [e.content for e in state_b.events]

    assert any("Sony" in log or "Scouts" in log for log in logs_a)
    assert any("Dell" in log or "Scouts" in log for log in logs_b)


@pytest.mark.asyncio
async def test_single_coordinator_session_tagging_and_rerank_isolation():
    """
    Verifies that a single global SentinelCoordinator properly tags all events
    with session_id and maintains isolated state per session across re-rankings.
    """
    from backend.schemas import RiskPreferences

    bus = EventBus()
    coord = SentinelCoordinator(bus)

    # 1. Search for User A and User B concurrently
    task_a = coord.execute_search(query="Sony WH-1000XM5", session_id="user-sess-alice")
    task_b = coord.execute_search(query="Dell Latitude 5511", session_id="user-sess-bob")
    state_a, state_b = await asyncio.gather(task_a, task_b)

    # 2. Check that events in bus are properly tagged with session_id
    alice_logs = bus.get_logs(session_id="user-sess-alice")
    bob_logs = bus.get_logs(session_id="user-sess-bob")

    assert len(alice_logs) > 0, "Alice's events must be tagged with user-sess-alice"
    assert len(bob_logs) > 0, "Bob's events must be tagged with user-sess-bob"

    for evt in alice_logs:
        assert evt.session_id == "user-sess-alice"
    for evt in bob_logs:
        assert evt.session_id == "user-sess-bob"

    # 3. Check re-rank isolation: Re-ranking Alice MUST NOT return Bob's results
    reranked_alice = await coord.re_rank_current_state(
        risk_prefs=RiskPreferences(warranty_priority=0.9),
        session_id="user-sess-alice"
    )
    assert reranked_alice is not None
    assert reranked_alice.session_id == "user-sess-alice"
    assert "Sony" in reranked_alice.search_query, f"Expected Sony search query for Alice, got {reranked_alice.search_query}"

    reranked_bob = await coord.re_rank_current_state(
        risk_prefs=RiskPreferences(speed_priority=0.9),
        session_id="user-sess-bob"
    )
    assert reranked_bob is not None
    assert reranked_bob.session_id == "user-sess-bob"
    assert "Dell" in reranked_bob.search_query, f"Expected Dell search query for Bob, got {reranked_bob.search_query}"
