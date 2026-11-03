/**
 * ProductFind Sentinel — Main Application Bootstrap & Orchestrator.
 * Wires together the reactive store, resilient WebSocket stream, AG Grid cockpit,
 * Self-Healer HUD, and Merkle tree dispute modal.
 */

import { store, showToast } from './state.js';
import { wsClient } from './websocket.js';
import { initializeAgGrid, updateGridData, filterGrid, exportGridCsv } from './ag_grid_setup.js';
import { refreshHud, triggerSelfTest, triggerSelfFix, triggerSelfLearn } from './self_healer_hud.js';
import { closeDossierModal, openDossierModal } from './merkle_modal.js';
import { openPayPalCheckoutModal, closePayPalCheckoutModal } from './paypal_checkout_modal.js';
import { openInstinctsModal, closeInstinctsModal, quarantineMerchantFromUI } from './instincts_modal.js';
import { renderPriceTrajectory } from './charts.js';
import { escapeHtml, sanitizeUrl } from './security.js';

let currentSearchController = null;
let currentSearchToken = 0;
let lastExecutedQuery = "";
let searchDebounceTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    // 1. Initialize WebSocket
    wsClient.connect();
    wsClient.onMessage(handleInboundWebSocket);

    // 2. Initialize AG Grid
    initializeAgGrid('comparison-grid');

    // 3. Initialize HUD
    refreshHud();

    // 4. Wire Preferences
    syncPreferencesUI();

    // 5. Wire Event Listeners
    setupEventListeners();

    // 6. Pre-seed demo search if first load
    setTimeout(() => {
        executeSearch("Sony WH-1000XM5");
    }, 400);
}

function syncPreferencesUI() {
    const prefs = store.preferences;
    const langSelect = document.getElementById('pref-language');
    const countrySelect = document.getElementById('pref-country');
    const currSelect = document.getElementById('pref-currency');
    const paySelect = document.getElementById('pref-payment');

    if (langSelect) langSelect.value = prefs.language || 'en';
    if (countrySelect) countrySelect.value = prefs.country || 'US';
    if (currSelect) currSelect.value = prefs.currency || 'USD';
    if (paySelect) paySelect.value = prefs.preferredPayment || 'all';
}

function setupEventListeners() {
    // Search Form Submit & Live Typing Debounce
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            clearTimeout(searchDebounceTimer);
            const q = searchInput ? searchInput.value.trim() : '';
            if (q) {
                lastExecutedQuery = q;
                executeSearch(q);
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            updatePromptBadges(searchInput.value);
            clearTimeout(searchDebounceTimer);
            const q = searchInput.value.trim();
            // Auto-search after 800ms pause if at least 3 characters and changed
            if (q.length >= 3 && q.toLowerCase() !== (lastExecutedQuery || '').toLowerCase()) {
                searchDebounceTimer = setTimeout(() => {
                    lastExecutedQuery = q;
                    executeSearch(q);
                }, 800);
            }
        });
        updatePromptBadges(searchInput.value);
    }

    // Quick Query Tag Buttons
    document.querySelectorAll('.query-tag-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            clearTimeout(searchDebounceTimer);
            const query = btn.getAttribute('data-query');
            if (query) {
                if (searchInput) searchInput.value = query;
                lastExecutedQuery = query;
                executeSearch(query);
            }
        });
    });

    // Quick Search Filter in AG Grid
    const gridSearch = document.getElementById('grid-quick-filter');
    if (gridSearch) {
        gridSearch.addEventListener('input', (e) => {
            filterGrid(e.target.value);
        });
    }

    // CSV Export Button
    const csvBtn = document.getElementById('btn-export-csv');
    if (csvBtn) {
        csvBtn.addEventListener('click', () => {
            exportGridCsv();
        });
    }

    // Preference Change Handlers
    const prefInputs = ['pref-language', 'pref-country', 'pref-currency', 'pref-payment'];
    prefInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                store.savePreferences({
                    language: document.getElementById('pref-language').value,
                    country: document.getElementById('pref-country').value,
                    currency: document.getElementById('pref-currency').value,
                    preferredPayment: document.getElementById('pref-payment').value,
                });
                showToast("Preferences updated. Re-executing active search...", "info");
                const currentQuery = searchInput ? searchInput.value.trim() : "Sony WH-1000XM5";
                if (currentQuery) executeSearch(currentQuery);
            });
        }
    });

    // Risk Vector Sliders (Dynamic Re-arbitration)
    const sliders = [
        { id: 'slider-warranty', key: 'warrantyPriority', valId: 'val-warranty' },
        { id: 'slider-speed', key: 'speedPriority', valId: 'val-speed' },
        { id: 'slider-trust', key: 'trustTolerance', valId: 'val-trust' }
    ];

    sliders.forEach(s => {
        const input = document.getElementById(s.id);
        const valEl = document.getElementById(s.valId);
        if (input) {
            input.addEventListener('input', () => {
                const num = parseFloat(input.value);
                if (valEl) valEl.textContent = `${Math.round(num * 100)}%`;
                store.setRiskPreferences({ [s.key]: num });
                debounceReRank();
            });
        }
    });

    // Self-Healer HUD Actions
    const btnTest = document.getElementById('btn-self-test');
    if (btnTest) btnTest.addEventListener('click', triggerSelfTest);

    const btnFix = document.getElementById('btn-self-fix');
    if (btnFix) btnFix.addEventListener('click', triggerSelfFix);

    const btnLearn = document.getElementById('btn-self-learn');
    if (btnLearn) btnLearn.addEventListener('click', triggerSelfLearn);

    // Modal Close Triggers
    const closeDossier = document.getElementById('modal-close-dossier');
    if (closeDossier) closeDossier.addEventListener('click', closeDossierModal);

    const dossierModal = document.getElementById('dossier-modal');
    if (dossierModal) {
        dossierModal.addEventListener('click', (e) => {
            if (e.target === dossierModal) closeDossierModal();
        });
    }

    const closePayPal = document.getElementById('modal-close-paypal');
    if (closePayPal) closePayPal.addEventListener('click', closePayPalCheckoutModal);

    const paypalModal = document.getElementById('paypal-checkout-modal');
    if (paypalModal) {
        paypalModal.addEventListener('click', (e) => {
            if (e.target === paypalModal) closePayPalCheckoutModal();
        });
    }

    const btnInstincts = document.getElementById('btn-view-instincts');
    if (btnInstincts) btnInstincts.addEventListener('click', openInstinctsModal);

    const closeInstincts = document.getElementById('modal-close-instincts');
    if (closeInstincts) closeInstincts.addEventListener('click', closeInstinctsModal);

    const instinctsModal = document.getElementById('instincts-modal');
    if (instinctsModal) {
        instinctsModal.addEventListener('click', (e) => {
            if (e.target === instinctsModal) closeInstinctsModal();
        });
    }

    // Clear Terminal Log
    const clearLogBtn = document.getElementById('btn-clear-log');
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', () => {
            const body = document.getElementById('terminal-body');
            if (body) body.innerHTML = '';
        });
    }
}

let reRankTimer = null;
function debounceReRank() {
    clearTimeout(reRankTimer);
    reRankTimer = setTimeout(() => {
        const risk = store.riskPreferences;
        const sent = wsClient.send('re_rank', {
            session_id: store.sessionId,
            warranty_priority: risk.warrantyPriority,
            speed_priority: risk.speedPriority,
            trust_tolerance: risk.trustTolerance,
        });
        if (sent) {
            showToast("Dynamic re-arbitration triggered via WebSocket.", "info");
        }
    }, 250);
}

export function executeSearch(query) {
    if (!query) return;

    // 1. Cancel prior pending HTTP search if active
    if (currentSearchController) {
        currentSearchController.abort();
    }
    currentSearchController = new AbortController();
    const searchToken = ++currentSearchToken;

    const prefs = store.preferences;
    const risk = store.riskPreferences;

    const payload = {
        query: query,
        language: prefs.language,
        country: prefs.country,
        currency: prefs.currency,
        preferred_payment: prefs.preferredPayment,
        session_id: store.sessionId,
        warranty_priority: risk.warrantyPriority,
        speed_priority: risk.speedPriority,
        trust_tolerance: risk.trustTolerance,
    };

    // Update UI status
    const statusText = document.getElementById('search-status-text');
    if (statusText) statusText.textContent = `Deploying multi-agent swarm for '${query}'...`;

    appendTerminalLog("Coordinator", `Deploying Tier-1 Scout Swarm for query: '${query}' in region: ${prefs.country} (${prefs.currency})...`);

    // Try WebSocket first
    const sentWs = wsClient.send('search', payload);
    if (!sentWs) {
        // Fallback to HTTP POST
        fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: currentSearchController.signal
        })
        .then(res => res.json())
        .then(state => {
            if (searchToken === currentSearchToken) {
                applySearchResults(state);
            }
        })
        .catch(err => {
            if (err.name !== 'AbortError') {
                console.error("HTTP Search Error:", err);
                showToast(`Search error: ${err.message}`, "error");
            }
        });
    } else {
        // Safety fallback: if WebSocket does not deliver within 4s, fetch via HTTP
        setTimeout(() => {
            if (searchToken === currentSearchToken && (!store.lastState || store.lastState.search_query !== query)) {
                fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    signal: currentSearchController.signal
                })
                .then(res => res.json())
                .then(state => {
                    if (searchToken === currentSearchToken) {
                        applySearchResults(state);
                    }
                })
                .catch(() => {});
            }
        }, 4000);
    }
}

function handleInboundWebSocket(msg) {
    if (!msg || !msg.type) return;

    if (msg.type === 'AGENT_EVENT' && msg.event) {
        const ev = msg.event;
        appendTerminalLog(ev.source_agent || "Agent", ev.content || "");
    } else if (msg.type === 'FINAL_RESULT' && msg.state) {
        applySearchResults(msg.state);
        showToast("Swarm synthesis complete: Comparison matrix updated.", "success");
    } else if (msg.type === 'CHALLENGE_RESOLVED' && msg.state) {
        applySearchResults(msg.state);
        showToast(`Challenge resolved for listing [${msg.listing_id}].`, "success");
    } else if (msg.type === 'ERROR') {
        showToast(`Agent error: ${msg.message}`, "error");
    }
}

function applySearchResults(state) {
    if (!state) return;
    store.setLastState(state);

    const statusText = document.getElementById('search-status-text');
    if (statusText) statusText.textContent = `Synthesis complete: Audited ${state.raw_listings ? state.raw_listings.length : 0} retailers.`;

    // 1. Render 3 Strategic Deal Cards
    renderStrategicCards(state.final_options || []);

    // 2. Render AG Grid Comparison Matrix
    updateGridData(state.comparison_matrix || []);

    // 3. Render Price Analytics & Trajectory Chart
    if (state.price_analytics) {
        renderPriceTrajectory(state.price_analytics, 'price-trajectory-chart');
    }

    // 4. Update KPI ribbon
    updateKpiRibbon(state);
}

function updateKpiRibbon(state) {
    const totalEl = document.getElementById('kpi-total-listings');
    if (totalEl) totalEl.textContent = (state.comparison_matrix || []).length;

    const lowestEl = document.getElementById('kpi-lowest-tco');
    if (lowestEl && state.final_options && state.final_options.length) {
        const opt = state.final_options[0];
        lowestEl.textContent = `${opt.display_currency} ${opt.risk_adjusted_tco.toLocaleString()}`;
    }

    const codCountEl = document.getElementById('kpi-cod-count');
    if (codCountEl) {
        const count = (state.comparison_matrix || []).filter(m => m.cod_available).length;
        codCountEl.textContent = count;
    }

    const openBoxCountEl = document.getElementById('kpi-openbox-count');
    if (openBoxCountEl) {
        const count = (state.comparison_matrix || []).filter(m => m.open_box_delivery).length;
        openBoxCountEl.textContent = count;
    }
}

function renderStrategicCards(options) {
    const grid = document.getElementById('strategic-cards-grid');
    if (!grid) return;

    if (!options.length) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 2rem;">No verified deals available for this query.</div>`;
        return;
    }

    grid.innerHTML = '';

    for (const opt of options) {
        const listing = opt.listing || {};
        const warranty = opt.warranty || {};
        const trust = opt.trust || {};
        const paypal = opt.paypal || opt.paypal_protection || {};

        const tier = opt.recommendation_tier || "OPTIMAL_VALUE";
        const ribbonClass = tier === "OPTIMAL_VALUE" ? "ribbon-optimal" : (tier === "MAX_PROTECTION" ? "ribbon-protection" : "ribbon-budget");
        const badgeClass = tier === "OPTIMAL_VALUE" ? "tier-optimal" : (tier === "MAX_PROTECTION" ? "tier-protection" : "tier-budget");
        const tierTitle = tier === "OPTIMAL_VALUE" ? "🏆 Optimal Value Champion" : (tier === "MAX_PROTECTION" ? "🛡️ Maximum Peace-of-Mind (ADP)" : "⚠️ Budget Sticker (Requires Caution)");

        const card = document.createElement('div');
        card.className = 'deal-card';
        card.innerHTML = `
            <div class="card-ribbon ${ribbonClass}"></div>
            <div class="tier-badge ${badgeClass}">${tierTitle}</div>

            <div class="deal-title">${escapeHtml(listing.product_title || 'Certified Item')}</div>

            <div class="deal-merchant-row">
                <span>🏬 ${escapeHtml(listing.merchant || 'Retailer')} • ${escapeHtml(listing.origin_country || 'US')}</span>
                <span class="hud-status-badge status-optimal">Trust: ${trust.overall_score || 85}/100</span>
            </div>

            <div class="price-box">
                <div class="price-main">
                    <div>
                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Risk-Adjusted TCO</div>
                        <div class="tco-val mono-font">${escapeHtml(opt.display_currency || '$')} ${opt.risk_adjusted_tco ? Number(opt.risk_adjusted_tco).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Sticker Outlay</div>
                        <div class="sticker-price mono-font">${escapeHtml(opt.display_currency || '$')} ${opt.converted_cash_outlay ? Number(opt.converted_cash_outlay).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}</div>
                    </div>
                </div>
            </div>

            <div class="feature-chips">
                ${listing.cod_available ? `<span class="chip chip-success">💵 COD Available</span>` : `<span class="chip">Prepaid Only</span>`}
                ${listing.open_box_delivery ? `<span class="chip chip-success">📦 Open Box OTP</span>` : `<span class="chip">Sealed Box</span>`}
                ${warranty.has_adp ? `<span class="chip chip-success">🛡️ ADP Included</span>` : `<span class="chip">${warranty.oem_warranty_months || 12}-Mo OEM</span>`}
            </div>

            <div style="font-size: 11.5px; color: #94a3b8; line-height: 1.4; margin-bottom: 1rem; flex: 1;">
                ${escapeHtml(opt.tier_reason || '')}
            </div>

            <!-- PayPal Pay in 4 Financing Callout -->
            <div style="background: rgba(0, 112, 186, 0.08); border: 1px solid rgba(0, 112, 186, 0.25); border-radius: 6px; padding: 8px 10px; margin-bottom: 12px; font-size: 11px; color: #93c5fd;">
                <strong>PayPal Pay in 4:</strong> 4 payments of <strong>${escapeHtml(opt.display_currency || '$')} ${paypal.pay_in_4_biweekly ? Number(paypal.pay_in_4_biweekly).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}</strong> bi-weekly with 0% APR.
            </div>

            <div style="display: flex; gap: 8px;">
                <button type="button" class="control-btn btn-primary btn-checkout-deal" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-price="${escapeHtml(opt.display_currency || '$')} ${opt.risk_adjusted_tco ? Number(opt.risk_adjusted_tco).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}" data-title="${escapeHtml(listing.product_title || '')}" style="flex: 1; justify-content: center;">
                    Pay with PayPal
                </button>
                <button type="button" class="control-btn btn-view-dossier" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-price="${escapeHtml(opt.display_currency || '$')} ${opt.risk_adjusted_tco ? Number(opt.risk_adjusted_tco).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}" title="Inspect Cryptographic Section 13 Dispute Dossier">
                    🛡️ Dossier
                </button>
                <button type="button" class="btn-flag-deal" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-domain="${escapeHtml(listing.merchant_domain || '')}" style="background: transparent; border: 1px solid rgba(244, 63, 94, 0.35); color: #fda4af; border-radius: 6px; padding: 6px 10px; font-size: 11px; cursor: pointer; display: flex; align-items: center; gap: 4px; transition: background 0.15s;" title="Teach Self-Healer: Flag & Quarantine Listing">
                    🚩 Flag
                </button>
            </div>
        `;

        grid.appendChild(card);
    }

    // Wire deal checkout & dossier buttons
    grid.querySelectorAll('.btn-checkout-deal').forEach(b => {
        b.addEventListener('click', () => {
            const m = b.getAttribute('data-merchant');
            const p = b.getAttribute('data-price');
            const id = b.getAttribute('data-order-id');
            const title = b.getAttribute('data-title') || '';
            openPayPalCheckoutModal(id, m, p, title);
        });
    });

    grid.querySelectorAll('.btn-view-dossier').forEach(b => {
        b.addEventListener('click', () => {
            const m = b.getAttribute('data-merchant');
            const p = b.getAttribute('data-price');
            const id = b.getAttribute('data-order-id');
            openDossierModal(`PP-${id}`, m, p);
        });
    });

    // Wire 1-Click Prompt Learning & Quarantine Feedback
    grid.querySelectorAll('.btn-flag-deal').forEach(b => {
        b.addEventListener('click', async () => {
            const m = b.getAttribute('data-merchant');
            const d = b.getAttribute('data-domain');
            const id = b.getAttribute('data-order-id');
            const card = b.closest('.deal-card');
            if (card) {
                card.style.opacity = '0.3';
                card.style.pointerEvents = 'none';
            }
            await quarantineMerchantFromUI(m, d, id, 'User Flagged 404/Scam/Out-of-Stock');
            if (card) card.remove();
        });
    });
}

function updatePromptBadges(query) {
    const bar = document.getElementById('prompt-constraints-bar');
    if (!bar) return;
    const q = (query || '').toLowerCase();
    
    const hasInStock = /in\s*stock|available|must\s*be\s*in\s*stock/.test(q);
    const has404 = /no\s*404|no\s*dead|working\s*links|zero\s*404/.test(q);
    const hasAntiScam = /no\s*scam|avoid\s*scam|reputable|verified|trusted/.test(q);
    const hasAccessories = /no\s*accessories|no\s*parts|full\s*product/.test(q);

    bar.innerHTML = `
        <span style="font-size: 11px; color: #94a3b8; font-weight: 600;">Active Learned Guardrails:</span>
        <span class="hud-status-badge status-optimal" style="font-size: 10.5px; padding: 2px 8px; border-color: ${hasInStock ? '#10b981' : 'rgba(16, 185, 129, 0.4)'}; background: ${hasInStock ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.1)'};">
            🟢 In-Stock Verified Only ${hasInStock ? '✓ (Enforced via Prompt)' : ''}
        </span>
        <span class="hud-status-badge status-optimal" style="font-size: 10.5px; padding: 2px 8px; border-color: ${has404 ? '#10b981' : 'rgba(16, 185, 129, 0.4)'}; background: ${has404 ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.1)'};">
            🛡️ Zero 404 Dead-Links ${has404 ? '✓ (Enforced via Prompt)' : ''}
        </span>
        <span class="hud-status-badge status-optimal" style="font-size: 10.5px; padding: 2px 8px; border-color: ${hasAntiScam ? '#10b981' : 'rgba(16, 185, 129, 0.4)'}; background: ${hasAntiScam ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.1)'};">
            🔒 Anti-Scam Shield Active ${hasAntiScam ? '✓ (Enforced via Prompt)' : ''}
        </span>
        <span class="hud-status-badge status-optimal" style="font-size: 10.5px; padding: 2px 8px; border-color: ${hasAccessories ? '#10b981' : 'rgba(16, 185, 129, 0.4)'}; background: ${hasAccessories ? 'rgba(16, 185, 129, 0.25)' : 'rgba(16, 185, 129, 0.1)'};">
            🚫 Accessory Hijack Filter ${hasAccessories ? '✓ (Enforced via Prompt)' : ''}
        </span>
    `;
}

function appendTerminalLog(source, content) {
    const body = document.getElementById('terminal-body');
    if (!body) return;

    const timeStr = new Date().toTimeString().split(' ')[0];
    const row = document.createElement('div');
    row.className = 'log-entry';
    row.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        <span class="log-agent">&lt;${escapeHtml(source)}&gt;</span>
        <span class="log-content">${escapeHtml(content)}</span>
    `;

    body.appendChild(row);
    // Keep max 200 log items
    if (body.children.length > 200) {
        body.removeChild(body.firstChild);
    }
    body.scrollTop = body.scrollHeight;
}
