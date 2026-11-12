"""
Comprehensive verification tests for the ProductFind Sentinel Enterprise Upgrade Suite:
- Live Reddit/HN Consensus & Zero-404 URLs
- iFixit Suggest 2.0 BIFL Integration & Graceful Fallback
- Live Scraped Listing Telemetry in Review Authenticity
- Vision-LLM Primary Identification Hook & Telemetry
- Persistent Savings & Risk Avoidance Ledger
- Price Watchdog Async Webhook Dispatcher
- Forensic Point-in-Time Checkout Snapshot in Dispute Dossiers
- SSRF-Safe Link Verifier & MCP JSON-RPC 2.0 Agent-Commerce Endpoint
"""

import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.server import app
from backend.core.reddit_consensus import (
    CURATED_COMMUNITY_KNOWLEDGE,
    reddit_consensus_engine,
    RedditThreadCitation,
)
from backend.core.bifl_index import bifl_index_engine, _IFIXIT_CACHE
from backend.core.review_authenticity import review_authenticity_engine
from backend.core.visual_search import visual_search_engine
from backend.core.savings_ledger import SavingsLedger
from backend.core.price_watchdog import PriceWatchdogService
from backend.core.dispute_assistant import DisputeAssistantService, DisputeFilingRequest
from backend.core.link_verifier import verify_url_live
from backend.core.state import (
    AnalyzedDealOption,
    BlackboardState,
    CrossBorderFxDutyAnalysis,
    MerchantTrustRating,
    PayPalProtectionAssessment,
    ScrapedListing,
    WarrantyAdpAnalysis,
)
from backend.paypal_service import PayPalEvidenceSentinel


client = TestClient(app)


def test_reddit_consensus_no_fake_comments_urls():
    # None of the curated citations should contain fake /comments/<made-up>/ URLs
    for key, entry in CURATED_COMMUNITY_KNOWLEDGE.items():
        for thread in entry.get("threads", []):
            assert "/comments/" not in thread["url"], f"Synthetic permalink found in curated {key}"
            assert thread["url"].startswith("https://www.reddit.com/")

    # Arbitrary unseen query uses valid search URL and explicit fallback mode when offline
    res = reddit_consensus_engine.analyze_community_consensus("Nova 2 Neo 5G Custom Phone", live_citations_override=[])
    assert res.source_mode == "synthetic_fallback"
    assert res.citations
    assert "/comments/" not in res.citations[0].url
    assert "reddit.com/search" in res.citations[0].url


@pytest.mark.asyncio
async def test_reddit_consensus_async_live_blending_and_llm():
    fake_live = [
        RedditThreadCitation(
            title="iPhone 15 1-year teardown & battery review",
            subreddit="HackerNews",
            upvotes=420,
            comment_count=118,
            url="https://news.ycombinator.com/item?id=37485290",
            summary_quote="Verified live discussion",
        )
    ]
    fake_llm = {
        "sentiment_score": 88,
        "sentiment_label": "Mostly Positive",
        "verdict_summary": "USB-C and repairable back glass praised across owner threads",
        "top_praises": ["USB-C universal charging", "Bright OLED outdoors"],
        "top_complaints": ["60Hz refresh rate on base model"],
        "failure_modes_after_1yr": "Battery holds ~89% after 450 cycles.",
        "bifl_certified": True,
    }
    with patch(
        "backend.core.reddit_consensus.fetch_live_community_threads_async",
        new=AsyncMock(return_value=(fake_live, ["HN thread about iPhone 15"], "live_api")),
    ), patch(
        "backend.core.reddit_consensus._synthesize_via_llm_async",
        new=AsyncMock(return_value=fake_llm),
    ):
        res = await reddit_consensus_engine.analyze_community_consensus_async("iPhone 15")
        assert res.source_mode == "live_web_llm"
        assert res.sentiment_score == 88
        assert res.citations[0].url == "https://news.ycombinator.com/item?id=37485290"


@pytest.mark.asyncio
async def test_bifl_ifixit_live_and_fallback():
    _IFIXIT_CACHE.clear()
    fake_hit = {
        "title": "iPhone 15",
        "url": "https://www.ifixit.com/Device/iPhone_15",
        "summary": "Modular back glass and USB-C port improve serviceability.",
    }
    with patch("backend.core.bifl_index.fetch_ifixit_device_async", new=AsyncMock(return_value=fake_hit)):
        live_res = await bifl_index_engine.evaluate_longevity_async("iPhone 15")
        assert live_res.source_mode == "live_ifixit_api"
        assert live_res.ifixit_url == "https://www.ifixit.com/Device/iPhone_15"
        assert "Modular back glass" in live_res.ifixit_guide_summary

    _IFIXIT_CACHE.clear()
    with patch("backend.core.bifl_index.fetch_ifixit_device_async", new=AsyncMock(return_value=None)):
        fallback_res = await bifl_index_engine.evaluate_longevity_async("Unlisted Brand X900")
        assert fallback_res.source_mode == "synthetic_fallback"
        assert "ifixit.com/Search" in fallback_res.ifixit_url


def test_review_authenticity_grounded_in_scraped_listings():
    listings = [
        {
            "merchant": "Flipkart",
            "rating": 4.9,
            "review_count": 8,  # thin high-rating suspicious volume
            "merchant_trust_score": 5.2,
        }
    ]
    res = review_authenticity_engine.audit_reviews(
        "Nova 2 Neo 5G", store="Amazon", scraped_listings=listings
    )
    assert res.source_mode == "live_scraped_telemetry"
    assert res.store_audited == "Flipkart"
    assert res.total_reviews_analyzed == 8
    assert any(s.status == "ALERT" for s in res.bot_signals)


def test_visual_search_vlm_hook_and_method_telemetry(monkeypatch):
    buf = io.BytesIO()
    Image.new("RGB", (120, 120), color=(40, 120, 210)).save(buf, format="PNG")
    img_bytes = buf.getvalue()

    monkeypatch.setenv("GEMINI_API_KEY", "test-fake-gemini-key")
    fake_vlm_result = {
        "brand": "Nothing",
        "model": "Phone (2a) Plus",
        "category": "Midrange Smartphone",
        "query": "Nothing Phone 2a Plus",
        "confidence": 0.94,
        "labels": ["Nothing", "Glyph Interface"],
        "_method": "vlm_gemini",
    }
    with patch.object(visual_search_engine, "_classify_via_vlm", return_value=fake_vlm_result):
        out = visual_search_engine.extract_visual_features(img_bytes, filename="camera_upload.png")
        assert out.extracted_query == "Nothing Phone 2a Plus"
        assert out.features["identification_method"] == "vlm_gemini"


def test_savings_ledger_persistence(tmp_path):
    ledger = SavingsLedger(ledger_path=tmp_path / "savings_ledger.json")
    listing1 = ScrapedListing(
        id="opt1", merchant="OEM Direct", merchant_domain="oem.com",
        product_title="Test Phone", base_price=500.0, seller_name="OEM",
        listing_url="https://oem.example/phone"
    )
    listing2 = ScrapedListing(
        id="opt2", merchant="Reseller", merchant_domain="reseller.com",
        product_title="Test Phone", base_price=620.0, condition="Grey Market",
        seller_name="GreySeller", listing_url="https://reseller.example/phone"
    )
    opt1 = AnalyzedDealOption(
        id="opt1", listing=listing1,
        warranty=WarrantyAdpAnalysis(listing_id="opt1"),
        trust=MerchantTrustRating(merchant="OEM Direct"),
        paypal=PayPalProtectionAssessment(listing_id="opt1"),
        total_cash_outlay=500.0, converted_cash_outlay=500.0, risk_adjusted_tco=500.0,
        url_verified=True,
    )
    opt2 = AnalyzedDealOption(
        id="opt2", listing=listing2,
        warranty=WarrantyAdpAnalysis(listing_id="opt2"),
        trust=MerchantTrustRating(merchant="Reseller", dispute_risk_factor="High"),
        paypal=PayPalProtectionAssessment(listing_id="opt2"),
        total_cash_outlay=620.0, converted_cash_outlay=620.0, risk_adjusted_tco=710.0,
    )
    state = BlackboardState(
        search_query="Test Phone",
        raw_listings=[listing1, listing2],
        final_options=[opt1, opt2],
        cross_border_analyses={"opt2": CrossBorderFxDutyAnalysis(is_cross_border=True, estimated_import_duty_amount=40.0)},
    )
    stats = ledger.record_search(state)
    assert stats["total_arbitrages_completed"] == 1
    assert stats["total_arbitrage_saved_usd"] == 120.0
    assert stats["total_customs_risks_flagged"] == 1
    assert stats["total_low_trust_filtered"] == 1
    assert stats["total_links_verified"] == 1


@pytest.mark.asyncio
async def test_price_watchdog_webhook_dispatch(tmp_path):
    svc = PriceWatchdogService(storage_path=str(tmp_path / "alerts.json"))
    alert = svc.subscribe(
        product_title="Sony WH-1000XM5",
        target_price=250.0,
        current_price=320.0,
        currency="USD",
        user_contact="discord-bot",
        channel="discord",
        webhook_url="https://hooks.example.test/webhook",
    )

    mock_resp = MagicMock(status_code=204)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    async def fake_scout(title, currency):
        if "wh-1000xm5" in title.lower():
            return {"price": 239.0, "merchant": "Best Buy", "currency": "USD"}
        return None

    with patch("backend.core.price_watchdog.httpx.AsyncClient", return_value=mock_client):
        triggered = await svc.evaluate_all_active_alerts(price_lookup_fn=fake_scout)
        triggered_ids = {t.id for t in triggered}
        assert alert.id in triggered_ids
        assert "alert-demo-xm5" not in triggered_ids  # INR alert not falsely triggered by USD quote
        assert svc._alerts[alert.id].webhook_status == "DISPATCHED_204"
        mock_client.post.assert_called_once()


def test_forensic_checkout_snapshot_in_dispute_and_paypal(tmp_path):
    svc = DisputeAssistantService(dossiers_dir=str(tmp_path))
    case = svc.file_dispute(
        DisputeFilingRequest(
            order_id="ORD-991",
            merchant="Flipkart",
            product_title="Nova 2 Neo 5G",
            amount=14999.0,
            currency="INR",
            issue_type="OPEN_BOX_VIOLATION",
            incident_description="Broken factory seal at delivery",
            merchant_url="https://www.flipkart.com/item/nova-2-neo-5g",
            captured_terms={"warranty_months": 12, "open_box_otp": True},
        )
    )
    assert len(case.checkout_snapshot["snapshot_sha256"]) == 64
    assert case.checkout_snapshot["merchant_url"] == "https://www.flipkart.com/item/nova-2-neo-5g"
    assert case.checkout_snapshot["captured_terms"]["open_box_otp"] is True

    dossier = PayPalEvidenceSentinel.create_dispute_dossier(
        order_id="PP-ORD-101",
        item_title="Nova 2 Neo 5G",
        platform="Flipkart",
        agreed_tco=14999.0,
        condition="Brand New",
        open_box_verified=True,
        seller_name="SuperComNet",
        seller_rating=4.6,
        warranty_claims="12-month OEM",
        display_currency="INR",
        merchant_url="https://www.flipkart.com/item/nova-2-neo-5g",
    )
    assert dossier.checkout_snapshot is not None
    assert len(dossier.checkout_snapshot["snapshot_sha256"]) == 64
    assert PayPalEvidenceSentinel.verify_dossier_integrity(dossier) is True


@pytest.mark.asyncio
async def test_ssrf_safe_link_verifier():
    blocked = await verify_url_live("http://127.0.0.1:8000/api/health")
    assert blocked["verified"] is False
    assert "Blocked" in blocked.get("reason", "")

    blocked_meta = await verify_url_live("http://169.254.169.254/latest/meta-data/")
    assert blocked_meta["verified"] is False


def test_server_routes_no_duplicates_and_mcp_endpoints():
    chat_post_routes = [
        r for r in app.routes
        if getattr(r, "path", None) == "/api/chat" and "POST" in (getattr(r, "methods", set()) or set())
    ]
    assert len(chat_post_routes) == 1

    r_ledger = client.get("/api/ledger/stats")
    assert r_ledger.status_code == 200
    assert "total_arbitrage_saved_usd" in r_ledger.json()

    r_manifest = client.get("/api/mcp/manifest")
    assert r_manifest.status_code == 200
    tool_names = {t["name"] for t in r_manifest.json()["tools"]}
    assert {"arbitrate_deal", "audit_consumer_proof", "verify_listing_safety", "compile_dispute_dossier"} <= tool_names

    # MCP JSON-RPC initialize & tools/list
    init_resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_resp.status_code == 200
    assert init_resp.json()["result"]["serverInfo"]["name"] == "productfind-sentinel"

    list_resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()["result"]["tools"]) == 4

    # SSRF verify-link endpoint test
    v_resp = client.post("/api/verify-link", json={"url": "http://127.0.0.1:8000/secret"})
    assert v_resp.status_code == 200
    assert v_resp.json()["verified"] is False
