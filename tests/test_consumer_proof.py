"""
Unit & Integration Tests for Consumer Decision Breakdown:
1. Reddit Community Hivemind Consensus
2. ReviewRay / Fakespot Review Authenticity Engine
3. iFixit & BIFL Longevity Engine
4. Coordinator & Server Endpoints Integration
"""

import pytest
from backend.core.reddit_consensus import reddit_consensus_engine, RedditConsensusResult
from backend.core.review_authenticity import review_authenticity_engine, ReviewAuthenticityResult
from backend.core.bifl_index import bifl_index_engine, BiflIndexResult


def test_reddit_consensus_curated_iphone():
    result = reddit_consensus_engine.get_consensus("Apple iPhone 16 Pro")
    assert isinstance(result, RedditConsensusResult)
    assert result.sentiment_score >= 90
    assert "r/BuyItForLife" in result.subreddits or "r/apple" in result.subreddits
    assert len(result.top_praises) >= 2
    assert len(result.top_complaints) >= 2
    assert len(result.citations) >= 1
    assert "after 60 days" in result.citations[0].title or "Pro" in result.citations[0].title


def test_reddit_consensus_dynamic_query():
    result = reddit_consensus_engine.get_consensus("Bose QuietComfort 45")
    assert isinstance(result, RedditConsensusResult)
    assert 70 <= result.sentiment_score <= 100
    assert len(result.top_praises) >= 1
    assert len(result.citations) >= 1
    assert result.threads_analyzed > 10


def test_review_authenticity_curated_macbook():
    audit = review_authenticity_engine.audit_reviews("Apple MacBook Air M2", store="Amazon")
    assert isinstance(audit, ReviewAuthenticityResult)
    assert audit.letter_grade in ["Grade A+", "Grade A"]
    assert audit.adjusted_honest_rating <= audit.sticker_rating
    assert audit.organic_reviews_pct >= 90
    assert len(audit.bot_signals) >= 3
    # Check signal fields
    for sig in audit.bot_signals:
        assert sig.status in ["PASS", "WARNING", "ALERT"]
        assert len(sig.metric) > 0


def test_review_authenticity_dynamic_product():
    audit = review_authenticity_engine.audit_reviews("Wireless Ergonomic Keyboard K860", store="Flipkart")
    assert isinstance(audit, ReviewAuthenticityResult)
    assert audit.letter_grade in ["Grade A", "Grade B", "Grade C", "Grade D"]
    assert audit.adjusted_honest_rating <= audit.sticker_rating
    assert audit.total_reviews_analyzed > 1000
    assert audit.organic_reviews_pct + audit.incentivized_or_bot_pct == 100


def test_bifl_index_curated_dell_latitude():
    bifl = bifl_index_engine.evaluate_longevity("Dell Latitude 5511")
    assert isinstance(bifl, BiflIndexResult)
    assert bifl.ifixit_score >= 8.0
    assert bifl.battery_replaceable is True
    assert bifl.expected_lifespan_years >= 7.0
    assert bifl.bifl_certified is True
    assert len(bifl.key_longevity_drivers) >= 3


def test_bifl_index_dynamic():
    bifl = bifl_index_engine.evaluate_longevity("KitchenAid Stand Mixer")
    assert isinstance(bifl, BiflIndexResult)
    assert 1.0 <= bifl.ifixit_score <= 10.0
    assert bifl.expected_lifespan_years >= 2.0
    assert len(bifl.repairability_tier) > 0


@pytest.mark.asyncio
async def test_coordinator_integration_populates_consumer_proof():
    from backend.coordinator import SentinelCoordinator
    from backend.core.bus import EventBus
    bus = EventBus()
    coordinator = SentinelCoordinator(bus=bus)
    state = await coordinator.execute_search(
        query="Sony WH-1000XM5",
        country="US",
        currency="USD"
    )
    assert state.reddit_consensus is not None
    assert "sentiment_score" in state.reddit_consensus
    assert state.review_authenticity is not None
    assert "letter_grade" in state.review_authenticity
    assert state.bifl_metrics is not None
    assert "ifixit_score" in state.bifl_metrics


def test_api_endpoints_via_testclient():
    from fastapi.testclient import TestClient
    from backend.server import app

    client = TestClient(app)

    # 1. /api/consensus
    r1 = client.get("/api/consensus?q=Apple+iPhone+16+Pro")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["sentiment_score"] >= 90
    assert len(d1["citations"]) >= 1

    # 2. /api/review-audit
    r2 = client.get("/api/review-audit?q=Apple+MacBook+Air+M2")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["letter_grade"] in ["Grade A+", "Grade A"]
    assert d2["organic_reviews_pct"] >= 90

    # 3. /api/bifl-score
    r3 = client.get("/api/bifl-score?q=Dell+Latitude+5511")
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["ifixit_score"] >= 8.0
    assert d3["battery_replaceable"] is True
