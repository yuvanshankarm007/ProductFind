import pytest
from backend.agents.web_scout_engine import LiveWebScoutEngine

@pytest.mark.asyncio
async def test_stealth_open_web_discovery():
    engine = LiveWebScoutEngine()
    results = await engine.search_open_web_stealth("dell latitude 5511 refurbished", dest_country="IN")
    assert isinstance(results, list)
    if results:
        # Check that top item matches the model 5511
        for item in results[:3]:
            assert "5511" in item["title"]
            assert item["url"].startswith("http")
            assert item["domain"]
