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
    print(" [x] Autonomous Skill Synthesis and Vault Persistence verified.")


@pytest.mark.asyncio
async def test_skills_rest_endpoints():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. List skills
        res = await client.get("/api/skills")
        assert res.status_code == 200
        data = res.json()
        assert "skills" in data
        assert data["count"] >= 3
        print(f" [x] /api/skills returned {data['count']} persistent skills.")

        # 2. Teach novel merchant on-demand
        learn_req = {
            "domain": "hifi-sound-berlin.de",
            "content": "HiFi Sound Berlin. 30 days money-back guarantee. No restocking fee. 3 year warranty. PayPal Accepted.",
            "country": "DE",
            "currency": "EUR"
        }
        res = await client.post("/api/skills/learn", json=learn_req)
        assert res.status_code == 200
        learn_data = res.json()
        assert learn_data["status"] == "success"
        learned_skill = learn_data["skill"]
        assert learned_skill["merchant_domain"] == "hifi-sound-berlin.de"
        assert learned_skill["policy_rules"]["return_window_days"] == 30
        assert learned_skill["policy_rules"]["restocking_fee_pct"] == 0.0
        assert learned_skill["policy_rules"]["warranty_months"] == 36
        print(" [x] On-demand autonomous skill learning endpoint verified.")

        # 3. Retrieve specific learned skill
        res = await client.get("/api/skills/hifi-sound-berlin.de")
        assert res.status_code == 200
        assert res.json()["merchant_domain"] == "hifi-sound-berlin.de"
        print(" [x] /api/skills/{domain} endpoint verified.")


@pytest.mark.asyncio
async def test_swarm_integration_with_adaptive_skills():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        search_req = {
            "query": "Sony WH-1000XM5",
            "country": "IN",
            "currency": "INR",
            "language": "en"
        }
        res = await client.post("/api/search", json=search_req)
        assert res.status_code == 200
        data = res.json()

        # Check that comparison matrix has the auto-learned skill metadata
        matrix = data["comparison_matrix"]
        learned_rows = [row for row in matrix if row.get("is_auto_learned_skill") is True]
        assert len(learned_rows) > 0, "Swarm should contain at least one dynamically synthesized merchant skill"

        croma_row = learned_rows[0]
        assert croma_row["is_auto_learned_skill"] is True
        assert "skill_croma_com" in croma_row["skill_id"]
        assert "Auto-Synthesized" in croma_row["skill_confidence"]
        print(f" [x] Swarm search produced dynamic merchant with skill '{croma_row['skill_id']}' ({croma_row['skill_confidence']})")
