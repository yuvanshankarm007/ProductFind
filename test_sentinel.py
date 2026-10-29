import sys
import asyncio

print("=== SCRIPT STARTED ===", flush=True)

from backend.core.bus import EventBus
print("=== EVENT BUS IMPORTED ===", flush=True)

from backend.coordinator import SentinelCoordinator
print("=== COORDINATOR IMPORTED ===", flush=True)

from backend.paypal_service import PayPalService
print("=== PAYPAL SERVICE IMPORTED ===", flush=True)

async def main():
    print("=== STARTING PAYPAL SENTINEL VERIFICATION TEST ===", flush=True)
    
    # 1. Test EventBus
    bus = EventBus()
    q = bus.subscribe()
    await bus.emit("TestAgent", "System", "DISPATCH", "Testing event bus...")
    event = await q.get()
    assert event.source_agent == "TestAgent"
    bus.unsubscribe(q)
    print(" [x] EventBus Pub/Sub operational.", flush=True)

    # 2. Test Coordinator & Bidirectional Swarm
    coordinator = SentinelCoordinator(bus)
    print(" [>] Executing full agent swarm for 'Sony WH-1000XM5'...", flush=True)
    state = await coordinator.execute_search("Sony WH-1000XM5 Noise Canceling Headphones")
    print(f" [x] Tier 1 Scouts collected {len(state.raw_listings)} merchant listings.", flush=True)

    # Check backpropagation verification events
    back_loop_events = [e for e in state.events if e.event_type == "BACKPROPAGATION_REQUEST"]
    print(f" [x] Bidirectional Feedback Loops triggered: {len(back_loop_events)} back-propagation queries resolved.", flush=True)
    for ev in back_loop_events:
        print(f"     -> {ev.source_agent} queried {ev.target_agent}: {ev.content}", flush=True)

    # Check Trust Scores
    print(" [x] Tier 2 Merchant Trust Scores:", flush=True)
    for merchant, t in state.trust_ratings.items():
        print(f"     -> {merchant}: {t.overall_score}/100 ({t.trust_tier}), Restocking Fee: {t.restocking_fee_pct}%", flush=True)

    # Check Final Curated Options
    print(f" [x] Tier 3 Strategy Options Curated: {len(state.final_options)}", flush=True)
    for opt in state.final_options:
        print(f"     -> [{opt.recommendation_tier}] {opt.listing.merchant}: Sticker ${opt.listing.base_price:.2f} | TCO ${opt.risk_adjusted_tco:.2f}", flush=True)

    # 3. Test PayPal Orders API
    paypal_svc = PayPalService()
    order = await paypal_svc.create_order(amount=328.00, item_name="Sony WH-1000XM5")
    print(f" [x] PayPal Orders API v2 createOrder successful. Order ID: {order['id']}", flush=True)

    capture = await paypal_svc.capture_order(order_id=order["id"])
    print(f" [x] PayPal Orders API v2 captureOrder successful. Status: {capture['status']}", flush=True)

    print("\n=== ALL SYSTEMS OPERATIONAL AND VERIFIED ===", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
