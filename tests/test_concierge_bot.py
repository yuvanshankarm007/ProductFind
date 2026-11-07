"""
Unit and integration tests for Sentinel AI Concierge Chatbot & Voice Integrated Bot.
Verifies doubt resolution on Open Box delivery, TCO, PayPal Section 13, COD,
price predictions, cart-split knapsack, and voice audio handling.
"""

import pytest
import io
from fastapi.testclient import TestClient
from backend.server import app
from backend.core.concierge_bot import SentinelConciergeBot

@pytest.fixture
def client():
    return TestClient(app)


def test_concierge_bot_open_box_doubt():
    res = SentinelConciergeBot.answer_query("Is Open Box delivery safe?", active_product="Sony WH-1000XM5")
    assert res.intent == "OPEN_BOX_VERIFICATION"
    assert "OTP" in res.reply
    assert "unbox" in res.reply.lower()
    assert len(res.suggestions) > 0
    assert len(res.voice_text) > 0


def test_concierge_bot_tco_calculation_doubt():
    res = SentinelConciergeBot.answer_query("Why is Risk-Adjusted TCO different from sticker price?")
    assert res.intent == "TCO_CALCULATION"
    assert "TCO" in res.reply
    assert "Warranty" in res.reply or "Counterfeit" in res.reply


def test_concierge_bot_paypal_protection_doubt():
    res = SentinelConciergeBot.answer_query("How does PayPal Section 13 escrow protect me from counterfeit?")
    assert res.intent == "PAYPAL_PROTECTION"
    assert "180" in res.reply
    assert "Section 13" in res.reply


def test_concierge_bot_cod_safety():
    res = SentinelConciergeBot.answer_query("Can I pay via cash on delivery?")
    assert res.intent == "COD_INQUIRY"
    assert "Cash on Delivery" in res.reply
    assert "UPI" in res.reply


def test_concierge_bot_price_prediction_doubt():
    res = SentinelConciergeBot.answer_query("Will the price drop soon or should I wait?")
    assert res.intent == "PRICE_PREDICTION"
    assert "price" in res.reply.lower() or "trajectory" in res.reply.lower()


def test_concierge_bot_bundle_arbitrage_doubt():
    res = SentinelConciergeBot.answer_query("How does cart-splitting save money on bundles?")
    assert res.intent == "BUNDLE_ARBITRAGE"
    assert "knapsack" in res.reply.lower() or "shipping" in res.reply.lower()


def test_concierge_bot_hardware_deal_recommendation():
    res = SentinelConciergeBot.answer_query("Which deal do you recommend for Epson L3250 printer?", active_product="Epson EcoTank L3250")
    assert res.intent == "DEAL_COMPARISON"
    assert "Optimal Value" in res.reply


def test_concierge_api_get(client):
    res = client.get("/api/chat")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "Sentinel AI Concierge" in data["service"]


def test_concierge_api_post_chat(client):
    payload = {
        "message": "Is open box inspection allowed before sharing OTP?",
        "active_query": "Dell Precision 7820",
        "voice_enabled": True
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["intent"] == "OPEN_BOX_VERIFICATION"
    assert len(data["voice_text"]) > 10


def test_concierge_api_post_empty_message_rejected(client):
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400


def test_concierge_api_voice_hint(client):
    data = {
        "query_hint": "How to file a PayPal dispute for fake product?",
        "active_query": "Sony WH-1000XM5"
    }
    res = client.post("/api/chat/voice", data=data)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "success"
    assert "Section 13" in res_data["chat_response"]["reply"]


def test_concierge_api_voice_audio_file(client):
    # Valid RIFF WAV header
    wav_header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00"
        b"data\x00\x00\x00\x00" + b"\x00" * 400
    )
    files = {"file": ("is_open_box_safe.wav", io.BytesIO(wav_header), "audio/wav")}
    res = client.post("/api/chat/voice", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Open Box" in data["transcript"] or "OTP" in data["chat_response"]["reply"]
