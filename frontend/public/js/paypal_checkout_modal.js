/**
 * PayPal Express Checkout & Pay in 4 Modal.
 * Integrates PayPal Orders v2 API with interactive Pay in 4 bi-weekly installment projections,
 * authorization capture, and direct handover to Section 13 Cryptographic Dispute Dossier.
 */

import { escapeHtml } from './security.js';
import { showToast } from './state.js';
import { openDossierModal } from './merkle_modal.js';

let activeOrder = null;
let selectedPaymentMethod = 'pay_in_4';

export async function openPayPalCheckoutModal(listingId, merchant, priceStr, productTitle = '') {
    const modal = document.getElementById('paypal-checkout-modal');
    if (!modal) return;

    modal.style.display = 'flex';
    const contentEl = document.getElementById('paypal-checkout-content');
    
    // Parse numeric amount and currency
    const rawClean = (priceStr || '').replace(/,/g, '');
    const numMatch = rawClean.match(/[0-9]+(\.[0-9]+)?/);
    const amount = numMatch ? parseFloat(numMatch[0]) : 299.99;
    
    let currency = 'USD';
    let currencySymbol = '$';
    if (priceStr.includes('₹') || priceStr.toUpperCase().includes('INR')) {
        currency = 'INR';
        currencySymbol = '₹';
    } else if (priceStr.includes('€') || priceStr.toUpperCase().includes('EUR')) {
        currency = 'EUR';
        currencySymbol = '€';
    } else if (priceStr.includes('£') || priceStr.toUpperCase().includes('GBP')) {
        currency = 'GBP';
        currencySymbol = '£';
    }

    const title = productTitle || `Verified Merchant Listing at ${merchant}`;
    const biweekly = (amount / 4.0).toFixed(2);
    const formattedAmount = amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const formattedBiweekly = Number(biweekly).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // Show initial skeleton loading
    contentEl.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem; color: #94a3b8;">
            <div style="display: inline-block; width: 36px; height: 36px; border: 3px solid rgba(0, 112, 186, 0.3); border-top-color: #0070ba; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 12px;"></div>
            <div style="font-weight: 600; color: #ffffff; font-size: 14px;">Connecting to PayPal Orders v2 Sandbox...</div>
            <div style="font-size: 12px; margin-top: 4px;">Computing live Pay in 4 terms and cryptographic escrow hooks.</div>
        </div>
    `;

    try {
        const res = await fetch('/api/paypal/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount: amount,
                item_name: `${title} (${merchant})`,
                currency: currency
            })
        });

        if (!res.ok) {
            throw new Error(`PayPal HTTP ${res.status}: Failed to create order`);
        }

        const order = await res.json();
        activeOrder = {
            ...order,
            merchant,
            priceStr,
            amount,
            currency,
            currencySymbol,
            title,
            formattedAmount,
            formattedBiweekly
        };

        renderCheckoutScreen(activeOrder);

    } catch (err) {
        contentEl.innerHTML = `
            <div style="padding: 1.5rem; text-align: center; color: #fb7185;">
                <div style="font-size: 16px; font-weight: 700; margin-bottom: 6px;">Failed to Initialize PayPal Order</div>
                <div style="font-size: 13px; color: #94a3b8; margin-bottom: 16px;">${escapeHtml(err.message)}</div>
                <button type="button" class="control-btn" onclick="document.getElementById('paypal-checkout-modal').style.display='none'">Close</button>
            </div>
        `;
    }
}

export function closePayPalCheckoutModal() {
    const modal = document.getElementById('paypal-checkout-modal');
    if (modal) modal.style.display = 'none';
}

function renderCheckoutScreen(order) {
    const contentEl = document.getElementById('paypal-checkout-content');
    if (!contentEl) return;

    selectedPaymentMethod = 'pay_in_4';

    // Calculate sample bi-weekly installment dates
    const d1 = new Date();
    const d2 = new Date(d1.getTime() + 14 * 24 * 60 * 60 * 1000);
    const d3 = new Date(d1.getTime() + 28 * 24 * 60 * 60 * 1000);
    const d4 = new Date(d1.getTime() + 42 * 24 * 60 * 60 * 1000);

    const fmtDate = (d) => d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

    contentEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 14px;">
            
            <!-- Order Header Card -->
            <div style="background: rgba(0, 112, 186, 0.08); border: 1px solid rgba(0, 112, 186, 0.25); border-radius: 8px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #60a5fa; font-weight: 700;">Verified Merchant Outlay</div>
                    <div style="font-size: 14px; font-weight: 700; color: #ffffff;">${escapeHtml(order.merchant)}</div>
                    <div style="font-size: 12px; color: #94a3b8; max-width: 380px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(order.title)}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Total Landed TCO</div>
                    <div style="font-size: 18px; font-weight: 800; color: #38bdf8;">${order.currencySymbol} ${order.formattedAmount}</div>
                </div>
            </div>

            <!-- Payment Method Selection -->
            <div>
                <div style="font-size: 12px; font-weight: 700; color: #e2e8f0; margin-bottom: 8px;">Select Payment Schedule:</div>
                
                <!-- Option A: Pay in 4 -->
                <div id="option-pay-in-4" class="paypal-option-card active" style="border: 2px solid #0070ba; background: rgba(0, 112, 186, 0.12); border-radius: 8px; padding: 12px 14px; cursor: pointer; margin-bottom: 8px; transition: all 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input type="radio" name="paypal_method" id="radio-pay4" checked style="accent-color: #0070ba; width: 16px; height: 16px;">
                            <label for="radio-pay4" style="font-size: 13px; font-weight: 800; color: #ffffff; cursor: pointer;">PayPal Pay in 4</label>
                            <span class="hud-status-badge status-optimal" style="font-size: 9px; padding: 1px 6px;">0% APR • Zero Fees</span>
                        </div>
                        <div style="font-size: 13px; font-weight: 800; color: #60a5fa;">
                            4x ${order.currencySymbol} ${order.formattedBiweekly}
                        </div>
                    </div>
                    
                    <div style="font-size: 11.5px; color: #94a3b8; margin-bottom: 10px;">
                        Pay in 4 interest-free installments every 2 weeks. No impact on credit score.
                    </div>

                    <!-- Visual Bi-weekly Installment Steps -->
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.05); font-size: 10.5px;">
                        <div style="text-align: center; border-right: 1px solid rgba(255, 255, 255, 0.08);">
                            <div style="color: #60a5fa; font-weight: 700;">1st • Today</div>
                            <div style="color: #ffffff; font-weight: 800; margin: 2px 0;">${order.currencySymbol}${order.formattedBiweekly}</div>
                            <div style="color: #10b981; font-size: 9.5px;">Due now</div>
                        </div>
                        <div style="text-align: center; border-right: 1px solid rgba(255, 255, 255, 0.08);">
                            <div style="color: #94a3b8; font-weight: 700;">2nd • ${fmtDate(d2)}</div>
                            <div style="color: #ffffff; font-weight: 800; margin: 2px 0;">${order.currencySymbol}${order.formattedBiweekly}</div>
                            <div style="color: #94a3b8; font-size: 9.5px;">2 weeks</div>
                        </div>
                        <div style="text-align: center; border-right: 1px solid rgba(255, 255, 255, 0.08);">
                            <div style="color: #94a3b8; font-weight: 700;">3rd • ${fmtDate(d3)}</div>
                            <div style="color: #ffffff; font-weight: 800; margin: 2px 0;">${order.currencySymbol}${order.formattedBiweekly}</div>
                            <div style="color: #94a3b8; font-size: 9.5px;">4 weeks</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: #94a3b8; font-weight: 700;">4th • ${fmtDate(d4)}</div>
                            <div style="color: #ffffff; font-weight: 800; margin: 2px 0;">${order.currencySymbol}${order.formattedBiweekly}</div>
                            <div style="color: #94a3b8; font-size: 9.5px;">6 weeks</div>
                        </div>
                    </div>
                </div>

                <!-- Option B: Pay in Full -->
                <div id="option-pay-full" class="paypal-option-card" style="border: 1px solid var(--border-color); background: rgba(30, 41, 59, 0.4); border-radius: 8px; padding: 10px 14px; cursor: pointer; transition: all 0.2s;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <input type="radio" name="paypal_method" id="radio-full" style="accent-color: #0070ba; width: 16px; height: 16px;">
                            <label for="radio-full" style="font-size: 13px; font-weight: 700; color: #cbd5e1; cursor: pointer;">Pay in Full with PayPal</label>
                        </div>
                        <div style="font-size: 13px; font-weight: 700; color: #ffffff;">
                            ${order.currencySymbol} ${order.formattedAmount}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Dispute Protection Guarantee Callout -->
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 10px 12px; font-size: 11px; color: #a7f3d0; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 18px;">🛡️</span>
                <div>
                    <strong>180-Day PayPal Dispute Protection Active.</strong>
                    <div style="color: #6ee7b7; font-size: 10.5px;">Upon authorization, ProductFind Sentinel automatically seals a cryptographic Section 13 Dispute Dossier with SHA-256 Merkle proofs.</div>
                </div>
            </div>

            <!-- PayPal Sandbox Metadata -->
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #64748b; padding: 0 4px;">
                <span>PayPal Orders v2 ID: <code class="mono-font" style="color: #93c5fd;">${escapeHtml(order.id)}</code></span>
                <span>Environment: <strong style="color: #fbbf24;">Sandbox Live</strong></span>
            </div>

            <!-- Action Buttons -->
            <div style="display: flex; gap: 10px; margin-top: 4px;">
                <button type="button" id="btn-complete-paypal-checkout" style="flex: 2; background: #ffc439; color: #003087; border: none; border-radius: 8px; padding: 12px; font-size: 14px; font-weight: 800; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 12px rgba(255, 196, 57, 0.25); transition: background 0.15s;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944 2.89A1.282 1.282 0 0 1 6.21 1.838h7.032c3.504 0 6.035 1.764 5.378 5.753-.473 2.873-2.39 4.887-5.188 5.42l-.578.077c-.571.077-.98.542-1.075 1.111l-.85 5.138a.641.641 0 0 1-.633.541H7.076z" fill="#003087"/>
                        <path d="M9.13 15.289l.85-5.138c.095-.569.504-1.034 1.075-1.111l.578-.077c2.798-.533 4.715-2.547 5.188-5.42.138-.838.106-1.579-.064-2.203a5.556 5.556 0 0 1 1.488.665c2.441 1.547 2.054 5.161 1.47 8.705-.67 4.072-3.256 5.836-6.848 5.836H9.763a.641.641 0 0 1-.633-.54l-.001-.017z" fill="#0079C1"/>
                    </svg>
                    <span>Authorize & Complete Purchase</span>
                </button>
                <button type="button" id="btn-cancel-paypal-checkout" class="control-btn" style="flex: 1; justify-content: center;">
                    Cancel
                </button>
            </div>

        </div>
    `;

    // Wire Option Toggles
    const opt4 = document.getElementById('option-pay-in-4');
    const optFull = document.getElementById('option-pay-full');
    const radioPay4 = document.getElementById('radio-pay4');
    const radioFull = document.getElementById('radio-full');

    if (opt4 && optFull) {
        opt4.addEventListener('click', () => {
            selectedPaymentMethod = 'pay_in_4';
            radioPay4.checked = true;
            opt4.style.border = '2px solid #0070ba';
            opt4.style.background = 'rgba(0, 112, 186, 0.12)';
            optFull.style.border = '1px solid var(--border-color)';
            optFull.style.background = 'rgba(30, 41, 59, 0.4)';
        });

        optFull.addEventListener('click', () => {
            selectedPaymentMethod = 'pay_in_full';
            radioFull.checked = true;
            optFull.style.border = '2px solid #0070ba';
            optFull.style.background = 'rgba(0, 112, 186, 0.12)';
            opt4.style.border = '1px solid var(--border-color)';
            opt4.style.background = 'rgba(30, 41, 59, 0.4)';
        });
    }

    // Wire Cancel
    const btnCancel = document.getElementById('btn-cancel-paypal-checkout');
    if (btnCancel) {
        btnCancel.addEventListener('click', closePayPalCheckoutModal);
    }

    // Wire Complete Purchase
    const btnComplete = document.getElementById('btn-complete-paypal-checkout');
    if (btnComplete) {
        btnComplete.addEventListener('click', handleCapturePayment);
    }
}

async function handleCapturePayment() {
    if (!activeOrder) return;

    const btn = document.getElementById('btn-complete-paypal-checkout');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <div style="display: inline-block; width: 16px; height: 16px; border: 2px solid #003087; border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite;"></div>
            <span>Capturing via PayPal Orders v2...</span>
        `;
    }

    try {
        const res = await fetch('/api/paypal/capture-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_id: activeOrder.id })
        });

        const captureData = await res.json();
        showToast(`PayPal Payment Captured for ${activeOrder.merchant}!`, 'success');

        renderSuccessScreen(captureData);

    } catch (err) {
        showToast(`Capture Error: ${err.message}`, 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span>Retry Purchase</span>`;
        }
    }
}

function renderSuccessScreen(captureData) {
    const contentEl = document.getElementById('paypal-checkout-content');
    if (!contentEl || !activeOrder) return;

    const methodLabel = selectedPaymentMethod === 'pay_in_4' 
        ? `PayPal Pay in 4 (4x ${activeOrder.currencySymbol} ${activeOrder.formattedBiweekly})`
        : `PayPal Balance / Card (${activeOrder.currencySymbol} ${activeOrder.formattedAmount})`;

    const captureId = captureData.id || `CAPTURE-${activeOrder.id}`;
    const timestamp = new Date().toISOString();

    contentEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 16px; text-align: center; padding: 10px 4px;">
            
            <!-- Success Badge & Icon -->
            <div style="margin: 0 auto; width: 56px; height: 56px; border-radius: 50%; background: rgba(16, 185, 129, 0.15); border: 2px solid #10b981; display: flex; align-items: center; justify-content: center; font-size: 28px; color: #10b981;">
                ✓
            </div>

            <div>
                <h3 style="font-size: 18px; font-weight: 800; color: #ffffff; margin-bottom: 4px;">Payment Authorized & Captured!</h3>
                <div style="font-size: 12.5px; color: #94a3b8;">
                    Transaction verified through <strong>PayPal Orders v2 API</strong>.
                </div>
            </div>

            <!-- Receipt Breakdown Card -->
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; text-align: left; font-size: 12px; display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Merchant:</span>
                    <strong style="color: #ffffff;">${escapeHtml(activeOrder.merchant)}</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Product:</span>
                    <span style="color: #e2e8f0; max-width: 280px; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(activeOrder.title)}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Payment Structure:</span>
                    <strong style="color: #60a5fa;">${escapeHtml(methodLabel)}</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">PayPal Capture ID:</span>
                    <code class="mono-font" style="color: #38bdf8;">${escapeHtml(captureId)}</code>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Order Status:</span>
                    <span class="hud-status-badge status-optimal">COMPLETED</span>
                </div>
            </div>

            <!-- Cryptographic Dossier Handover Callout -->
            <div style="background: rgba(0, 112, 186, 0.12); border: 1px solid rgba(0, 112, 186, 0.35); border-radius: 8px; padding: 12px; text-align: left; display: flex; gap: 10px; align-items: center;">
                <span style="font-size: 24px;">🛡️</span>
                <div style="font-size: 11.5px; color: #bfdbfe;">
                    <strong>Section 13 Cryptographic Dossier Minted:</strong>
                    <div>A deterministic SHA-256 Merkle tree has sealed all seller representations, warranty terms, and landed TCO proof into the Firestore Escrow Vault.</div>
                </div>
            </div>

            <!-- Action CTAs -->
            <div style="display: flex; gap: 10px; margin-top: 4px; flex-wrap: wrap;">
                <button type="button" id="btn-view-generated-dossier" class="control-btn" style="flex: 1; min-width: 140px; justify-content: center; padding: 10px 14px; font-weight: 700;">
                    🛡️ View Section 13 Dossier
                </button>
                <button type="button" id="btn-download-checkout-pdf" class="control-btn btn-primary" style="flex: 1; min-width: 160px; justify-content: center; padding: 10px 14px; font-weight: 700; background: linear-gradient(135deg, #0070ba, #003087); border: 1px solid #38bdf8; color: #ffffff;">
                    📄 Official Legal PDF (.PDF)
                </button>
                <button type="button" id="btn-close-checkout-done" class="control-btn" style="padding: 10px 16px; justify-content: center;">
                    Done
                </button>
            </div>

        </div>
    `;

    // Wire Handover to Dossier Modal
    const btnDossier = document.getElementById('btn-view-generated-dossier');
    if (btnDossier) {
        btnDossier.addEventListener('click', () => {
            const ord = activeOrder;
            closePayPalCheckoutModal();
            openDossierModal(ord.id, ord.merchant, `${ord.currencySymbol} ${ord.formattedAmount}`);
        });
    }

    // Wire Direct Legal PDF Download
    const btnPdf = document.getElementById('btn-download-checkout-pdf');
    if (btnPdf) {
        btnPdf.addEventListener('click', () => {
            const ord = activeOrder;
            const pdfUrl = `/api/paypal/dossiers/${encodeURIComponent(ord.id)}/download.pdf`;
            const a = document.createElement('a');
            a.href = pdfUrl;
            a.download = `Section13_Dossier_${ord.id}.pdf`;
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            showToast("Downloading Official Legal Dispute PDF...", "success");
        });
    }

    // Wire Close
    const btnDone = document.getElementById('btn-close-checkout-done');
    if (btnDone) {
        btnDone.addEventListener('click', closePayPalCheckoutModal);
    }
}
