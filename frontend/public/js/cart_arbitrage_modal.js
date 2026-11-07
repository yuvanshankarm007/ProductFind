/**
 * Multi-Retailer Knapsack Cart Split & Arbitrage Modal.
 * Renders combinatorial split carts across Amazon, Flipkart, OEM Direct,
 * evaluates shipping fee step-functions and card bonuses, and displays monopoly comparisons.
 */

import { escapeHtml } from './security.js';
import { showToast } from './state.js';
import { openDossierModal } from './merkle_modal.js';

let activeSplitData = null;

export async function openWorkflowArbitrageModal(query, budgetLimit = null, itemsList = null) {
    const modal = document.getElementById('workflow-arbitrage-modal');
    if (!modal) return;

    modal.style.display = 'flex';
    const contentEl = document.getElementById('workflow-arbitrage-modal-content');
    contentEl.innerHTML = `
        <div style="text-align: center; padding: 2.5rem; color: #94a3b8;">
            <div style="font-size: 28px; margin-bottom: 12px; animation: spin 1.5s linear infinite;">⚡</div>
            <div style="font-weight: 700; color: #38bdf8; font-size: 14px;">Computing Combinatorial Knapsack Arbitrage...</div>
            <div style="font-size: 12px; margin-top: 6px;">Jointly optimizing across Amazon, Flipkart, & OEM Direct baskets for "${escapeHtml(query)}"</div>
        </div>
    `;

    try {
        const payload = {
            query: query,
            budget_limit: budgetLimit
        };
        if (itemsList && itemsList.length > 0) {
            payload.items_list = itemsList;
        }

        const res = await fetch('/api/workflow/arbitrate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            throw new Error(`Arbitration service responded with HTTP ${res.status}`);
        }

        const data = await res.json();
        activeSplitData = data;
        renderArbitrageResult(data, query);
    } catch (err) {
        contentEl.innerHTML = `
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 1.5rem; color: #f87171; text-align: center;">
                <div style="font-weight: 700; font-size: 14px; margin-bottom: 6px;">Arbitration Failed</div>
                <div style="font-size: 12px;">${escapeHtml(err.message)}</div>
            </div>
        `;
    }
}

export function closeWorkflowArbitrageModal() {
    const modal = document.getElementById('workflow-arbitrage-modal');
    if (modal) modal.style.display = 'none';
}

function renderArbitrageResult(data, query) {
    const contentEl = document.getElementById('workflow-arbitrage-modal-content');
    if (!contentEl) return;

    const optTotal = data.optimized_total || 0;
    const netSavings = data.net_arbitrage_savings || 0;
    const savingsPct = data.savings_percentage || 0;
    const cardSavings = data.card_bonus_savings || 0;
    const shipSavings = data.shipping_savings || 0;
    const platformCut = data.platform_arbitrage_cut || 0;
    const subCarts = data.sub_carts || [];
    const monopolies = data.monopoly_alternatives || {};
    const unfulfilled = data.unfulfilled_categories || [];

    let subCartsHtml = '';
    subCarts.forEach((sc) => {
        const retailerColor = sc.retailer === 'Amazon' ? '#ff9900' : sc.retailer === 'Flipkart' ? '#2874f0' : '#10b981';
        let itemsListHtml = '';
        (sc.items || []).forEach(item => {
            itemsListHtml += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px dashed rgba(255,255,255,0.08); font-size: 11.5px;">
                    <div>
                        <div style="color: #f1f5f9; font-weight: 600;">${escapeHtml(item.title)}</div>
                        <div style="color: #64748b; font-size: 10px;">${escapeHtml(item.brand)} | ${escapeHtml(item.category)} | Seller: ${escapeHtml(item.seller_name || 'Authorized')}</div>
                    </div>
                    <div style="text-align: right; white-space: nowrap;">
                        <span style="color: #38bdf8; font-weight: 700; font-family: monospace;">₹${Number(item.current_price).toLocaleString('en-IN')}</span>
                        <div style="font-size: 9px; color: #10b981;">🛡️ 100% Sealed</div>
                    </div>
                </div>
            `;
        });

        let promosHtml = '';
        if (sc.promotions_applied && sc.promotions_applied.length > 0) {
            promosHtml = `
                <div style="margin-top: 6px; font-size: 10px; color: #a7f3d0; background: rgba(16, 185, 129, 0.08); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.2);">
                    🎁 Promos: ${sc.promotions_applied.map(p => escapeHtml(p)).join(' • ')}
                </div>
            `;
        }

        subCartsHtml += `
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-left: 4px solid ${retailerColor}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: ${retailerColor}; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                        <span>🛒 ${escapeHtml(sc.retailer)} Basket</span>
                        <span style="font-size: 10px; color: #94a3b8; font-weight: normal;">(${sc.items ? sc.items.length : 0} items)</span>
                    </div>
                    <div style="font-weight: 700; color: #f8fafc; font-family: monospace; font-size: 13px;">
                        ₹${Number(sc.retailer_total).toLocaleString('en-IN')}
                    </div>
                </div>
                <div>${itemsListHtml}</div>
                <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; color: #94a3b8; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px;">
                    <span>Subtotal: ₹${Number(sc.items_subtotal).toLocaleString('en-IN')}</span>
                    <span>Shipping: ${sc.shipping_fee === 0 ? '<strong style="color: #10b981;">FREE</strong>' : `₹${sc.shipping_fee}`}</span>
                    <span>Card Discount: <strong style="color: #34d399;">-₹${Number(sc.card_discount_applied).toLocaleString('en-IN')}</strong></span>
                </div>
                ${promosHtml}
            </div>
        `;
    });

    let monopoliesHtml = '';
    Object.entries(monopolies).forEach(([ret, mono]) => {
        const penalty = (mono.total_cost || 0) - optTotal;
        monopoliesHtml += `
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 8px 10px; text-align: center; flex: 1; min-width: 140px;">
                <div style="font-size: 11px; color: #94a3b8; font-weight: 600;">${escapeHtml(ret)} Monopoly</div>
                <div style="font-size: 13px; font-weight: 700; color: #cbd5e1; font-family: monospace; margin: 3px 0;">₹${Number(mono.total_cost || 0).toLocaleString('en-IN')}</div>
                <div style="font-size: 10px; color: ${penalty > 0 ? '#f87171' : '#94a3b8'}; font-weight: 600;">
                    ${penalty > 0 ? `+₹${Number(penalty).toLocaleString('en-IN')} penalty` : 'Baseline'}
                </div>
            </div>
        `;
    });

    let unfulfilledHtml = '';
    if (unfulfilled.length > 0) {
        unfulfilledHtml = `
            <div style="background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 11px; color: #fde047;">
                ⚠️ <strong>Inventory Shortfall:</strong> No in-stock listings available across retailers for: ${unfulfilled.map(u => escapeHtml(u)).join(', ')}.
            </div>
        `;
    }

    contentEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
            <!-- Header Summary -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px;">
                <div>
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #38bdf8; font-weight: 700;">Optimal Multi-Retailer Arbitrage</div>
                    <div style="font-size: 16px; font-weight: 800; color: #f8fafc; margin-top: 2px;">${escapeHtml(query)}</div>
                </div>
                <div style="text-align: right;">
                    <span style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #34d399; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-size: 12px;">
                        ${savingsPct}% SAVED
                    </span>
                </div>
            </div>

            <!-- KPI Banner -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px;">
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #a7f3d0; text-transform: uppercase; font-weight: 700;">Net Arbitrage Savings</div>
                    <div style="font-size: 18px; font-weight: 800; color: #10b981; font-family: monospace;">₹${Number(netSavings).toLocaleString('en-IN')}</div>
                    <div style="font-size: 9px; color: #6ee7b7;">vs Single Retailer</div>
                </div>
                <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #7dd3fc; text-transform: uppercase; font-weight: 700;">Optimal Split Total</div>
                    <div style="font-size: 18px; font-weight: 800; color: #38bdf8; font-family: monospace;">₹${Number(optTotal).toLocaleString('en-IN')}</div>
                    <div style="font-size: 9px; color: #bae6fd;">${subCarts.length} Retailer Baskets</div>
                </div>
                <div style="background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #d8b4fe; text-transform: uppercase; font-weight: 700;">Card & Tier Bonuses</div>
                    <div style="font-size: 18px; font-weight: 800; color: #c084fc; font-family: monospace;">₹${Number(cardSavings).toLocaleString('en-IN')}</div>
                    <div style="font-size: 9px; color: #e9d5ff;">Thresholds Applied</div>
                </div>
                <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="font-size: 10px; color: #fda4af; text-transform: uppercase; font-weight: 700;">Platform 1% Cut</div>
                    <div style="font-size: 18px; font-weight: 800; color: #fb7185; font-family: monospace;">₹${Number(platformCut).toLocaleString('en-IN')}</div>
                    <div style="font-size: 9px; color: #fecdd3;">Contingent on Savings</div>
                </div>
            </div>

            ${unfulfilledHtml}

            <!-- Sub-Carts Breakdown -->
            <div>
                <div style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;">Multi-Store Baskets & Cross-Retailer Fulfillment:</div>
                ${subCartsHtml}
            </div>

            <!-- Single Store Monopoly Comparison -->
            <div>
                <div style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;">Single-Store Monopoly Penalty:</div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    ${monopoliesHtml}
                </div>
            </div>

            <!-- Action CTAs -->
            <div style="display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap;">
                <button type="button" id="btn-lock-split-cart" class="control-btn btn-primary" style="flex: 2; min-width: 180px; justify-content: center; font-weight: 700; background: linear-gradient(135deg, #0ea5e9, #2563eb); border: 1px solid #38bdf8;">
                    🎯 1-Click Lock Bundle & Checkout
                </button>
                <button type="button" id="btn-merkle-escrow" class="control-btn" style="flex: 1.5; min-width: 160px; justify-content: center; background: rgba(99, 102, 241, 0.15); border-color: rgba(99, 102, 241, 0.4); color: #a5b4fc; font-weight: 600;">
                    📜 Merkle Dispute Dossier
                </button>
                <button type="button" id="btn-export-split-json" class="control-btn" style="flex: 1; min-width: 120px; justify-content: center;">
                    📥 Export Plan (.JSON)
                </button>
                <button type="button" id="btn-close-arbitrage-done" class="control-btn" style="padding: 10px 16px; justify-content: center;">
                    Close
                </button>
            </div>
        </div>
    `;

    // 1-Click Lock Snipe Deal
    const btnLock = document.getElementById('btn-lock-split-cart');
    if (btnLock) {
        btnLock.addEventListener('click', async () => {
            btnLock.disabled = true;
            btnLock.textContent = "Securing Pre-Authorized Lock...";
            try {
                // Find primary item ID from sub-carts
                const firstCart = (subCarts[0] && subCarts[0].items && subCarts[0].items[0]) ? subCarts[0].items[0] : null;
                const listingId = firstCart ? firstCart.id : 'wf-arbitrage-pack';

                const lockRes = await fetch('/api/snipe/lock', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        listing_id: listingId,
                        target_price: optTotal,
                        preauth_payment_method: 'ONE_CLICK_ESCROW',
                        auto_execute_within_seconds: 600
                    })
                });

                if (lockRes.ok) {
                    const lockData = await lockRes.json();
                    showToast(`Bundle Deal Locked! Receipt: ${lockData.receipt_hash.substring(0, 16)}...`, "success");
                    btnLock.textContent = "🔒 Bundle Rate Locked (10m Escrow)";
                    btnLock.style.background = "#10b981";
                    btnLock.style.borderColor = "#34d399";
                } else {
                    throw new Error("Lock service error");
                }
            } catch (err) {
                showToast("Failed to lock snipe deal: " + err.message, "error");
                btnLock.disabled = false;
                btnLock.textContent = "🎯 1-Click Lock Bundle & Checkout";
            }
        });
    }

    // Merkle Escrow Dispute Dossier
    const btnMerkle = document.getElementById('btn-merkle-escrow');
    if (btnMerkle) {
        btnMerkle.addEventListener('click', () => {
            closeWorkflowArbitrageModal();
            openDossierModal(data.workflow_id || 'wf-bundle-escrow', 'Amazon + Flipkart + OEM Knapsack Escrow', `₹${optTotal}`);
        });
    }

    // Export Plan JSON
    const btnExport = document.getElementById('btn-export-split-json');
    if (btnExport) {
        btnExport.addEventListener('click', () => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Arbitrage_Cart_${data.workflow_id || 'plan'}.json`;
            a.click();
            URL.revokeObjectURL(url);
            showToast("Arbitrage plan exported.", "success");
        });
    }

    // Close
    const btnDone = document.getElementById('btn-close-arbitrage-done');
    if (btnDone) {
        btnDone.addEventListener('click', closeWorkflowArbitrageModal);
    }
}
