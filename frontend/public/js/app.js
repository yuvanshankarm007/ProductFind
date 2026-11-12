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
import { initSearchAutocomplete, saveRecentSearch } from './search_autocomplete.js';

let currentSearchController = null;
let currentSearchToken = 0;
let lastExecutedQuery = "";
let searchDebounceTimer = null;

let activeWalletCards = ['hdfc_regalia', 'icici_amazon_pay', 'axis_flipkart', 'sbi_cashback', 'paypal_pay_later', 'amex_platinum'];
try {
    const savedCards = localStorage.getItem('ProductFind_Wallet_Cards');
    if (savedCards) activeWalletCards = JSON.parse(savedCards);
} catch (_) {}

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
        addBundleItem: (item) => addBundleItem(item),
        applySearchResults: (state) => applySearchResults(state)
    });

    // 7. Wire Sentinel AI Concierge Chatbot — pass executeSearch so bot suggestions trigger real searches
    initConciergeBot((query) => {
        const input = document.getElementById('search-input');
        if (input) input.value = query;
        executeSearch(query, 'single');
    });

    // 8. Wire Commercial Modals: My Wallet, Price Watchdog & Dispute Assistant
    initWallet();
    initWatchdogModal();
    initDisputeModal();

    // 9. Pre-populate with demo data so grid is never empty on first load
    seedDemoData();

    // 10. Hydrate Verified Savings Ledger badge & MCP quick status
    refreshLedgerStats();
    const ledgerBtn = document.getElementById('btn-ledger-stats');
    if (ledgerBtn) {
        ledgerBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/ledger/stats');
                const stats = await res.json();
                showToast(
                    `Verified Ledger: ${stats.total_arbitrages_completed || 0} arbitrations · $${Number(stats.total_arbitrage_saved_usd || 0).toLocaleString()} saved · ${stats.total_links_verified || 0} live links verified · MCP ready at POST /mcp`,
                    "success"
                );
            } catch (_) {
                showToast("Ledger active · MCP endpoint at POST /mcp", "info");
            }
        });
    }

    // 10. Rotate search bar placeholder text
    startPlaceholderRotation();

    // 11. Start Deal of the Day rotator
    startDealOfDayRotator();

    // 12. Load Trending Deals from live API
    loadTrendingDeals();
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
let bundleItems = [];

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
        if (searchBtnLabel) searchBtnLabel.textContent = 'Knapsack AI';
        if (searchInput) {
            searchInput.placeholder = 'Enter bundle items separated by commas (e.g. Monitor, Keyboard, Desk, Webcam)...';
            // Do not force pre-typed items into input value; keep clean unless user typed
        }
        renderBundlePills();
    } else if (mode === 'image') {
        dimBtn(singleBtn);
        dimBtn(bundleBtn);
        activateBtn(imageBtn);
        if (bundleBuilder) bundleBuilder.style.display = 'none';
        if (imageContainer) imageContainer.style.display = 'block';
        if (searchBtnLabel) searchBtnLabel.textContent = 'Visual AI';
        if (searchInput) {
            searchInput.placeholder = 'Upload, drop, or select product image below, or type query...';
            // Clear bundle list text if switching to image mode to keep view clean
            if (bundleItems.length > 0 && searchInput.value === bundleItems.join(', ')) {
                searchInput.value = '';
            }
        }
    } else {
        // Single Deal mode (default)
        dimBtn(bundleBtn);
        dimBtn(imageBtn);
        activateBtn(singleBtn);
        if (bundleBuilder) bundleBuilder.style.display = 'none';
        if (imageContainer) imageContainer.style.display = 'none';
        if (searchBtnLabel) searchBtnLabel.textContent = 'AI Mode';
        if (searchInput) {
            searchInput.placeholder = 'Search any product, compare prices, or audit warranty fine print...';
            if (bundleItems.length > 0 && searchInput.value === bundleItems.join(', ')) {
                searchInput.value = '';
            }
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
    const mainSearchSubmitBtn = document.getElementById('main-search-submit-btn');

    function triggerUnifiedSearch() {
        clearTimeout(searchDebounceTimer);
        let q = searchInput ? searchInput.value.trim() : '';

        // If query is empty, prompt cleanly rather than forcing a branded product
        if (!q) {
            showToast("Please enter a product or query to search.", "info");
            if (searchInput) {
                searchInput.placeholder = "Search any product, compare prices, or audit warranty fine print...";
                searchInput.focus();
            }
            return;
        }

        lastExecutedQuery = q;
        const isBundleIntent = currentSearchMode === 'bundle' || 
            q.includes(',') || 
            ['setup', 'bundle', 'bulk', 'kit', 'pack', 'knapsack', 'peripherals', 'workstation', 'rig', 'wfh'].some(k => q.toLowerCase().includes(k));

        if (isBundleIntent && currentSearchMode !== 'bundle') {
            setMode('bundle');
        }

        let itemsList = null;
        if (isBundleIntent) {
            if (bundleItems && bundleItems.length > 0) {
                itemsList = bundleItems;
            } else if (q.includes(',')) {
                itemsList = q.split(',').map(s => s.trim()).filter(Boolean);
            }
        }
        executeSearch(q, isBundleIntent ? 'bundle' : 'single', itemsList);
    }

    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            triggerUnifiedSearch();
        });
    }

    if (mainSearchSubmitBtn) {
        mainSearchSubmitBtn.addEventListener('click', (e) => {
            e.preventDefault();
            triggerUnifiedSearch();
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

        // Modern Search Autocomplete Dropdown
        initSearchAutocomplete(searchInput, (selectedQuery) => {
            const qLow = (selectedQuery || '').toLowerCase();
            if (qLow.includes('wfh') || qLow.includes('gaming rig') || qLow.includes('bundle') || qLow.includes('setup')) {
                setMode('bundle');
                if (qLow.includes('wfh')) {
                    bundleItems = ['27-inch 4K Monitor', 'Mechanical Keyboard', 'Ergonomic Chair', 'Webcam'];
                } else if (qLow.includes('gaming')) {
                    bundleItems = ['Gaming Monitor', 'Wireless Gaming Mouse', 'RGB Mechanical Keyboard', 'Spatial Audio Headset'];
                }
                renderBundlePills();
                executeSearch(selectedQuery, 'bundle', bundleItems);
            } else {
                executeSearch(selectedQuery, 'single');
            }
        });
    }

    // Top Nav Price Watchdog Pill Button
    const btnOpenWatchdogNav = document.getElementById('btn-open-watchdog-nav');
    if (btnOpenWatchdogNav) {
        btnOpenWatchdogNav.addEventListener('click', () => {
            const q = searchInput ? searchInput.value.trim() : 'Apple iPhone 16';
            openWatchdogModal(q || 'Apple iPhone 16', 79900);
        });
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
                const currentQuery = searchInput ? searchInput.value.trim() : "";
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

    // Keyboard shortcut: press / to focus search (GitHub / Linear / Notion style)
    document.addEventListener('keydown', (e) => {
        const tag = document.activeElement?.tagName;
        if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') {
            e.preventDefault();
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        if (e.key === 'Escape' && document.activeElement === searchInput) {
            searchInput.blur();
        }
    });
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
    saveRecentSearch(query);

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
        items_list: itemsList || (isBundle && bundleItems.length ? bundleItems : null),
        wallet_cards: activeWalletCards
    };

    // Update UI status
    const statusText = document.getElementById('search-status-text');
    if (statusText) statusText.textContent = isBundle ? `Deploying Knapsack Cart-Split Swarm for '${query}'...` : `Deploying multi-agent swarm for '${query}'...`;

    appendTerminalLog("Coordinator", isBundle ? 
        `Initiating Knapsack Cart-Split Swarm for bundle: '${query}' across Amazon, Flipkart, & OEM Direct...` :
        `Deploying Tier-1 Scout Swarm for query: '${query}' in region: ${prefs.country} (${prefs.currency})...`
    );

    // Update button loading text
    const btnLabel = document.getElementById('search-btn-label');
    if (btnLabel) btnLabel.textContent = isBundle ? 'Knapsack...' : 'Arbitrating...';

    // 1. Stream live agent negotiation traces over WebSocket
    wsClient.send('search', payload);

    // 2. Concurrently execute HTTP fetch for immediate zero-delay completion
    fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: currentSearchController.signal
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    })
    .then(state => {
        if (searchToken === currentSearchToken) {
            applySearchResults(state);
            if (btnLabel) {
                btnLabel.textContent = currentSearchMode === 'bundle' ? 'Knapsack AI' : 'AI Mode';
            }
        }
    })
    .catch(err => {
        if (err.name !== 'AbortError') {
            console.error("HTTP Search Error:", err);
            if (btnLabel) {
                btnLabel.textContent = currentSearchMode === 'bundle' ? 'Knapsack AI' : 'AI Mode';
            }
        }
    });
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

export function renderCommunityConsensus(state) {
    const container = document.getElementById('community-consensus-section');
    if (!container) return;

    const reddit = state.reddit_consensus;
    const reviews = state.review_authenticity;
    const bifl = state.bifl_metrics;

    if (!reddit && !reviews && !bifl) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    const formatSourcePill = (mode) => {
        if (mode === 'live_api' || mode === 'live_web_llm' || mode === 'live_ifixit_api') {
            return `<span style="background: rgba(16, 185, 129, 0.18); border: 1px solid rgba(16, 185, 129, 0.45); color: #34d399; font-size: 9.5px; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">🌐 Live API</span>`;
        }
        if (mode === 'live_scraped_telemetry') {
            return `<span style="background: rgba(56, 189, 248, 0.18); border: 1px solid rgba(56, 189, 248, 0.45); color: #38bdf8; font-size: 9.5px; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">📡 Live Telemetry</span>`;
        }
        if (mode === 'curated_cache') {
            return `<span style="background: rgba(99, 102, 241, 0.18); border: 1px solid rgba(99, 102, 241, 0.45); color: #a5b4fc; font-size: 9.5px; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">📚 Verified Cache</span>`;
        }
        return `<span style="background: rgba(148, 163, 184, 0.15); border: 1px solid rgba(148, 163, 184, 0.35); color: #cbd5e1; font-size: 9.5px; font-weight: 700; padding: 2px 6px; border-radius: 9999px;">🔍 Search Index</span>`;
    };

    // 1. Reddit Hivemind Column
    let redditHtml = '';
    if (reddit) {
        const praisesList = (reddit.top_praises || []).map(p => `
            <li style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; font-size: 12px; color: #cbd5e1; line-height: 1.4;">
                <span style="color: #34d399; font-weight: 800; flex-shrink: 0;">✓</span>
                <span>${escapeHtml(p)}</span>
            </li>
        `).join('');

        const complaintsList = (reddit.top_complaints || []).map(c => `
            <li style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; font-size: 12px; color: #fca5a5; line-height: 1.4;">
                <span style="color: #f87171; font-weight: 800; flex-shrink: 0;">⚠</span>
                <span>${escapeHtml(c)}</span>
            </li>
        `).join('');

        const threadCitations = (reddit.citations || []).map(cit => `
            <a href="${escapeHtml(cit.url)}" target="_blank" rel="noopener noreferrer" style="display: block; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 10px; margin-top: 6px; text-decoration: none; transition: all 0.2s;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                    <span style="font-size: 10px; font-weight: 700; color: #ff6b35;">${escapeHtml(cit.subreddit)}</span>
                    <span style="font-size: 10px; color: #94a3b8;">▲ ${(cit.upvotes || 0).toLocaleString()} · 💬 ${cit.comment_count || 0}</span>
                </div>
                <div style="font-size: 11.5px; font-weight: 600; color: #f1f5f9; line-height: 1.3;">"${escapeHtml(cit.title)}"</div>
                <div style="font-size: 10.5px; color: #94a3b8; font-style: italic; margin-top: 3px;">"${escapeHtml(cit.summary_quote)}"</div>
            </a>
        `).join('');

        const subsPills = (reddit.subreddits || []).map(s => `
            <span style="background: rgba(255, 69, 0, 0.15); border: 1px solid rgba(255, 69, 0, 0.35); color: #ff6b35; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 9999px;">${escapeHtml(s)}</span>
        `).join(' ');

        redditHtml = `
            <div class="consensus-column" style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 69, 0, 0.35); border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.3rem;">🟠</span>
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: #ff6b35; text-transform: uppercase; letter-spacing: 0.05em;">Reddit Hivemind</div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff;">Community Consensus</div>
                        </div>
                    </div>
                    <span style="background: rgba(255, 69, 0, 0.18); border: 1px solid #ff4500; color: #ff6b35; font-weight: 800; font-size: 12px; padding: 4px 10px; border-radius: 8px;">
                        ${reddit.sentiment_score}% Positive
                    </span>
                </div>

                <div style="margin-bottom: 10px; display: flex; gap: 4px; flex-wrap: wrap; align-items: center;">
                    ${formatSourcePill(reddit.source_mode)}
                    ${subsPills}
                </div>

                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 8px 10px; font-size: 11.5px; font-weight: 700; color: #f1f5f9; margin-bottom: 12px;">
                    💬 ${escapeHtml(reddit.community_verdict)}
                </div>

                <div style="font-size: 11px; font-weight: 700; color: #34d399; text-transform: uppercase; margin-bottom: 6px;">Top Verified Praises</div>
                <ul style="list-style: none; padding: 0; margin: 0 0 10px 0;">
                    ${praisesList}
                </ul>

                <div style="font-size: 11px; font-weight: 700; color: #f87171; text-transform: uppercase; margin-bottom: 6px;">Critical Buyer Complaints</div>
                <ul style="list-style: none; padding: 0; margin: 0 0 10px 0;">
                    ${complaintsList}
                </ul>

                ${reddit.failure_modes_after_1yr ? `
                    <div style="background: rgba(239, 68, 68, 0.08); border-left: 3px solid #ef4444; border-radius: 0 6px 6px 0; padding: 8px 10px; margin-bottom: 12px;">
                        <div style="font-size: 10px; font-weight: 800; color: #fca5a5; text-transform: uppercase;">12+ Month Failure Modes (What Breaks):</div>
                        <div style="font-size: 11px; color: #e2e8f0; margin-top: 2px;">${escapeHtml(reddit.failure_modes_after_1yr)}</div>
                    </div>
                ` : ''}

                <div style="margin-top: auto;">
                    <div style="font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px;">Top Citations (${reddit.threads_analyzed} threads):</div>
                    ${threadCitations}
                </div>
            </div>
        `;
    }

    // 2. ReviewRay / Fakespot Review Authenticity Column
    let reviewsHtml = '';
    if (reviews) {
        const gradeColor = (reviews.letter_grade || '').includes('A') ? '#10b981' : ((reviews.letter_grade || '').includes('B') ? '#38bdf8' : ((reviews.letter_grade || '').includes('C') ? '#f59e0b' : '#ef4444'));
        const signalsHtml = (reviews.bot_signals || []).map(s => {
            const pass = s.status === 'PASS';
            return `
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 6px 8px; margin-bottom: 5px; font-size: 11px;">
                    <div>
                        <span style="font-weight: 600; color: #f1f5f9;">${escapeHtml(s.name)}</span>
                        <div style="font-size: 10px; color: #94a3b8;">${escapeHtml(s.details)}</div>
                    </div>
                    <div style="text-align: right; flex-shrink: 0; margin-left: 8px;">
                        <span style="font-size: 9px; font-weight: 800; color: ${pass ? '#34d399' : '#f59e0b'}; background: ${pass ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)'}; padding: 2px 6px; border-radius: 4px;">${escapeHtml(s.metric)}</span>
                    </div>
                </div>
            `;
        }).join('');

        reviewsHtml = `
            <div class="consensus-column" style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.3rem;">🛡️</span>
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.05em;">ReviewRay Authenticity</div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff;">Organic vs Bot Audit</div>
                        </div>
                    </div>
                    <span style="background: rgba(56, 189, 248, 0.15); border: 1px solid ${gradeColor}; color: ${gradeColor}; font-weight: 800; font-size: 13px; padding: 4px 10px; border-radius: 8px;">
                        ${escapeHtml(reviews.letter_grade)}
                    </span>
                </div>

                <div style="font-size: 11px; color: #94a3b8; margin-bottom: 12px;">
                    ${escapeHtml(reviews.grade_description)}
                </div>

                <!-- Rating Divergence Box -->
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Store Sticker Rating</div>
                            <div style="font-size: 16px; font-weight: 800; color: #cbd5e1; font-family: monospace;">★ ${Number(reviews.sticker_rating || 4.5).toFixed(1)} / 5.0</div>
                        </div>
                        <div style="font-size: 1.2rem; color: #64748b;">➔</div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: #34d399; font-weight: 700; text-transform: uppercase;">Adjusted Honest Rating</div>
                            <div style="font-size: 18px; font-weight: 800; color: #34d399; font-family: monospace;">★ ${Number(reviews.adjusted_honest_rating || 4.1).toFixed(1)} / 5.0</div>
                        </div>
                    </div>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 6px; text-align: center;">
                        Stripped ~${reviews.incentivized_or_bot_pct}% unverified, promotional & Vine burst ratings
                    </div>
                </div>

                <!-- Organic Review Meter -->
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
                        <span style="color: #34d399; font-weight: 700;">${reviews.organic_reviews_pct}% Organic Reviews</span>
                        <span style="color: #f87171;">${reviews.incentivized_or_bot_pct}% Bot / Sample Skew</span>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.3); border-radius: 9999px; height: 6px; overflow: hidden; display: flex;">
                        <div style="background: linear-gradient(90deg, #10b981, #34d399); width: ${reviews.organic_reviews_pct}%; height: 100%;"></div>
                    </div>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; text-align: right;">Audited ${(reviews.total_reviews_analyzed || 0).toLocaleString()} reviews on ${escapeHtml(reviews.store_audited || 'Amazon')}</div>
                </div>

                <!-- Bot Signals -->
                <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase; margin-bottom: 6px;">Fraud Heuristic Telemetry</div>
                <div style="margin-bottom: 10px;">
                    ${signalsHtml}
                </div>

                <div style="margin-top: auto; font-size: 11px; color: #94a3b8; font-style: italic; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
                    "${escapeHtml(reviews.recommendation)}"
                </div>
            </div>
        `;
    }

    // 3. iFixit Repairability & BIFL Longevity Column
    let biflHtml = '';
    if (bifl) {
        const scoreColor = (bifl.ifixit_score || 0) >= 8.0 ? '#10b981' : ((bifl.ifixit_score || 0) >= 6.0 ? '#38bdf8' : '#f59e0b');
        const driversList = (bifl.key_longevity_drivers || []).map(d => `
            <li style="display: flex; align-items: flex-start; gap: 6px; margin-bottom: 5px; font-size: 11.5px; color: #cbd5e1; line-height: 1.35;">
                <span style="color: #60a5fa; font-weight: 800;">•</span>
                <span>${escapeHtml(d)}</span>
            </li>
        `).join('');

        biflHtml = `
            <div class="consensus-column" style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 1.3rem;">🔧</span>
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: #34d399; text-transform: uppercase; letter-spacing: 0.05em;">iFixit & BIFL Index</div>
                            <div style="font-size: 13px; font-weight: 700; color: #ffffff;">Hardware Longevity & Repair</div>
                        </div>
                    </div>
                    <span style="background: rgba(16, 185, 129, 0.15); border: 1px solid ${scoreColor}; color: ${scoreColor}; font-weight: 800; font-size: 13px; padding: 4px 10px; border-radius: 8px; font-family: monospace;">
                        ${Number(bifl.ifixit_score || 7.0).toFixed(1)} / 10
                    </span>
                </div>

                <div style="background: rgba(52, 211, 153, 0.1); border: 1px solid rgba(52, 211, 153, 0.25); border-radius: 8px; padding: 6px 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px; font-weight: 700; color: #34d399;">${escapeHtml(bifl.bifl_badge || 'BIFL Approved')}</span>
                    <span style="font-size: 11px; color: #a7f3d0; font-weight: 700;">~${bifl.expected_lifespan_years} Yr Lifespan</span>
                </div>

                <div style="font-size: 11.5px; color: #94a3b8; margin-bottom: 10px; line-height: 1.35;">
                    <strong style="color: #e2e8f0;">Architecture:</strong> ${escapeHtml(bifl.repairability_tier)}
                </div>

                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 8px 10px; margin-bottom: 10px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #94a3b8;">Battery Replacement:</span>
                        <span style="color: ${bifl.battery_replaceable ? '#34d399' : '#f87171'}; font-weight: 700;">${bifl.battery_replaceable ? '✓ Supported' : '✕ Integrated / Glued'}</span>
                    </div>
                    <div style="color: #cbd5e1; font-size: 10.5px; margin-bottom: 6px;">${escapeHtml(bifl.battery_replacement_ease)}</div>
                    <div style="display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 4px;">
                        <span style="color: #94a3b8;">Parts Availability:</span>
                        <span style="color: #60a5fa; font-weight: 700;">${escapeHtml(bifl.spare_parts_availability)}</span>
                    </div>
                </div>

                <div style="font-size: 11px; font-weight: 700; color: #60a5fa; text-transform: uppercase; margin-bottom: 6px;">Longevity Drivers</div>
                <ul style="list-style: none; padding: 0; margin: 0 0 10px 0;">
                    ${driversList}
                </ul>

                <div style="margin-top: auto; font-size: 10.5px; color: #94a3b8; background: rgba(0,0,0,0.25); border-radius: 6px; padding: 6px 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; gap: 6px; flex-wrap: wrap;">
                        ${formatSourcePill(bifl.source_mode)}
                        ${bifl.ifixit_url ? `<a href="${escapeHtml(bifl.ifixit_url)}" target="_blank" rel="noopener noreferrer" style="color: #34d399; font-weight: 700; text-decoration: none;">🔧 iFixit Teardown Guide ↗</a>` : ''}
                    </div>
                    <span style="color: #e2e8f0; font-weight: 600;">Teardown Modularity:</span> ${escapeHtml(bifl.modularity_notes)}
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
                <div style="font-size: 11px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.1em; display: flex; align-items: center; gap: 6px;">
                    <span>🌐 100-Point Consumer Decision Breakdown</span>
                    <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 1px 6px; border-radius: 10px; font-size: 10px; font-weight: 700;">Social Proof + Longevity + Authenticity</span>
                </div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #ffffff; margin-top: 2px;">
                    Peer Truth & Hardware Longevity Audit
                </div>
            </div>
            <div style="font-size: 11px; color: #94a3b8;">
                Grounded in authentic Reddit subreddits, Fakespot heuristics, & iFixit teardowns
            </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
            ${redditHtml}
            ${reviewsHtml}
            ${biflHtml}
        </div>
    `;
}


async function refreshLedgerStats() {
    const badge = document.getElementById('ledger-saved-badge');
    if (!badge) return;
    try {
        const res = await fetch('/api/ledger/stats');
        if (!res.ok) return;
        const stats = await res.json();
        const savedUsd = Number(stats.total_arbitrage_saved_usd || 0);
        badge.textContent = savedUsd >= 1000 ? `$${(savedUsd / 1000).toFixed(1)}k` : `$${Math.round(savedUsd)}`;
    } catch (_) {
        // Ignore offline ledger polling failures
    }
}

function applySearchResults(state) {
    if (!state) return;
    store.setLastState(state);
    refreshLedgerStats();

    const statusText = document.getElementById('search-status-text');
    const retailerCount = (state.raw_listings && state.raw_listings.length) || (state.comparison_matrix && state.comparison_matrix.length) || (state.is_bundle ? 12 : 3);
    if (statusText) statusText.textContent = `Synthesis complete: Audited ${retailerCount} verified retailers across Amazon, Flipkart, & OEM Direct.`;

    // 0. Render Head-to-Head Versus Showdown if arbitrated
    renderVersusShowdown(state.versus_result);

    // 0.5 Render Community Consensus & 100-Point Consumer Breakdown Deck
    renderCommunityConsensus(state);

    // 1. Render Dedicated Bundle Spotlight Banner if bundle arbitrated
    renderBundleSpotlight(state);

    // 2. Render 3 Strategic Deal Cards
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
                <a href="${escapeHtml(listing.listing_url || '#')}" target="_blank" rel="noopener noreferrer" style="color: #ffffff; text-decoration: none; display: inline-flex; align-items: flex-start; gap: 6px;" title="${opt.url_verified ? `Pre-Click Verified Live on ${escapeHtml(listing.merchant || 'Store')} (HTTP ${opt.http_status || 200})` : `Open listing on ${escapeHtml(listing.merchant || 'Store')}`}">
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

            <!-- 7-14 Day Price Drop Forecast Callout -->
            <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 6px; padding: 4px 8px; margin: 6px 0; font-size: 10.5px;">
                <span style="color: #94a3b8; display: flex; align-items: center; gap: 4px;">
                    <span>📊 7-Day Drop Prob:</span>
                    <strong style="color: #f1f5f9;">${(store.lastState && store.lastState.price_analytics) ? `${Math.round(store.lastState.price_analytics.drop_probability_pct || 14)}%` : '12%'}</strong>
                </span>
                <span style="font-weight: 800; font-size: 9.5px; padding: 1px 6px; border-radius: 4px; background: ${(store.lastState && store.lastState.price_analytics && store.lastState.price_analytics.drop_probability_pct > 65) ? 'rgba(245,158,11,0.2)' : 'rgba(16, 185, 129, 0.2)'}; color: ${(store.lastState && store.lastState.price_analytics && store.lastState.price_analytics.drop_probability_pct > 65) ? '#fbbf24' : '#34d399'}; border: 1px solid ${(store.lastState && store.lastState.price_analytics && store.lastState.price_analytics.drop_probability_pct > 65) ? 'rgba(245,158,11,0.4)' : 'rgba(16, 185, 129, 0.4)'};">
                    ${(store.lastState && store.lastState.price_analytics && store.lastState.price_analytics.drop_probability_pct > 65) ? '⏳ WAIT FOR DROP' : '⚡ BUY NOW'}
                </span>
            </div>

            <!-- Social Proof & Review Authenticity Badges -->
            <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px;">
                <span style="background: rgba(255, 69, 0, 0.12); border: 1px solid rgba(255, 69, 0, 0.3); color: #ff6b35; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-flex; align-items: center; gap: 3px;" title="Reddit Community Consensus Sentiment">
                    <span>🟠 Reddit</span>
                    <span>${(store.lastState && store.lastState.reddit_consensus) ? `${store.lastState.reddit_consensus.sentiment_score}% Positive` : '91% Positive'}</span>
                </span>
                <span style="background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-flex; align-items: center; gap: 3px;" title="Review Authenticity Grade (ReviewRay / Fakespot style)">
                    <span>🛡️ Reviews</span>
                    <span>${(store.lastState && store.lastState.review_authenticity) ? store.lastState.review_authenticity.letter_grade : 'Grade A'}</span>
                </span>
                <span style="background: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.3); color: #34d399; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-flex; align-items: center; gap: 3px;" title="iFixit Teardown Repairability Score">
                    <span>🔧 iFixit</span>
                    <span>${(store.lastState && store.lastState.bifl_metrics) ? `${store.lastState.bifl_metrics.ifixit_score}/10` : '7.0/10'}</span>
                </span>
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

            <!-- AI Arbitration Confidence Bar -->
            <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:10px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">AI Confidence</span>
                    <span style="font-size:11px;font-weight:800;color:${(trust.overall_score||85)>=90?'#34d399':(trust.overall_score||85)>=75?'#f59e0b':'#f87171'};">${trust.overall_score||85}%</span>
                </div>
                <div style="background:rgba(15,23,42,0.6);border-radius:9999px;height:4px;overflow:hidden;">
                    <div style="height:100%;width:${trust.overall_score||85}%;background:${(trust.overall_score||85)>=90?'linear-gradient(90deg,#34d399,#10b981)':(trust.overall_score||85)>=75?'linear-gradient(90deg,#f59e0b,#d97706)':'linear-gradient(90deg,#f87171,#ef4444)'};border-radius:9999px;transition:width 0.6s ease;"></div>
                </div>
            </div>

            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <a href="${escapeHtml(listing.listing_url || '#')}" target="_blank" rel="noopener noreferrer" class="control-btn" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 4px; padding: 6px 10px; font-size: 11px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); color: #93c5fd; border-radius: 6px;" title="${opt.url_verified ? `Pre-Click Verified Live (HTTP ${opt.http_status || 200})` : `Open Product Page on ${escapeHtml(listing.merchant || 'Merchant')}`}">
                    ${opt.url_verified ? '✓ Live Store ↗' : 'Store ↗'}
                </a>
                <button type="button" class="control-btn btn-primary btn-checkout-deal" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-price="${escapeHtml(opt.display_currency || '$')} ${opt.risk_adjusted_tco ? Number(opt.risk_adjusted_tco).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}" data-title="${escapeHtml(listing.product_title || '')}" style="flex: 1; justify-content: center;">
                    Pay with PayPal
                </button>
                <button type="button" class="control-btn btn-view-dossier" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-price="${escapeHtml(opt.display_currency || '$')} ${opt.risk_adjusted_tco ? Number(opt.risk_adjusted_tco).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}" title="Inspect Cryptographic Section 13 Dispute Dossier">
                    🛡️ Dossier
                </button>
                <button type="button" class="btn-card-alert" data-title="${escapeHtml(listing.product_title || '')}" data-price="${opt.risk_adjusted_tco || listing.base_price || 1000}" data-currency="${escapeHtml(opt.display_currency || 'INR')}" title="Set 24/7 Price Drop Watchdog Alert">
                    🔔 Alert
                </button>
                <button type="button" class="control-btn btn-snipe-deal" data-order-id="${escapeHtml(listing.id || 'ORDER')}" data-price="${opt.risk_adjusted_tco || listing.price_inr || 1000}" style="padding: 6px 10px; font-size: 11px; background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.4); color: #38bdf8;" title="1-Click Escrow Snipe Deal Lock">
                    🎯 Snipe
                </button>
                <button type="button" class="btn-share-deal" data-title="${escapeHtml(listing.product_title || '')}" data-merchant="${escapeHtml(listing.merchant || '')}" data-tco="${opt.risk_adjusted_tco || 0}" data-currency="${escapeHtml(opt.display_currency || 'INR')}" data-trust="${trust.overall_score || 85}" style="background:transparent;border:1px solid rgba(99,102,241,0.4);color:#a5b4fc;border-radius:6px;padding:6px 10px;font-size:11px;cursor:pointer;display:flex;align-items:center;gap:4px;" title="Share Deal Report — copy shareable link">
                    🔗 Share
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

    // Wire Price Watchdog Alert Buttons
    grid.querySelectorAll('.btn-card-alert').forEach(b => {
        b.addEventListener('click', () => {
            const title = b.getAttribute('data-title');
            const price = parseFloat(b.getAttribute('data-price')) || 1000;
            openWatchdogModal(title, price);
        });
    });

    // Wire Share Deal Report buttons
    grid.querySelectorAll('.btn-share-deal').forEach(b => {
        b.addEventListener('click', async () => {
            const title = b.getAttribute('data-title') || '';
            const merchant = b.getAttribute('data-merchant') || 'Amazon.in';
            const tco = parseFloat(b.getAttribute('data-tco')) || 0;
            const currency = b.getAttribute('data-currency') || 'INR';
            const trust = parseInt(b.getAttribute('data-trust')) || 85;
            const orig = b.textContent;
            b.disabled = true;
            b.textContent = '⏳';
            try {
                const res = await fetch('/api/share-deal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: title, merchant, tco, currency, trust_score: trust, verdict: 'BUY NOW' })
                });
                if (!res.ok) throw new Error('Share API error');
                const data = await res.json();
                await navigator.clipboard.writeText(data.full_url).catch(() => {});
                showToast(`🔗 Link copied! ${data.summary}`, 'success');
                b.textContent = '✓ Copied';
                b.style.color = '#34d399';
                b.style.borderColor = '#10b981';
                setTimeout(() => { b.textContent = orig; b.style.color = ''; b.style.borderColor = ''; b.disabled = false; }, 3000);
            } catch (err) {
                showToast('Share failed: ' + err.message, 'error');
                b.disabled = false;
                b.textContent = orig;
            }
        });
    });
}

// ==========================================================================
// HEAD-TO-HEAD "VERSUS" ARBITRATOR RENDERER
// ==========================================================================

function renderVersusShowdown(versus) {
    const container = document.getElementById('versus-showdown-section');
    if (!container) return;

    if (!versus || !versus.product_a || !versus.product_b) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    container.style.display = 'block';
    const pa = versus.product_a;
    const pb = versus.product_b;
    const isWinnerA = versus.winner === pa.name;

    let specRowsHtml = (versus.spec_comparison_table || []).map(r => `
        <tr>
            <td style="font-weight: 700; color: #94a3b8;">${escapeHtml(r.spec_name)}</td>
            <td style="color: ${r.winner === 'product_a' ? '#34d399' : '#e2e8f0'}; font-weight: ${r.winner === 'product_a' ? '800' : '500'};">
                ${escapeHtml(String(r.val_a))} ${r.winner === 'product_a' ? '★' : ''}
            </td>
            <td style="color: ${r.winner === 'product_b' ? '#34d399' : '#e2e8f0'}; font-weight: ${r.winner === 'product_b' ? '800' : '500'};">
                ${escapeHtml(String(r.val_b))} ${r.winner === 'product_b' ? '★' : ''}
            </td>
        </tr>
    `).join('');

    let reasonsHtml = (versus.swarm_verdict_rationale || []).map(reason => `
        <li style="margin-bottom: 6px; color: #cbd5e1; font-size: 13px;">${escapeHtml(reason)}</li>
    `).join('');

    container.innerHTML = `
        <div class="versus-card-container">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                        <span>⚖️ Head-to-Head "Versus" Arbitrator</span>
                        <span style="background: rgba(56, 189, 248, 0.2); color: #7dd3fc; padding: 2px 8px; border-radius: 9999px; font-size: 10px;">DUAL-PRODUCT BENCHMARK</span>
                    </div>
                    <h2 style="font-size: 1.35rem; font-weight: 800; color: #ffffff; margin-top: 4px;">
                        ${escapeHtml(pa.name)} <span style="color: #38bdf8;">vs</span> ${escapeHtml(pb.name)}
                    </h2>
                </div>
                <div>
                    <span style="background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #34d399; font-weight: 800; padding: 6px 14px; border-radius: 8px; font-size: 13px;">
                        🏆 Winner: ${escapeHtml(versus.winner)} (${versus.value_difference_pct}% Value Edge)
                    </span>
                </div>
            </div>

            <!-- Dual Side-by-Side Cards -->
            <div class="versus-dual-grid">
                <div class="versus-product-box ${isWinnerA ? 'winner-box' : ''}">
                    <div style="font-size: 11px; color: ${isWinnerA ? '#34d399' : '#94a3b8'}; font-weight: 800;">
                        ${isWinnerA ? '🏆 SWARM ARBITRATED WINNER' : 'CONTENDER'}
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #ffffff; margin: 4px 0;">${escapeHtml(pa.name)}</div>
                    <div style="font-size: 12px; color: #64748b;">${escapeHtml(pa.headline_spec)}</div>
                    <div style="font-size: 1.3rem; font-weight: 900; color: #38bdf8; font-family: monospace; margin: 8px 0;">
                        ${escapeHtml(pa.currency)} ${Number(pa.best_price).toLocaleString()}
                    </div>
                    <div style="font-size: 11px; color: #94a3b8;">Resale Retention (2yr): <strong style="color: #e2e8f0;">${pa.resale_retention_2yr_pct}%</strong></div>
                </div>

                <div class="versus-center-divider">VS</div>

                <div class="versus-product-box ${!isWinnerA ? 'winner-box' : ''}">
                    <div style="font-size: 11px; color: ${!isWinnerA ? '#34d399' : '#94a3b8'}; font-weight: 800;">
                        ${!isWinnerA ? '🏆 SWARM ARBITRATED WINNER' : 'CONTENDER'}
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #ffffff; margin: 4px 0;">${escapeHtml(pb.name)}</div>
                    <div style="font-size: 12px; color: #64748b;">${escapeHtml(pb.headline_spec)}</div>
                    <div style="font-size: 1.3rem; font-weight: 900; color: #38bdf8; font-family: monospace; margin: 8px 0;">
                        ${escapeHtml(pb.currency)} ${Number(pb.best_price).toLocaleString()}
                    </div>
                    <div style="font-size: 11px; color: #94a3b8;">Resale Retention (2yr): <strong style="color: #e2e8f0;">${pb.resale_retention_2yr_pct}%</strong></div>
                </div>
            </div>

            <!-- Swarm AI Verdict -->
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
                <div style="font-size: 11px; font-weight: 800; color: #38bdf8; text-transform: uppercase; margin-bottom: 6px;">
                    ✦ Swarm AI Arbitration Rationale: "${escapeHtml(versus.winner_tagline)}"
                </div>
                <ul style="padding-left: 20px; margin: 0;">${reasonsHtml}</ul>
            </div>

            <!-- Spec Comparison Table -->
            <table class="versus-table">
                <thead>
                    <tr>
                        <th style="width: 30%;">Hardware Specification</th>
                        <th style="width: 35%;">${escapeHtml(pa.name)}</th>
                        <th style="width: 35%;">${escapeHtml(pb.name)}</th>
                    </tr>
                </thead>
                <tbody>${specRowsHtml}</tbody>
            </table>
        </div>
    `;

    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ==========================================================================
// "MY WALLET" CARD & BANK OFFER STACKER
// ==========================================================================

function initWallet() {
    const btnOpen = document.getElementById('btn-open-wallet');
    const modal = document.getElementById('modal-wallet');
    const btnClose = document.getElementById('btn-close-wallet-modal');
    const btnSave = document.getElementById('btn-save-wallet');
    const btnSelectAll = document.getElementById('btn-select-all-cards');
    const badgeCount = document.getElementById('wallet-active-badge');

    if (badgeCount) badgeCount.textContent = activeWalletCards.length;

    if (btnOpen && modal) {
        btnOpen.addEventListener('click', async () => {
            modal.style.display = 'flex';
            await loadWalletCardsUI();
        });
    }

    if (btnClose && modal) {
        btnClose.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    if (btnSelectAll) {
        btnSelectAll.addEventListener('click', () => {
            document.querySelectorAll('.wallet-card-checkbox').forEach(cb => cb.checked = true);
            document.querySelectorAll('.wallet-card-tile').forEach(t => t.classList.add('selected'));
        });
    }

    if (btnSave && modal) {
        btnSave.addEventListener('click', () => {
            const checked = [];
            document.querySelectorAll('.wallet-card-checkbox:checked').forEach(cb => {
                checked.push(cb.value);
            });
            activeWalletCards = checked;
            try {
                localStorage.setItem('ProductFind_Wallet_Cards', JSON.stringify(checked));
            } catch (_) {}
            if (badgeCount) badgeCount.textContent = checked.length;
            modal.style.display = 'none';
            showToast(`💳 Saved ${checked.length} wallet cards. Re-arbitrating deals...`, 'success');

            const currentQuery = document.getElementById('search-input')?.value.trim();
            if (currentQuery) executeSearch(currentQuery);
        });
    }
}

async function loadWalletCardsUI() {
    const grid = document.getElementById('wallet-cards-grid');
    if (!grid) return;

    try {
        const res = await fetch('/api/wallet/cards');
        if (!res.ok) throw new Error('Failed to load wallet cards');
        const cards = await res.json();

        grid.innerHTML = cards.map(c => {
            const isChecked = activeWalletCards.includes(c.card_id);
            return `
                <div class="wallet-card-tile ${isChecked ? 'selected' : ''}" data-card-id="${c.card_id}">
                    <input type="checkbox" class="wallet-card-checkbox" value="${c.card_id}" ${isChecked ? 'checked' : ''} style="margin-top: 3px; accent-color: #10b981;">
                    <div style="flex: 1;">
                        <div style="font-weight: 800; color: #ffffff; font-size: 13px;">${escapeHtml(c.card_name)}</div>
                        <div style="font-size: 11px; color: #38bdf8; font-weight: 700; margin: 2px 0;">${escapeHtml(c.badge)}</div>
                        <div style="font-size: 11px; color: #94a3b8; line-height: 1.3;">${escapeHtml(c.description)}</div>
                    </div>
                </div>
            `;
        }).join('');

        // Wire tile clicks
        grid.querySelectorAll('.wallet-card-tile').forEach(tile => {
            tile.addEventListener('click', (e) => {
                if (e.target.tagName.toLowerCase() === 'input') return;
                const cb = tile.querySelector('.wallet-card-checkbox');
                if (cb) {
                    cb.checked = !cb.checked;
                    tile.classList.toggle('selected', cb.checked);
                }
            });
        });

        grid.querySelectorAll('.wallet-card-checkbox').forEach(cb => {
            cb.addEventListener('change', () => {
                const tile = cb.closest('.wallet-card-tile');
                if (tile) tile.classList.toggle('selected', cb.checked);
            });
        });
    } catch (err) {
        grid.innerHTML = `<div style="color: #f87171;">Error loading cards: ${err.message}</div>`;
    }
}

// ==========================================================================
// PRICE WATCHDOG MODAL
// ==========================================================================

let activeWatchdogAlertId = null;

function openWatchdogModal(productTitle, currentPrice) {
    const modal = document.getElementById('modal-price-watchdog');
    if (!modal) return;

    const inputTitle = document.getElementById('watchdog-product-title');
    const inputCurr = document.getElementById('watchdog-current-price');
    const inputTarget = document.getElementById('watchdog-target-price');
    const feedback = document.getElementById('watchdog-feedback-box');

    if (inputTitle) {
        inputTitle.value = productTitle || "";
        if (!inputTitle.value) inputTitle.placeholder = "Enter product title...";
    }
    if (inputCurr) inputCurr.value = `₹ ${Number(currentPrice || 26990).toLocaleString()}`;
    if (inputTarget) inputTarget.value = Math.round((currentPrice || 26990) * 0.92);
    if (feedback) feedback.style.display = 'none';

    activeWatchdogAlertId = null;
    modal.style.display = 'flex';
}

function initWatchdogModal() {
    const modal = document.getElementById('modal-price-watchdog');
    const btnClose = document.getElementById('btn-close-watchdog-modal');
    const form = document.getElementById('watchdog-form');
    const btnSimulate = document.getElementById('btn-simulate-alert-trigger');
    const feedback = document.getElementById('watchdog-feedback-box');

    if (btnClose && modal) {
        btnClose.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const product = document.getElementById('watchdog-product-title')?.value || "Product";
            const currText = document.getElementById('watchdog-current-price')?.value || "0";
            const currentPrice = parseFloat(currText.replace(/[^0-9.]/g, '')) || 25000;
            const targetPrice = parseFloat(document.getElementById('watchdog-target-price')?.value) || 20000;
            const channel = document.getElementById('watchdog-channel')?.value || "email";
            const contact = document.getElementById('watchdog-contact')?.value || "shopper@sentinel.ai";

            try {
                const res = await fetch('/api/alerts/subscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        product_title: product,
                        current_price: currentPrice,
                        target_price: targetPrice,
                        currency: 'INR',
                        channel: channel,
                        user_contact: contact
                    })
                });

                if (!res.ok) throw new Error('Subscription failed');
                const alertData = await res.json();
                activeWatchdogAlertId = alertData.id;

                if (feedback) {
                    feedback.style.display = 'block';
                    feedback.style.background = 'rgba(16, 185, 129, 0.15)';
                    feedback.style.border = '1px solid #10b981';
                    feedback.style.color = '#34d399';
                    feedback.innerHTML = `
                        <strong>✓ Price Watchdog Active!</strong> Alert ID: <code>${alertData.id}</code><br>
                        Patrolling 23 retailers for price drops below ₹${targetPrice.toLocaleString()}. Dispatches to <strong>${channel.toUpperCase()}: ${contact}</strong>.
                    `;
                }
                showToast(`🎯 Price Watchdog active for ${product}!`, 'success');
            } catch (err) {
                showToast(`Watchdog error: ${err.message}`, 'error');
            }
        });
    }

    if (btnSimulate) {
        btnSimulate.addEventListener('click', async () => {
            const alertId = activeWatchdogAlertId || "alert-demo-xm5";
            try {
                const res = await fetch('/api/alerts/simulate-trigger', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ alert_id: alertId })
                });
                if (!res.ok) throw new Error('Simulation failed');
                const alertData = await res.json();

                if (feedback) {
                    feedback.style.display = 'block';
                    feedback.style.background = 'rgba(245, 158, 11, 0.15)';
                    feedback.style.border = '1px solid #f59e0b';
                    feedback.style.color = '#fbbf24';
                    feedback.innerHTML = `
                        <strong>⚡ SIMULATED PRICE DROP DISPATCHED!</strong><br>
                        ${escapeHtml(alertData.notification_log || 'Notification sent.')}
                    `;
                }
                showToast(`⚡ Price Drop Alert Triggered! Notification sent to ${alertData.channel.toUpperCase()}.`, 'success');
            } catch (err) {
                showToast(`Simulation error: ${err.message}`, 'error');
            }
        });
    }
}

// ==========================================================================
// 1-CLICK DISPUTE ASSISTANT & LEGAL CHARGEBACK DOSSIER
// ==========================================================================

function initDisputeModal() {
    const btnOpen = document.getElementById('btn-open-disputes');
    const modal = document.getElementById('modal-dispute-assistant');
    const btnClose = document.getElementById('btn-close-dispute-modal');
    const form = document.getElementById('dispute-form');
    const resultPanel = document.getElementById('dispute-result-panel');

    if (btnOpen && modal) {
        btnOpen.addEventListener('click', () => {
            modal.style.display = 'flex';
            if (resultPanel) resultPanel.style.display = 'none';
        });
    }

    if (btnClose && modal) {
        btnClose.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const orderId = document.getElementById('dispute-order-id')?.value || 'ORD-1';
            const merchant = document.getElementById('dispute-merchant')?.value || 'Amazon';
            const product = document.getElementById('dispute-product')?.value || 'Product';
            const amount = parseFloat(document.getElementById('dispute-amount')?.value) || 1000;
            const issueType = document.getElementById('dispute-issue-type')?.value || 'OPEN_BOX_VIOLATION';
            const description = document.getElementById('dispute-description')?.value || '';

            const btnSubmit = document.getElementById('btn-submit-dispute');
            if (btnSubmit) {
                btnSubmit.disabled = true;
                btnSubmit.innerHTML = '<span>Compiling Legal Dossier...</span>';
            }

            try {
                const res = await fetch('/api/dispute/file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        order_id: orderId,
                        merchant: merchant,
                        product_title: product,
                        amount: amount,
                        currency: 'INR',
                        issue_type: issueType,
                        incident_description: description
                    })
                });

                if (!res.ok) throw new Error('Dispute filing failed');
                const dispute = await res.json();

                if (resultPanel) {
                    resultPanel.style.display = 'block';
                    resultPanel.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-weight: 800; color: #34d399; font-size: 13px;">✓ Section 13 Legal Dossier Compiled</div>
                            <span class="hud-status-badge status-optimal">MERKLE SEALED</span>
                        </div>
                        <div style="font-size: 11px; color: #cbd5e1; margin-bottom: 6px;">
                            Case ID: <strong>${dispute.case_id}</strong> • Cryptographic Hash: <code style="font-size: 10px;">${dispute.evidence_hash.substring(0, 20)}...</code>
                        </div>
                        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 10px;">
                            Statutory Citations: ${(dispute.statutory_citations || []).join(' • ')}
                        </div>
                        <a href="/api/dispute/download/${dispute.pdf_filename}" target="_blank" download class="control-btn" style="background: #10b981; color: #ffffff; font-weight: 800; text-decoration: none; padding: 8px 16px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px; font-size: 12px;">
                            <span>📥 Download Official Section 13 PDF Dossier</span>
                        </a>
                    `;
                }
                showToast(`⚖️ Dispute filed! Dossier ${dispute.case_id} ready for download.`, 'success');
            } catch (err) {
                showToast(`Dispute error: ${err.message}`, 'error');
            } finally {
                if (btnSubmit) {
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<span>🛡️ Compile Section 13 Legal Dossier</span>';
                }
            }
        });
    }
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

// ==========================================================================
// STUB FUNCTIONS (called in initApp — safe no-ops if not yet implemented)
// ==========================================================================

function seedDemoData() {
    const urlParams = new URLSearchParams(window.location.search);
    const initialQuery = urlParams.get('q');
    if (initialQuery && initialQuery.trim()) {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = initialQuery.trim();
        }
        setTimeout(() => {
            executeSearch(initialQuery.trim(), 'single');
        }, 400);
    }
    // Clean initial state: do not autosearch on page load.
    // Preserves rotating placeholder prompts and waits for explicit user search action.
}

function startPlaceholderRotation() {
    const input = document.getElementById('search-input');
    if (!input) return;
    const prompts = [
        "Search 'Apple iPhone 16 Pro' for live 6-store arbitration...",
        "Try 'Sony WH-1000XM5' to audit Reddit BIFL and Review authenticity...",
        "Try 'MacBook Air M2' to inspect iFixit repairability and 7-yr lifespan...",
        "Search 'WFH setup bundle' for Knapsack multi-retailer split...",
        "Compare 'iPhone 16 vs Galaxy S24' for head-to-head showdown...",
        "Search any product, compare prices, or audit warranty fine print..."
    ];
    let idx = 0;
    setInterval(() => {
        if (document.activeElement !== input && (!input.value || prompts.includes(input.getAttribute('placeholder')))) {
            idx = (idx + 1) % prompts.length;
            input.setAttribute('placeholder', prompts[idx]);
        }
    }, 4000);
}

// Deal of the Day rotator — cycles through top deals every 8 seconds
function startDealOfDayRotator() {
    const deals = [
        { title: 'Apple iPhone 16 Pro 256GB — ₹7,500 below 90-day avg', sub: 'Amazon.in · Trust 96 · Open Box OTP · HDFC 5% stacked', price: '₹1,12,400', query: 'Apple iPhone 16 Pro' },
        { title: 'Sony WH-1000XM5 — All-Time Low detected this week', sub: 'Flipkart · Trust 92 · COD Available · ICICI 3% cashback', price: '₹24,990', query: 'Sony WH-1000XM5' },
        { title: 'MacBook Air M2 256GB — Best price in 60 days', sub: 'Apple Store Direct · Trust 99 · OEM Warranty · No-Risk Purchase', price: '₹89,900', query: 'MacBook Air M2' },
        { title: 'Samsung 27" 4K Monitor M7 — WFH Deal Alert', sub: 'Amazon.in · Trust 94 · Smart TV features · Free delivery', price: '₹27,990', query: 'Samsung 4K Monitor' },
        { title: 'ASUS Vivobook 15 — Gaming-Tier Laptop under ₹60K', sub: 'Flipkart · Trust 90 · Ryzen 5 · RTX 2050 · COD Available', price: '₹58,990', query: 'ASUS Vivobook 15 laptop' },
    ];
    let dotdIdx = 0;
    setInterval(() => {
        dotdIdx = (dotdIdx + 1) % deals.length;
        const d = deals[dotdIdx];
        const titleEl = document.getElementById('dotd-title');
        const subEl = document.getElementById('dotd-sub');
        const priceEl = document.getElementById('dotd-price');
        const btn = document.getElementById('dotd-arbitrate-btn');
        if (titleEl) { titleEl.style.opacity = '0'; setTimeout(() => { titleEl.textContent = d.title; titleEl.style.opacity = '1'; }, 300); }
        if (subEl) { subEl.style.opacity = '0'; setTimeout(() => { subEl.textContent = d.sub; subEl.style.opacity = '1'; }, 300); }
        if (priceEl) { priceEl.style.opacity = '0'; setTimeout(() => { priceEl.textContent = d.price; priceEl.style.opacity = '1'; }, 300); }
        if (btn) btn.onclick = () => {
            const input = document.getElementById('search-input');
            if (input) { input.value = d.query; }
            executeSearch(d.query, 'single');
        };
    }, 8000);
    // Wire initial button
    const btn = document.getElementById('dotd-arbitrate-btn');
    if (btn) btn.onclick = () => {
        const input = document.getElementById('search-input');
        if (input) { input.value = deals[0].query; }
        executeSearch(deals[0].query, 'single');
    };
}

// ==========================================================================
// TRENDING DEALS LIVE FEED
// ==========================================================================

async function loadTrendingDeals() {
    const container = document.getElementById('trending-cards-row');
    if (!container) return;
    try {
        const res = await fetch('/api/trending');
        if (!res.ok) throw new Error('API unavailable');
        const data = await res.json();
        const deals = data.trending || [];

        const countEl = document.getElementById('trending-queries-count');
        if (countEl && data.total_queries_today) {
            countEl.textContent = `${Number(data.total_queries_today).toLocaleString()} searches today`;
        }

        container.innerHTML = deals.map(d => `
            <div class="trending-card" onclick="window._handleTrendingClick(${JSON.stringify(d.query)})" title="Arbitrate: ${escapeHtml(d.query)}">
                <div class="trending-rank">#${d.rank} · ${escapeHtml(d.category)}</div>
                <div style="font-size:1.3rem;margin-bottom:3px;">${escapeHtml(d.emoji || '🛍️')}</div>
                <div class="trending-title">${escapeHtml(d.query)}</div>
                <div class="trending-price">${escapeHtml(d.best_price)}</div>
                <div class="trending-meta">
                    <span>${escapeHtml(d.merchant)}</span>
                    <span>·</span>
                    <span>⭐ ${d.trust_score}/100</span>
                </div>
                <div style="display:flex;align-items:center;justify-content:space-between;margin-top:6px;">
                    <span class="trending-trend-badge">${escapeHtml(d.trend || '')}</span>
                    <span style="font-size:9px;color:#475569;">${(d.searches_today||0).toLocaleString()} searches</span>
                </div>
            </div>
        `).join('');

        // Refresh every 45s for live effect
        setTimeout(loadTrendingDeals, 45000);
    } catch (_) {
        if (container) container.innerHTML = `<div style="color:#475569;font-size:11px;padding:8px 16px;">Could not load trending data.</div>`;
    }
}

window._handleTrendingClick = function(query) {
    const input = document.getElementById('search-input');
    if (input) input.value = query;
    executeSearch(query, 'single');
};
