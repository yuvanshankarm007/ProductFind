"""
Unit and integration tests for ProductFind Omnibox Autocomplete Engine.
Verifies live suggestions, department scoping, instant deal spotlight cards, and fallback resilience.
"""

import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend.core.autocomplete_service import autocomplete_service

@pytest.fixture
def client():
    return TestClient(app)


def test_autocomplete_service_empty_query():
    res = autocomplete_service.get_completions(query="")
    assert res.total > 0
    assert len(res.suggestions) > 0
    assert len(res.departments) > 0
    assert res.spotlight is not None


def test_autocomplete_service_laptop_query():
    res = autocomplete_service.get_completions(query="laptop")
    assert res.query == "laptop"
    assert any("laptop" in s.query.lower() for s in res.suggestions)
    assert res.spotlight is not None
    assert "laptop" in res.spotlight.title.lower() or "vivobook" in res.spotlight.title.lower()


def test_autocomplete_service_iphone_query():
    res = autocomplete_service.get_completions(query="iphone")
    assert res.query == "iphone"
    assert any("iphone" in s.query.lower() for s in res.suggestions)
    assert res.spotlight is not None
    assert "iphone" in res.spotlight.title.lower()


def test_autocomplete_api_endpoint(client):
    res = client.get("/api/autocomplete?q=macbook")
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "suggestions" in data
    assert "spotlight" in data
    assert len(data["suggestions"]) > 0
    assert "macbook" in data["spotlight"]["title"].lower()
