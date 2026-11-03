/**
 * Prompt Instincts & Reflex Memory Modal.
 * Manages learned operational instincts, prompt-derived negative constraints,
 * and user-driven merchant quarantine.
 */

import { escapeHtml } from './security.js';
import { showToast } from './state.js';

export async function openInstinctsModal() {
    const modal = document.getElementById('instincts-modal');
    if (!modal) return;

    modal.style.display = 'flex';
    await refreshInstinctsView();
}

export function closeInstinctsModal() {
    const modal = document.getElementById('instincts-modal');
    if (modal) modal.style.display = 'none';
}

export async function refreshInstinctsView() {
    const contentEl = document.getElementById('instincts-modal-content');
    if (!contentEl) return;

    contentEl.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: #94a3b8;">
            <div style="display: inline-block; width: 28px; height: 28px; border: 3px solid rgba(0, 112, 186, 0.3); border-top-color: #0070ba; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 8px;"></div>
            <div>Querying Reflex Memory Vault & Prompt Instincts...</div>
        </div>
    `;

    try {
        const res = await fetch('/api/system/instincts');
        if (!res.ok) throw new Error("Failed to load instincts");
        const data = await res.json();
        const instincts = data.instincts || [];

        // Update badge count in HUD
        const badge = document.getElementById('hud-instincts-badge');
        if (badge) badge.textContent = instincts.length;

        renderInstinctsList(instincts);
    } catch (err) {
        contentEl.innerHTML = `<div style="color: #fb7185; padding: 1rem;">Failed to retrieve instincts: ${escapeHtml(err.message)}</div>`;
    }
}

function renderInstinctsList(instincts) {
    const contentEl = document.getElementById('instincts-modal-content');
    if (!contentEl) return;

    const categoryIcons = {
        'PROMPT_CONSTRAINT_IN_STOCK': '🟢 In-Stock Only',
        'PROMPT_CONSTRAINT_ZERO_404': '🛡️ Zero 404s',
        'PROMPT_CONSTRAINT_ANTI_SCAM': '🔒 Anti-Scam Shield',
        'USER_QUARANTINE_MERCHANT': '🚫 Banned Merchant',
        'BLACKLIST_DEAD_SKU': '⛔ Dead SKU Blacklist',
        'SEARCH_PAGE_INTERCEPT': '🔗 Search Intercept',
        'BOT_CHALLENGE_DEFENSE': '⚡ TLS Defense'
    };

    const rows = instincts.map(inst => {
        const catLabel = categoryIcons[inst.category] || inst.category;
        const triggers = inst.triggers_count || 0;
        return `
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="hud-status-badge status-optimal" style="font-size: 10px;">${escapeHtml(catLabel)}</span>
                        <code class="mono-font" style="font-size: 11px; color: #93c5fd;">${escapeHtml(inst.pattern)}</code>
                    </div>
                    <span style="font-size: 10.5px; color: #64748b;">Enforced <strong>${triggers}</strong> times</span>
                </div>
                <div style="font-size: 11.5px; color: #cbd5e1; line-height: 1.35;">${escapeHtml(inst.reason)}</div>
            </div>
        `;
    }).join('');

    contentEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 14px;">
            
            <!-- Description Banner -->
            <div style="background: rgba(0, 112, 186, 0.08); border: 1px solid rgba(0, 112, 186, 0.25); border-radius: 8px; padding: 12px; font-size: 12px; color: #bfdbfe;">
                <strong>Prompt-Learned Reflex Memory (ECC / Voyager Architecture)</strong>
                <div style="margin-top: 3px; color: #94a3b8; font-size: 11px;">
                    When you type queries like <em>"in stock only"</em>, <em>"no 404s"</em>, or <em>"no scams"</em>, the Self-Healer compiles permanent negative constraint instincts.
                    Quarantined items are automatically purged from both cards and the AG Grid Cockpit.
                </div>
            </div>

            <!-- Interactive Teacher Box -->
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;">
                <div style="font-size: 11.5px; font-weight: 700; color: #ffffff; margin-bottom: 6px;">Teach Self-Healer Directly:</div>
                <div style="display: flex; gap: 8px;">
                    <input type="text" id="teach-prompt-input" class="search-input" placeholder="e.g. strictly in stock only, ban shadytech.biz, no 404 links..." style="font-size: 12px; padding: 8px 12px; flex: 1;">
                    <button type="button" id="btn-submit-teach-prompt" class="control-btn btn-primary" style="padding: 8px 16px; font-size: 12px; white-space: nowrap;">
                        ⚡ Train Reflex Memory
                    </button>
                </div>
            </div>

            <!-- Active Instincts List -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 12px; font-weight: 700; color: #ffffff;">Active Reflex Rules Vault (${instincts.length})</div>
                    <span style="font-size: 11px; color: #34d399;">100% Quarantine Active</span>
                </div>
                <div style="max-height: 280px; overflow-y: auto; padding-right: 4px;">
                    ${rows}
                </div>
            </div>

        </div>
    `;

    // Wire Teacher Button
    const btnTeach = document.getElementById('btn-submit-teach-prompt');
    const inputTeach = document.getElementById('teach-prompt-input');
    if (btnTeach && inputTeach) {
        btnTeach.addEventListener('click', async () => {
            const promptText = inputTeach.value.trim();
            if (!promptText) return;

            btnTeach.disabled = true;
            btnTeach.textContent = "Synthesizing...";
            try {
                const res = await fetch('/api/system/instincts/learn-from-prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: promptText })
                });
                const resData = await res.json();
                showToast(`Self-Healer learned new rules: ${resData.newly_learned_count} new constraints activated!`, "success");
                await refreshInstinctsView();
            } catch (err) {
                showToast(`Teaching Error: ${err.message}`, "error");
            } finally {
                btnTeach.disabled = false;
                btnTeach.textContent = "⚡ Train Reflex Memory";
            }
        });
    }
}

export async function quarantineMerchantFromUI(merchant, merchantDomain = '', listingId = '', reason = 'User Flagged') {
    try {
        const res = await fetch('/api/system/quarantine-item', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                merchant,
                merchant_domain: merchantDomain,
                listing_id: listingId,
                reason
            })
        });
        if (res.ok) {
            showToast(`Quarantined '${merchant}'. Self-Healer learned rule and purged merchant from matrix.`, "success");
            // Refresh instincts count in HUD
            const instRes = await fetch('/api/system/instincts');
            if (instRes.ok) {
                const data = await instRes.json();
                const badge = document.getElementById('hud-instincts-badge');
                if (badge) badge.textContent = data.instincts?.length || 0;
            }
        }
    } catch (err) {
        showToast(`Failed to quarantine: ${err.message}`, "error");
    }
}
