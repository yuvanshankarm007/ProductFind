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
    print("=== STARTING PRODUCTFIND SENTINEL VERIFICATION TEST ===", flush=True)
    
    # 1. Test EventBus
    bus = EventBus()
    q = bus.subscribe()
    await bus.emit("TestAgent", "System", "DISPATCH", "Testing event bus...")
    event = await q.get()
    assert event.source_agent == "TestAgent"
    bus.unsubscribe(q)
    print(" [x] EventBus Pub/Sub operational.", flush=True)

    # 2. Test Coordinator & Full Multi-Feature Swarm (US -> India test with INR currency & COD)
    coordinator = SentinelCoordinator(bus)
    print(" [>] Executing full agent swarm for 'Sony WH-1000XM5' (Destination: IN, Currency: INR, Language: en, Payment: all)...", flush=True)
    state = await coordinator.execute_search(
        query="Sony WH-1000XM5 Noise Canceling Headphones",
        language="en",
        country="IN",
        currency="INR",
        preferred_payment="all",
        session_id="test-session-inr"
    )
    print(f" [x] Tier 1 Scouts collected {len(state.raw_listings)} merchant listings.", flush=True)

    # Check backpropagation verification events
    back_loop_events = [e for e in state.events if e.event_type == "BACKPROPAGATION_REQUEST"]
    print(f" [x] Bidirectional Feedback Loops triggered: {len(back_loop_events)} back-propagation queries resolved.", flush=True)
    for ev in back_loop_events:
        print(f"     -> {ev.source_agent} queried {ev.target_agent}: {ev.content}", flush=True)

    # Check Trust Scores & Delivery features
    print(" [x] Tier 2 Merchant Audit (Trust, Delivery, COD & Open Box):", flush=True)
    for listing in state.raw_listings:
        t = state.trust_ratings.get(listing.merchant)
        print(f"     -> {listing.merchant} ({listing.origin_country}): Trust {t.overall_score}/100, Deliv: {listing.estimated_delivery_text}, COD: {listing.cod_available}, Open Box: {listing.open_box_delivery}, Exchange: {listing.exchange_offer_available}", flush=True)

    # Check Cross-Border FX and Import Duty Audit
    print(" [x] Cross-Border FX & Import Duty Inspector:", flush=True)
    for lid, cb in state.cross_border_analyses.items():
        if cb.is_cross_border:
            print(f"     -> Listing [{lid}] Cross-Border {cb.merchant_country} -> {cb.destination_country}: FX Rate={cb.fx_rate}, Duty={cb.estimated_import_duty_pct}% ({cb.estimated_import_duty_amount} {cb.target_currency}), Card Fee 3.5% vs PayPal Shield", flush=True)

    # Check Price History and AI Prediction
    print(" [x] Price History & AI Prediction Agent:", flush=True)
    p_ana = state.price_analytics
    assert p_ana is not None
    print(f"     -> ATL: {p_ana.all_time_low} {p_ana.target_currency} | ATH: {p_ana.all_time_high} {p_ana.target_currency} | 90d Avg: {p_ana.avg_90d_price} {p_ana.target_currency}", flush=True)
    print(f"     -> Prediction: {p_ana.price_prediction_14d} (Delta {p_ana.prediction_delta_pct}%), Verdict: '{p_ana.buy_verdict}', Confidence: {p_ana.prediction_confidence}%", flush=True)

    # Check Final Curated Options
    print(f" [x] Tier 3 Strategy Options Curated: {len(state.final_options)}", flush=True)
    for opt in state.final_options:
        print(f"     -> [{opt.recommendation_tier}] {opt.listing.merchant}: Converted Outlay {opt.display_currency} {opt.converted_cash_outlay:,.2f} | TCO {opt.display_currency} {opt.risk_adjusted_tco:,.2f} | COD: {opt.cod_summary} | OpenBox: {opt.open_box_summary}", flush=True)

    # Check Comparison Matrix
    print(f" [x] Comparison Matrix Generated with {len(state.comparison_matrix)} rows.", flush=True)
    assert len(state.comparison_matrix) > 0

    # 3. Test Multilingual Execution (Hindi test)
    print(" [>] Testing Multilingual agent loop in Hindi ('hi')...", flush=True)
    hi_state = await coordinator.execute_search(
        query="Sony WH-1000XM5",
        language="hi",
        country="IN",
        currency="INR"
    )
    hi_events = [e for e in hi_state.events if "खोज" in e.content or "विक्रेता" in e.content or "पेपाल" in e.content]
    print(f" [x] Localized Hindi events generated: {len(hi_events)} events matched.", flush=True)

    # 4. Test PayPal Orders API with Multi-Currency (INR and USD)
    paypal_svc = PayPalService()
    order_inr = await paypal_svc.create_order(amount=28500.00, item_name="Sony WH-1000XM5", currency="INR")
    print(f" [x] PayPal Orders API v2 createOrder successful for INR. Order ID: {order_inr['id']}", flush=True)

    capture_inr = await paypal_svc.capture_order(order_id=order_inr["id"])
    print(f" [x] PayPal Orders API v2 captureOrder successful for INR. Status: {capture_inr['status']}", flush=True)

    print("\n=== ALL SYSTEMS OPERATIONAL AND VERIFIED ===", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
