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
import { openWorkflowArbitrageModal, closeWorkflowArbitrageModal } from './cart_arbitrage_modal.js';
import { renderPriceTrajectory } from './charts.js';
import { escapeHtml, sanitizeUrl } from './security.js';
import { initMultimodalSearch } from './multimodal_search.js';
import { initConciergeBot } from './concierge_bot.js';

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

    // 6. Wire Multimodal Voice & Visual Search
    initMultimodalSearch({
        executeSearch: (query, mode, itemsList) => executeSearch(query, mode, itemsList),
        getSearchMode: () => currentSearchMode,
        getBundleItems: () => bundleItems,
        addBundleItem: (item) => addBundleItem(item)
    });

    // 7. Wire Sentinel AI Concierge Chatbot & Voice Bot for Doubts & Queries
    initConciergeBot();
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

let currentSearchMode = "single";
let bundleItems = ["27-inch 4K Monitor", "Mechanical Keyboard", "Ergonomic Chair", "1080p Webcam"];

export function setMode(mode) {
    currentSearchMode = mode;
    const singleBtn = document.getElementById('mode-single-btn');
    const bundleBtn = document.getElementById('mode-bundle-btn');
    const imageBtn = document.getElementById('mode-image-btn');
    const bundleBuilder = document.getElementById('bundle-builder-container');
    const imageContainer = document.getElementById('image-search-container');
    const searchInput = document.getElementById('search-input');
    const searchBtnLabel = document.getElementById('search-btn-label');

    const dimBtn = (btn) => {
        if (!btn) return;
        btn.classList.remove('active');
        btn.style.setProperty('background-color', 'rgba(15, 23, 42, 0.75)', 'important');
        btn.style.setProperty('border', '1px solid rgba(255, 255, 255, 0.12)', 'important');
        btn.style.setProperty('color', '#94a3b8', 'important');
    };

    const activateBtn = (btn) => {
        if (!btn) return;
        btn.classList.add('active');
        btn.style.setProperty('background-color', 'rgba(14, 165, 233, 0.18)', 'important');
        btn.style.setProperty('border', '1px solid #38bdf8', 'important');
        btn.style.setProperty('color', '#38bdf8', 'important');
    };

    if (mode === 'bundle') {
        dimBtn(singleBtn);
        dimBtn(imageBtn);
        activateBtn(bundleBtn);
        if (bundleBuilder) bundleBuilder.style.display = 'block';
        if (imageContainer) imageContainer.style.display = 'none';
        if (searchBtnLabel) searchBtnLabel.textContent = '📦 Search Bundle Discounts';
        if (searchInput) {
            searchInput.placeholder = 'e.g. 27-inch 4K Monitor, Mechanical Keyboard, Ergonomic Chair, 1080p Webcam';
            if (!searchInput.value) {
                searchInput.value = bundleItems.join(', ');
            }
        }
        renderBundlePills();
    } else if (mode === 'image') {
        dimBtn(singleBtn);
        dimBtn(bundleBtn);
        activateBtn(imageBtn);
        if (bundleBuilder) bundleBuilder.style.display = 'none';
        if (imageContainer) imageContainer.style.display = 'block';
        if (searchBtnLabel) searchBtnLabel.textContent = 'Arbitrate Deals';
        if (searchInput) {
            searchInput.placeholder = 'Upload, drop, or select product image below, or type query...';
        }
    } else {
        // Single Deal mode (default)
        dimBtn(bundleBtn);
        dimBtn(imageBtn);
        activateBtn(singleBtn);
        if (bundleBuilder) bundleBuilder.style.display = 'none';
        if (imageContainer) imageContainer.style.display = 'none';
        if (searchBtnLabel) searchBtnLabel.textContent = 'Arbitrate Deals';
        if (searchInput) {
            searchInput.placeholder = 'Search any product (e.g., Sony WH-1000XM5, MacBook Pro M3, Epson L3250)...';
        }
    }
}

export function renderBundlePills() {
    const pillsContainer = document.getElementById('bundle-pills-list');
    const countBadge = document.getElementById('bundle-item-count-badge');
    if (!pillsContainer) return;

    if (countBadge) {
        countBadge.textContent = `${bundleItems.length} items`;
    }

    if (bundleItems.length === 0) {
        pillsContainer.innerHTML = `<span style="font-size: 11.5px; color: #64748b; font-style: italic;">No items added yet. Type an item below or enter comma-separated items above.</span>`;
        return;
    }

    pillsContainer.innerHTML = bundleItems.map((item, index) => `
        <span class="bundle-item-pill">
            <span>📦 ${escapeHtml(item)}</span>
            <span class="bundle-item-pill-remove" data-index="${index}" title="Remove item">×</span>
        </span>
    `).join('');

    pillsContainer.querySelectorAll('.bundle-item-pill-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.getAttribute('data-index'), 10);
            removeBundleItem(idx);
        });
    });
}

export function addBundleItem(item) {
    const trimmed = (item || "").trim();
    if (!trimmed) return;
    if (!bundleItems.includes(trimmed)) {
        bundleItems.push(trimmed);
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = bundleItems.join(', ');
        }
        renderBundlePills();
    }
}

export function removeBundleItem(index) {
    if (index >= 0 && index < bundleItems.length) {
        bundleItems.splice(index, 1);
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = bundleItems.join(', ');
        }
        renderBundlePills();
    }
}

export function clearBundleItems() {
    bundleItems = [];
    const searchInput = document.getElementById('search-input');
    if (searchInput && currentSearchMode === 'bundle') {
        searchInput.value = '';
    }
    renderBundlePills();
}

function setupEventListeners() {
    // Mode Switcher Buttons
    const singleModeBtn = document.getElementById('mode-single-btn');
    if (singleModeBtn) {
        singleModeBtn.addEventListener('click', () => setMode('single'));
    }

    const bundleModeBtn = document.getElementById('mode-bundle-btn');
    if (bundleModeBtn) {
        bundleModeBtn.addEventListener('click', () => setMode('bundle'));
    }

    const imageModeBtn = document.getElementById('mode-image-btn');
    if (imageModeBtn) {
        imageModeBtn.addEventListener('click', () => setMode('image'));
    }

    // Bundle Quick Add Item Input & Buttons
    const bundleQuickInput = document.getElementById('bundle-item-quick-input');
    const btnAddBundleItem = document.getElementById('btn-add-bundle-item');
    const btnClearBundleItems = document.getElementById('btn-clear-bundle-items');

    if (btnAddBundleItem && bundleQuickInput) {
        btnAddBundleItem.addEventListener('click', () => {
            addBundleItem(bundleQuickInput.value);
            bundleQuickInput.value = '';
        });
        bundleQuickInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addBundleItem(bundleQuickInput.value);
                bundleQuickInput.value = '';
            }
        });
    }

    if (btnClearBundleItems) {
        btnClearBundleItems.addEventListener('click', () => {
            clearBundleItems();
        });
    }

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
                const isBundleIntent = currentSearchMode === 'bundle' || 
                    q.includes(',') || 
                    ['setup', 'bundle', 'bulk', 'kit', 'pack', 'knapsack', 'peripherals', 'workstation', 'rig', 'wfh'].some(k => q.toLowerCase().includes(k));

                if (isBundleIntent && currentSearchMode !== 'bundle') {
                    setMode('bundle');
                }

                let itemsList = null;
                if (isBundleIntent) {
                    if (bundleItems.length > 0) {
                        itemsList = bundleItems;
                    } else if (q.includes(',')) {
                        itemsList = q.split(',').map(s => s.trim()).filter(Boolean);
                    }
                }
                executeSearch(q, isBundleIntent ? 'bundle' : 'single', itemsList);
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            updatePromptBadges(searchInput.value);
            const q = searchInput.value.trim();
            // If user typed comma-separated in bundle mode, auto-populate pills
            if (currentSearchMode === 'bundle' && q.includes(',')) {
                const parts = q.split(',').map(s => s.trim()).filter(Boolean);
                if (parts.length > 0 && JSON.stringify(parts) !== JSON.stringify(bundleItems)) {
                    bundleItems = parts;
                    renderBundlePills();
                }
            }
        });
        updatePromptBadges(searchInput.value);
    }

    // Quick Query Tag & Workflow Preset Buttons
    document.querySelectorAll('.query-tag-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            clearTimeout(searchDebounceTimer);
            const query = btn.getAttribute('data-query');
            if (query) {
                if (searchInput) searchInput.value = query;
                lastExecutedQuery = query;
                if (btn.classList.contains('workflow-preset-btn')) {
                    setMode('bundle');
                    const qLow = query.toLowerCase();
                    if (qLow.includes('wfh')) {
                        bundleItems = ['27-inch 4K Monitor', 'Mechanical Keyboard', 'Ergonomic Chair', 'Webcam'];
                    } else if (qLow.includes('gaming')) {
                        bundleItems = ['Gaming Monitor', 'Wireless Gaming Mouse', 'RGB Mechanical Keyboard', 'Spatial Audio Headset'];
                    } else if (qLow.includes('podcast')) {
                        bundleItems = ['Studio Microphone', 'Audio Interface', 'Monitor Headphones', 'Boom Arm'];
                    } else if (qLow.includes('developer')) {
                        bundleItems = ['Thunderbolt 4 Dock', 'NVMe 2TB High-Speed SSD', 'Vertical Aluminum Stand', '4K Ultra-Clear Hub'];
                    }
                    renderBundlePills();
                    executeSearch(query, 'bundle', bundleItems);
                } else {
                    executeSearch(query, 'single');
                }
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

    const closeArbitrage = document.getElementById('modal-close-arbitrage');
    if (closeArbitrage) closeArbitrage.addEventListener('click', closeWorkflowArbitrageModal);

    const arbitrageModal = document.getElementById('workflow-arbitrage-modal');
    if (arbitrageModal) {
        arbitrageModal.addEventListener('click', (e) => {
            if (e.target === arbitrageModal) closeWorkflowArbitrageModal();
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

export function executeSearch(query, mode = null, itemsList = null) {
    if (!query) return;

    // 1. Cancel prior pending HTTP search if active
    if (currentSearchController) {
        currentSearchController.abort();
    }
    currentSearchController = new AbortController();
    const searchToken = ++currentSearchToken;

    const prefs = store.preferences;
    const risk = store.riskPreferences;

    const isBundle = mode === 'bundle' || 
        currentSearchMode === 'bundle' || 
        ['setup', 'bundle', 'bulk', 'kit', 'pack', 'knapsack', 'peripherals', 'workstation', 'rig', 'wfh'].some(k => query.toLowerCase().includes(k)) ||
        (query.includes(',') && query.split(',').length >= 2);

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
        mode: isBundle ? 'bundle' : 'single',
        items_list: itemsList || (isBundle && bundleItems.length ? bundleItems : null)
    };

    // Update UI status
    const statusText = document.getElementById('search-status-text');
    if (statusText) statusText.textContent = isBundle ? `Deploying Knapsack Cart-Split Swarm for '${query}'...` : `Deploying multi-agent swarm for '${query}'...`;

    appendTerminalLog("Coordinator", isBundle ? 
        `Initiating Knapsack Cart-Split Swarm for bundle: '${query}' across Amazon, Flipkart, & OEM Direct...` :
        `Deploying Tier-1 Scout Swarm for query: '${query}' in region: ${prefs.country} (${prefs.currency})...`
    );

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

function renderBundleSpotlight(state) {
    const container = document.getElementById('bundle-spotlight-section');
    if (!container) return;

    const split = state.cart_split_result;
    if (!split || !split.sub_carts || split.sub_carts.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    const optTotal = split.optimized_total || 0;
    const netSavings = split.net_arbitrage_savings || 0;
    const savingsPct = split.savings_percentage || 0;
    const cardSavings = split.card_bonus_savings || 0;
    const shipSavings = split.shipping_savings || 0;
    const platformCut = split.platform_arbitrage_cut || 0;
    const subCarts = split.sub_carts || [];
    const monopolies = split.monopoly_alternatives || {};

    let subCartsHtml = '';
    subCarts.forEach(sc => {
        const retColor = sc.retailer === 'Amazon' ? '#ff9900' : sc.retailer === 'Flipkart' ? '#2874f0' : '#10b981';
        let itemsHtml = (sc.items || []).map(itm => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px dashed rgba(255,255,255,0.06); font-size: 12px;">
                <div>
                    <span style="font-weight: 700; color: #f8fafc;">${escapeHtml(itm.title)}</span>
                    <span style="color: #64748b; font-size: 11px; margin-left: 6px;">[${escapeHtml(itm.category)}]</span>
                </div>
                <div style="font-weight: 700; color: #38bdf8; font-family: monospace;">
                    ₹${Number(itm.current_price).toLocaleString('en-IN')}
                </div>
            </div>
        `).join('');

        subCartsHtml += `
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid ${retColor}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-weight: 700; color: ${retColor}; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                        <span>🛒 ${escapeHtml(sc.retailer)} Basket</span>
                        <span style="font-size: 10px; color: #94a3b8;">(${sc.items ? sc.items.length : 0} items)</span>
                    </div>
                    <div style="font-weight: 800; color: #f8fafc; font-family: monospace; font-size: 13px;">
                        ₹${Number(sc.retailer_total).toLocaleString('en-IN')}
                    </div>
                </div>
                <div>${itemsHtml}</div>
                <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; color: #94a3b8; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px;">
                    <span>Subtotal: ₹${Number(sc.items_subtotal).toLocaleString('en-IN')}</span>
                    <span>Shipping: ${sc.shipping_fee === 0 ? '<strong style="color: #10b981;">FREE</strong>' : `₹${sc.shipping_fee}`}</span>
                    <span>Card Discount: <strong style="color: #34d399;">-₹${Number(sc.card_discount_applied).toLocaleString('en-IN')}</strong></span>
                </div>
            </div>
        `;
    });

    let monopoliesHtml = Object.entries(monopolies).map(([ret, mono]) => {
        const penalty = (mono.total_cost || 0) - optTotal;
        return `
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 8px 12px; text-align: center; flex: 1; min-width: 130px;">
                <div style="font-size: 11px; color: #94a3b8; font-weight: 600;">${escapeHtml(ret)} Monopoly</div>
                <div style="font-size: 14px; font-weight: 800; color: #cbd5e1; font-family: monospace; margin: 2px 0;">₹${Number(mono.total_cost || 0).toLocaleString('en-IN')}</div>
                <div style="font-size: 10px; color: ${penalty > 0 ? '#f87171' : '#94a3b8'}; font-weight: 700;">
                    ${penalty > 0 ? `+₹${Number(penalty).toLocaleString('en-IN')} penalty` : 'Baseline'}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="bundle-spotlight-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                        <span>📦 Multi-Retailer Bundle / Bulk Arbitrage Breakdown</span>
                        <span style="background: rgba(56, 189, 248, 0.2); color: #7dd3fc; padding: 2px 8px; border-radius: 9999px; font-size: 10px;">KNAPSACK GLOBAL OPTIMUM</span>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #ffffff; margin-top: 2px;">
                        ${escapeHtml(state.search_query)}
                    </div>
                </div>
                <div>
                    <span style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #34d399; font-weight: 800; padding: 6px 12px; border-radius: 8px; font-size: 13px;">
                        💰 ₹${Number(netSavings).toLocaleString('en-IN')} SAVED (${savingsPct}%)
                    </span>
                </div>
            </div>

            <!-- KPI Row -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; margin-bottom: 14px;">
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #a7f3d0; text-transform: uppercase; font-weight: 700;">Net Arbitrage Savings</div>
                    <div style="font-size: 17px; font-weight: 800; color: #10b981; font-family: monospace;">₹${Number(netSavings).toLocaleString('en-IN')}</div>
                    <div style="font-size: 9px; color: #6ee7b7;">vs Single Retailer</div>
                </div>
                <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #7dd3fc; text-transform: uppercase; font-weight: 700;">Optimal Split Total</div>
                    <div style="font-size: 17px; font-weight: 800; color: #38bdf8; font-family: monospace;">₹${Number(optTotal).toLocaleString('en-IN')}</div>
                    <div style="font-size: 9px; color: #bae6fd;">${subCarts.length} Cross-Store Baskets</div>
                </div>
                <div style="background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.25); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #d8b4fe; text-transform: uppercase; font-weight: 700;">Stacked Card Discounts</div>
                    <div style="font-size: 17px; font-weight: 800; color: #c084fc; font-family: monospace;">₹${Number(cardSavings).toLocaleString('en-IN')}</div>
                    <div style="font-size: 9px; color: #e9d5ff;">Threshold Bonuses</div>
                </div>
                <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #86efac; text-transform: uppercase; font-weight: 700;">Free Shipping</div>
                    <div style="font-size: 17px; font-weight: 800; color: #22c55e; font-family: monospace;">FREE (₹0)</div>
                    <div style="font-size: 9px; color: #bbf7d0;">₹${Number(shipSavings).toLocaleString('en-IN')} Fees Waived</div>
                </div>
            </div>

            <!-- Sub Carts -->
            <div style="margin-bottom: 12px;">
                <div style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;">Matched Products & Multi-Retailer Distribution:</div>
                ${subCartsHtml}
            </div>

            <!-- Monopoly Alternatives -->
            <div style="margin-bottom: 14px;">
                <div style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;">Single-Retailer Monopoly Cost Penalties:</div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    ${monopoliesHtml}
                </div>
            </div>

            <!-- CTAs -->
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button type="button" id="btn-spotlight-lock" class="control-btn btn-primary" style="flex: 2; min-width: 180px; justify-content: center; font-weight: 700; background: linear-gradient(135deg, #0ea5e9, #2563eb); border: 1px solid #38bdf8;">
                    🎯 1-Click Lock Bundle & Checkout
                </button>
                <button type="button" id="btn-spotlight-merkle" class="control-btn" style="flex: 1.5; min-width: 160px; justify-content: center; background: rgba(99, 102, 241, 0.15); border-color: rgba(99, 102, 241, 0.4); color: #a5b4fc; font-weight: 600;">
                    📜 Merkle Dispute Dossier
                </button>
                <button type="button" id="btn-spotlight-modal" class="control-btn" style="flex: 1; min-width: 120px; justify-content: center;">
                    🔍 Full Modal View
                </button>
            </div>
        </div>
    `;

    const btnLock = document.getElementById('btn-spotlight-lock');
    if (btnLock) {
        btnLock.addEventListener('click', async () => {
            btnLock.disabled = true;
            btnLock.textContent = "Securing Pre-Authorized Lock...";
            try {
                const firstCart = (subCarts[0] && subCarts[0].items && subCarts[0].items[0]) ? subCarts[0].items[0] : null;
                const listingId = firstCart ? firstCart.id : 'wf-bundle-pack';
                const res = await fetch('/api/snipe/lock', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        listing_id: listingId,
                        target_price: optTotal,
                        preauth_payment_method: 'ONE_CLICK_ESCROW',
                        auto_execute_within_seconds: 600
                    })
                });
                if (res.ok) {
                    const data = await res.json();
                    showToast(`Bundle Locked! Escrow: ${data.receipt_hash.substring(0, 16)}...`, "success");
                    btnLock.textContent = "🔒 Bundle Rate Locked (10m Escrow)";
                    btnLock.style.background = "#10b981";
                }
            } catch (err) {
                showToast("Failed to lock deal: " + err.message, "error");
                btnLock.disabled = false;
                btnLock.textContent = "🎯 1-Click Lock Bundle & Checkout";
            }
        });
    }

    const btnMerkle = document.getElementById('btn-spotlight-merkle');
    if (btnMerkle) {
        btnMerkle.addEventListener('click', () => {
            openDossierModal(split.workflow_id || 'wf-bundle-escrow', 'Multi-Retailer Knapsack Split (Amazon + Flipkart + OEM)', `₹${optTotal}`);
        });
    }

    const btnModal = document.getElementById('btn-spotlight-modal');
    if (btnModal) {
        btnModal.addEventListener('click', () => {
            openWorkflowArbitrageModal(state.search_query);
        });
    }

    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function applySearchResults(state) {
    if (!state) return;
    store.setLastState(state);

    const statusText = document.getElementById('search-status-text');
    if (statusText) statusText.textContent = `Synthesis complete: Audited ${state.raw_listings ? state.raw_listings.length : 0} retailers.`;

    // 0. Render Dedicated Bundle Spotlight Banner if bundle arbitrated
    renderBundleSpotlight(state);

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

    // 5. Scroll smoothly to results
    const spotlight = document.getElementById('bundle-spotlight-section');
    if (spotlight && state.cart_split_result) {
        spotlight.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        const cardsSection = document.getElementById('strategic-cards-grid');
        if (cardsSection && state.final_options && state.final_options.length > 0) {
            cardsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
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

            <div class="deal-title">
                <a href="${escapeHtml(listing.listing_url || '#')}" target="_blank" rel="noopener noreferrer" style="color: #ffffff; text-decoration: none; display: inline-flex; align-items: flex-start; gap: 6px;" title="Open live verified listing on ${escapeHtml(listing.merchant || 'Store')} (200 OK Guaranteed)">
                    <span>${escapeHtml(listing.product_title || 'Certified Item')}</span>
                    <span style="color: #60a5fa; font-size: 12px;">↗</span>
                </a>
            </div>

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

            <!-- Visual Truth & Packaging Seal Badge -->
            <div class="visual-seal-badge-row" style="display: flex; align-items: center; justify-content: space-between; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 5px 8px; margin: 8px 0; font-size: 11px;">
                <div style="display: flex; align-items: center; gap: 5px; color: #34d399; font-weight: 700;">
                    <span>🛡️ Packaging Shield:</span>
                    <span style="color: #a7f3d0; font-weight: 600;">${listing.open_box_delivery ? 'OTP Doorstep Verified' : '100% Factory Sealed'}</span>
                </div>
                <span class="hud-status-badge status-optimal" style="font-size: 9px; padding: 1px 6px;">SEAL INTACT</span>
            </div>

            <div style="font-size: 11.5px; color: #94a3b8; line-height: 1.4; margin-bottom: 1rem; flex: 1;">
                ${escapeHtml(opt.tier_reason || '')}
            </div>

            <!-- PayPal Pay in 4 Financing Callout -->
            <div style="background: rgba(0, 112, 186, 0.08); border: 1px solid rgba(0, 112, 186, 0.25); border-radius: 6px; padding: 8px 10px; margin-bottom: 12px; font-size: 11px; color: #93c5fd;">
                <strong>PayPal Pay in 4:</strong> 4 payments of <strong>${escapeHtml(opt.display_currency || '$')} ${paypal.pay_in_4_biweekly ? Number(paypal.pay_in_4_biweekly).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}</strong> bi-weekly with 0% APR.
            </div>

            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <a href="${escapeHtml(listing.listing_url || '#')}" target="_blank" rel="noopener noreferrer" class="control-btn" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 4px; padding: 6px 10px; font-size: 11px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); color: #93c5fd; border-radius: 6px;" title="Open Verified Live Product Page on ${escapeHtml(listing.merchant || 'Merchant')}">
                    Store ↗
                </a>
                <button type="button" class="control-btn btn-primary btn-checkout-deal" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-price="${escapeHtml(opt.display_currency || '$')} ${opt.risk_adjusted_tco ? Number(opt.risk_adjusted_tco).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}" data-title="${escapeHtml(listing.product_title || '')}" style="flex: 1; justify-content: center;">
                    Pay with PayPal
                </button>
                <button type="button" class="control-btn btn-view-dossier" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-price="${escapeHtml(opt.display_currency || '$')} ${opt.risk_adjusted_tco ? Number(opt.risk_adjusted_tco).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}" title="Inspect Cryptographic Section 13 Dispute Dossier">
                    🛡️ Dossier
                </button>
                <button type="button" class="control-btn btn-snipe-deal" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-price="${opt.risk_adjusted_tco || listing.price_inr || 1000}" style="padding: 6px 10px; font-size: 11px; background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.4); color: #38bdf8;" title="1-Click Escrow Snipe Deal Lock">
                    🎯 Snipe
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

    // Wire 1-Click Snipe Deal Lock
    grid.querySelectorAll('.btn-snipe-deal').forEach(b => {
        b.addEventListener('click', async () => {
            const id = b.getAttribute('data-order-id') || 'deal-001';
            const price = parseFloat(b.getAttribute('data-price')) || 1000.0;
            b.disabled = true;
            b.textContent = "Locking...";
            try {
                const res = await fetch('/api/snipe/lock', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        listing_id: id,
                        target_price: price,
                        preauth_payment_method: 'ONE_CLICK_ESCROW',
                        auto_execute_within_seconds: 600
                    })
                });
                if (res.ok) {
                    const lock = await res.json();
                    showToast(`🎯 Snipe Locked! Receipt: ${lock.receipt_hash.substring(0, 16)}...`, "success");
                    b.textContent = "🔒 Locked";
                    b.style.color = "#34d399";
                    b.style.borderColor = "#10b981";
                } else {
                    throw new Error("Lock service error");
                }
            } catch (err) {
                showToast("Failed to lock snipe: " + err.message, "error");
                b.disabled = false;
                b.textContent = "🎯 Snipe";
            }
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
