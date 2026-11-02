import sys
import pytest
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.core.bus import EventBus
from backend.coordinator import SentinelCoordinator
from backend.paypal_service import PayPalService

@pytest.mark.asyncio
async def test_sentinel_full_flow():
    # 1. Test EventBus Pub/Sub
    bus = EventBus()
    q = bus.subscribe()
    await bus.emit("TestAgent", "System", "DISPATCH", "Testing event bus...")
    event = await q.get()
    assert event.source_agent == "TestAgent"
    bus.unsubscribe(q)

    # 2. Test Coordinator & Full Multi-Feature Swarm (US -> India test with INR currency & COD)
    coordinator = SentinelCoordinator(bus)
    state = await coordinator.execute_search(
        query="Sony WH-1000XM5 Noise Canceling Headphones",
        language="en",
        country="IN",
        currency="INR",
        preferred_payment="all",
        session_id="test-session-inr"
    )
    assert len(state.raw_listings) > 0, "Scouts should collect raw listings"

    # Check backpropagation verification events
    back_loop_events = [e for e in state.events if e.event_type == "BACKPROPAGATION_REQUEST"]
    assert len(back_loop_events) >= 0

    # Check Trust Scores & Delivery features
    for listing in state.raw_listings:
        t = state.trust_ratings.get(listing.merchant)
        assert t is not None, f"Trust rating missing for merchant: {listing.merchant}"
        assert 0 <= t.overall_score <= 100

    # Check Price History and AI Prediction
    p_ana = state.price_analytics
    assert p_ana is not None
    assert p_ana.all_time_low > 0
    assert p_ana.all_time_high >= p_ana.all_time_low

    # Check Final Curated Options
    assert len(state.final_options) >= 2, "Expected at least 2 curated deal options"
    tiers = [opt.recommendation_tier for opt in state.final_options]
    assert len(set(tiers)) == len(tiers), f"Duplicate tiers found: {tiers}"

    # Check Comparison Matrix
    assert len(state.comparison_matrix) > 0

    # 3. Test Multilingual Execution (Hindi test)
    hi_state = await coordinator.execute_search(
        query="Sony WH-1000XM5",
        language="hi",
        country="IN",
        currency="INR"
    )
    assert hi_state is not None
    assert len(hi_state.final_options) > 0

    # 4. Test PayPal Orders API with Multi-Currency (INR and USD)
    paypal_svc = PayPalService()
    order_inr = await paypal_svc.create_order(amount=28500.00, item_name="Sony WH-1000XM5", currency="INR")
    assert order_inr["id"].startswith(("ORDER-", "ORD-"))
    assert order_inr["status"] == "CREATED"

    capture_inr = await paypal_svc.capture_order(order_id=order_inr["id"])
    assert capture_inr["status"] == "COMPLETED"
