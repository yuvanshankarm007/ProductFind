import sys
import pytest
import httpx
from backend.agents.adaptive_skill_learner import AdaptiveSkillLearner, SkillVault, AdaptiveSkill
from backend.server import app

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def test_autonomous_skill_learner_and_vault(tmp_path):
    # 1. Initialize vault with temp directory
    vault = SkillVault(vault_dir=str(tmp_path))
    learner = AdaptiveSkillLearner(vault)

    # 2. Discover and learn a novel merchant
    skill = learner.discover_and_learn_merchant(
        domain="boutique-tech.de",
        page_html_or_text="Boutique Tech Germany. 14 Tage Widerrufsrecht Rückgabe. 15% restocking fee on unsealed boxes. 24 Monate Gewährleistung. PayPal Käuferschutz.",
        country="DE",
        currency="EUR"
    )

    assert skill.merchant_name == "Boutique-tech"
    assert skill.merchant_domain == "boutique-tech.de"
    assert skill.origin_country == "DE"
    assert skill.currency == "EUR"
    assert skill.policy_rules.return_window_days == 14
    assert skill.policy_rules.restocking_fee_pct == 15.0
    assert skill.policy_rules.warranty_months == 24
    assert skill.paypal_shield_required is True
    assert skill.verification_score >= 0.85
    assert "audit_merchant_boutique_tech_de" in skill.synthesized_code

    # 3. Test persistence in vault
    loaded = vault.get_skill("boutique-tech.de")
    assert loaded is not None
    assert loaded.skill_id == skill.skill_id

@pytest.mark.asyncio
async def test_skills_rest_endpoints():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. List skills
        res = await client.get("/api/skills")
        assert res.status_code == 200
        data = res.json()
        assert "skills" in data
        assert data["count"] >= 3

        # 2. Teach novel merchant on-demand
        learn_req = {
            "domain": "hifi-sound-berlin.de",
            "content": "HiFi Sound Berlin. 30 days money-back guarantee. No restocking fee. 3 year warranty. PayPal Accepted.",
            "country": "DE",
            "currency": "EUR"
        }
        res = await client.post("/api/skills/teach", json=learn_req)
        assert res.status_code == 200
        t_data = res.json()
        assert t_data.get("status") == "success"
        assert t_data["skill"]["merchant_domain"] == "hifi-sound-berlin.de"
