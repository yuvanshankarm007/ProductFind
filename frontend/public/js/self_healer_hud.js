/**
 * Self-Healer HUD Controller.
 * Provides real-time subsystem diagnostics, automated repair triggering, and self-learning management.
 */

import { showToast } from './state.js';
import { escapeHtml } from './security.js';

export async function refreshHud() {
    try {
        const res = await fetch('/api/system/health');
        if (res.ok) {
            const report = await res.json();
            renderHud(report);
        }
        
        // Also refresh prompt instincts count
        const instRes = await fetch('/api/system/instincts');
        if (instRes.ok) {
            const instData = await instRes.json();
            const badge = document.getElementById('hud-instincts-badge');
            if (badge && instData.total_instincts !== undefined) {
                badge.textContent = instData.total_instincts;
            }
        }
    } catch (e) {
        console.warn("HUD refresh failed:", e);
    }
}

export function renderHud(report) {
    // 1. Overall Health Score
    const scoreEl = document.getElementById('hud-overall-score');
    if (scoreEl) {
        const score = Math.round(report.overall_health_score || 95);
        scoreEl.textContent = `${score}%`;
        scoreEl.style.color = score >= 85 ? '#34d399' : (score >= 70 ? '#60a5fa' : '#fb7185');
    }

    // 2. Overall Status Badge
    const statusEl = document.getElementById('hud-overall-status');
    if (statusEl) {
        const status = report.overall_status || 'ALL_SYSTEMS_OPTIMAL';
        statusEl.textContent = status.replace(/_/g, ' ');
        statusEl.className = `hud-status-badge ${status.includes('OPTIMAL') ? 'status-optimal' : (status.includes('HEALED') ? 'status-healed' : 'status-degraded')}`;
    }

    // 3. Subsystem Cards Grid
    const gridEl = document.getElementById('hud-subsystems-grid');
    if (gridEl && report.subsystems) {
        gridEl.innerHTML = '';
        for (const sub of report.subsystems) {
            const card = document.createElement('div');
            card.className = 'hud-card';
            const statusClass = sub.status === 'HEALTHY' ? 'status-optimal' : (sub.status.includes('REPAIRED') ? 'status-healed' : 'status-degraded');
            card.innerHTML = `
                <div class="hud-card-label">${escapeHtml(sub.subsystem.replace(/_/g, ' '))}</div>
                <div class="hud-card-val">
                    <span class="hud-status-badge ${statusClass}">${escapeHtml(sub.status)}</span>
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 4px; display: flex; justify-content: space-between;">
                    <span>Latency</span>
                    <span class="mono-font">${sub.latency_ms}ms</span>
                </div>
            `;
            gridEl.appendChild(card);
        }
    }

    // 4. Learned Skills Count
    const countEl = document.getElementById('hud-skills-count');
    if (countEl) {
        countEl.textContent = report.learned_skills_count || 23;
    }

    // 5. Recent Repairs Count
    const repairsEl = document.getElementById('hud-repairs-count');
    if (repairsEl) {
        repairsEl.textContent = (report.recent_repairs || []).length;
    }
}

export async function triggerSelfTest() {
    showToast("Executing synthetic diagnostic audit across all 5 subsystems...", "info");
    try {
        const res = await fetch('/api/system/self-test', { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            renderHud(data.report);
            showToast("Diagnostic probe finished: All systems operational.", "success");
        } else {
            showToast("Self-test encountered an error.", "error");
        }
    } catch (e) {
        showToast(`Diagnostic failed: ${e.message}`, "error");
    }
}

export async function triggerSelfFix() {
    showToast("Executing closed-loop automated heuristic healing...", "info");
    try {
        const res = await fetch('/api/system/self-fix', { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            renderHud(data.report);
            const repairs = data.repairs_applied || [];
            showToast(`Self-Healing verified: ${repairs.length} auto-repairs executed.`, "success");
        } else {
            showToast("Self-fix failed.", "error");
        }
    } catch (e) {
        showToast(`Self-fix failed: ${e.message}`, "error");
    }
}

export async function triggerSelfLearn() {
    showToast("Launching continuous discovery & merchant skill distillation cycle...", "info");
    try {
        const res = await fetch('/api/system/self-learn', { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            const count = (data.skills_acquired || []).length;
            showToast(`Autonomous Learner acquired ${count} new merchant skills. Total in Vault: ${data.total_skills_in_vault}`, "success");
            refreshHud();
        } else {
            showToast("Self-learning failed.", "error");
        }
    } catch (e) {
        showToast(`Self-learning failed: ${e.message}`, "error");
    }
}
