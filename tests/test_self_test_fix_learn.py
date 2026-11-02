"""
Unit and Integration Test Suite for Autonomous Self-Testing, Self-Fixing & Learning Modules.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.server import app
from backend.agents.autonomous_self_healer import (
    AutonomousSelfTester,
    AutonomousSelfFixer,
    AutonomousContinuousLearner,
    AutonomousOrchestrator,
    autonomous_healer
)

@pytest.mark.asyncio
async def test_autonomous_self_tester_diagnostic():
    """Verifies that the self-testing engine probes all 5 subsystems and produces a health report."""
    tester = AutonomousSelfTester()
    report = await tester.run_full_diagnostic()

    assert report.overall_health_score >= 80.0, f"Expected health score >= 80, got {report.overall_health_score}"
    assert report.overall_status in ("ALL_SYSTEMS_OPTIMAL", "HEALED", "DEGRADED")
    assert len(report.subsystems) == 5, f"Expected 5 subsystems probed, got {len(report.subsystems)}"

    sub_names = {s.subsystem for s in report.subsystems}
    expected_subs = {"stealth_browser", "url_integrity", "persistence_cache", "paypal_sentinel", "skill_vault"}
    assert sub_names == expected_subs, f"Subsystem mismatch: {sub_names}"

    for sub in report.subsystems:
        assert sub.latency_ms >= 0.0
        assert sub.status in ("HEALTHY", "DEGRADED", "AUTO_REPAIRED", "ANOMALY_DETECTED")
        assert len(sub.details) > 5

@pytest.mark.asyncio
async def test_autonomous_self_fixer_auto_repair():
    """Verifies that the auto-repair engine can heal degradations and maintain a verified fix log."""
    fixer = AutonomousSelfFixer()

    # Test specific heuristic healing
    stealth_fix = await fixer.heal_stealth_browser("Simulated Akamai Challenge")
    assert stealth_fix.subsystem == "stealth_browser"
    assert stealth_fix.verification_status == "VERIFIED_HEALTHY"

    url_fix = fixer.heal_url_integrity("Simulated Search Query Leak")
    assert url_fix.subsystem == "url_integrity"
    assert url_fix.verification_status == "VERIFIED_HEALTHY"

    cache_fix = fixer.heal_persistence_cache("Simulated Cache Desync")
    assert cache_fix.subsystem == "persistence_cache"
    assert cache_fix.verification_status == "VERIFIED_HEALTHY"

    # Test full auto-repair loop
    repairs = await fixer.execute_auto_repair()
    assert len(repairs) >= 1
    for r in repairs:
        assert r.verification_status == "VERIFIED_HEALTHY"

@pytest.mark.asyncio
async def test_autonomous_continuous_learner():
    """Verifies that the continuous learner discovers uncataloged domains and distills skills."""
    learner = AutonomousContinuousLearner()

    # Discover and distill a novel candidate
    record = await learner.discover_and_learn_domain("vijaysales.com", country="IN", currency="INR")
    assert record.domain == "vijaysales.com"
    assert record.confidence >= 0.85
    assert record.return_window_days > 0
    assert record.persisted is True
    assert record.skill_id.startswith("skill_vijaysales_com")

    # Run discovery cycle on small batch
    batch = await learner.run_discovery_cycle(["reliancedigital.in", "tatacliq.com"])
    assert len(batch) == 2
    for b in batch:
        assert b.confidence >= 0.80
        assert b.persisted is True

@pytest.mark.asyncio
async def test_autonomous_orchestrator_closed_loop():
    """Verifies the closed-loop orchestrator (Audit -> Detect -> Heal -> Re-Audit)."""
    orchestrator = AutonomousOrchestrator()
    report = await orchestrator.run_comprehensive_audit_and_heal()

    assert report.overall_health_score >= 80.0
    assert len(report.recent_repairs) >= 1
    assert report.learned_skills_count >= 3

def test_system_rest_endpoints():
    """Verifies FastAPI REST endpoints for self-testing, self-fixing, and continuous learning."""
    client = TestClient(app)

    # 1. Health endpoint
    r_health = client.get("/api/system/health")
    assert r_health.status_code == 200
    h_data = r_health.json()
    assert "overall_health_score" in h_data
    assert "subsystems" in h_data

    # 2. Trigger Self-Test endpoint
    r_test = client.post("/api/system/self-test")
    assert r_test.status_code == 200
    t_data = r_test.json()
    assert t_data.get("status") == "success"
    assert "report" in t_data

    # 3. Trigger Self-Fix endpoint
    r_fix = client.post("/api/system/self-fix")
    assert r_fix.status_code == 200
    f_data = r_fix.json()
    assert f_data.get("status") == "success"
    assert "repairs_applied" in f_data

    # 4. Trigger Self-Learn endpoint
    r_learn = client.post("/api/system/self-learn", json={"domains": ["poorvika.com"]})
    assert r_learn.status_code == 200
    l_data = r_learn.json()
    assert l_data.get("status") == "success"
    assert len(l_data.get("skills_acquired", [])) >= 1

    # 5. Repairs history endpoint
    r_repairs = client.get("/api/system/repairs")
    assert r_repairs.status_code == 200
    rep_list = r_repairs.json()
    assert isinstance(rep_list, list)
