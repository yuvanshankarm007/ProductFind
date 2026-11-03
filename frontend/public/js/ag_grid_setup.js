/**
 * AG Grid Cockpit Configuration & Custom Cell Renderers (Quartz Dark Theme).
 * Built for PayPal AI Hackathon Sponsor Category: Best Use of AG Grid.
 * Features Pinned Columns, Live Quick Search, Custom Cell Renderers, and Native CSV Export.
 */

import { escapeHtml, sanitizeUrl } from './security.js';
import { openDossierModal } from './merkle_modal.js';
import { showToast } from './state.js';

let gridApi = null;

export function initializeAgGrid(containerId) {
    const gridDiv = document.getElementById(containerId);
    if (!gridDiv) return null;

    const columnDefs = [
        // 1. Pinned Left: Store Branding & Merchant
        {
            headerName: "Merchant & Store",
            field: "merchant",
            pinned: "left",
            width: 210,
            filter: "agTextColumnFilter",
            cellRenderer: (params) => {
                const data = params.data;
                const country = escapeHtml(data.origin_country || "US");
                const store = escapeHtml(data.merchant || "Retail Partner");
                const domain = escapeHtml(data.merchant_domain || "");
                return `
                    <div style="display: flex; align-items: center; gap: 8px; height: 100%;">
                        <div style="font-weight: 700; color: #ffffff; line-height: 1.2;">
                            <div>${store}</div>
                            <div style="font-size: 11px; color: #94a3b8; font-family: monospace;">${domain} • ${country}</div>
                        </div>
                    </div>
                `;
            }
        },
        // 2. Product Title & Condition
        {
            headerName: "Product & Hardware Spec",
            field: "product_title",
            width: 280,
            filter: "agTextColumnFilter",
            cellRenderer: (params) => {
                const data = params.data;
                const title = escapeHtml(data.product_title || "");
                const condition = escapeHtml(data.condition || "Brand New");
                const url = sanitizeUrl(data.listing_url);
                return `
                    <div style="line-height: 1.3; padding: 4px 0;">
                        <a href="${url}" target="_blank" rel="noopener noreferrer" style="color: #60a5fa; text-decoration: none; font-weight: 600; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;" title="${title}">
                            ${title} ↗
                        </a>
                        <div style="font-size: 11px; color: #94a3b8;">${condition}</div>
                    </div>
                `;
            }
        },
        // 3. Sticker Landed Outlay
        {
            headerName: "Sticker Outlay",
            field: "landed_outlay_conv",
            width: 140,
            sortable: true,
            cellRenderer: (params) => {
                const val = escapeHtml(params.value || (params.data && (params.data.landed_outlay_conv || params.data.sticker_price_conv)) || "$0.00");
                return `<span style="color: #94a3b8; font-family: monospace; font-size: 13px;">${val}</span>`;
            }
        },
        // 4. Mathematical Risk-Adjusted TCO
        {
            headerName: "Risk-Adjusted TCO",
            field: "tco_conv",
            width: 165,
            sortable: true,
            cellRenderer: (params) => {
                const val = escapeHtml(params.value || "$0.00");
                return `
                    <div style="font-weight: 800; color: #34d399; font-family: monospace; font-size: 14px;">
                        ${val}
                    </div>
                `;
            }
        },
        // 5. Merchant Trust Index
        {
            headerName: "Trust Index",
            field: "trust_score",
            width: 145,
            sortable: true,
            cellRenderer: (params) => {
                const score = parseInt(params.value || 80, 10);
                const color = score >= 85 ? "#10b981" : (score >= 70 ? "#3b82f6" : "#f59e0b");
                return `
                    <div style="display: flex; align-items: center; gap: 8px; height: 100%;">
                        <div style="flex: 1; height: 6px; background: #334155; border-radius: 3px; overflow: hidden;">
                            <div style="width: ${score}%; height: 100%; background: ${color};"></div>
                        </div>
                        <span style="font-size: 12px; font-weight: 700; color: ${color}; font-family: monospace;">${score}/100</span>
                    </div>
                `;
            }
        },
        // 6. Service Assurance Chips (COD, Open Box, Exchange)
        {
            headerName: "Assurance Badges",
            field: "badges",
            width: 220,
            cellRenderer: (params) => {
                const data = params.data;
                const chips = [];
                if (data.cod_available) {
                    chips.push(`<span class="chip chip-success" style="font-size: 10px; padding: 2px 6px;">COD</span>`);
                }
                if (data.open_box_delivery) {
                    chips.push(`<span class="chip chip-success" style="font-size: 10px; padding: 2px 6px;">Open Box OTP</span>`);
                }
                if (data.exchange_available) {
                    chips.push(`<span class="chip" style="font-size: 10px; padding: 2px 6px;">Exchange</span>`);
                }
                if (!chips.length) {
                    chips.push(`<span class="chip" style="font-size: 10px; padding: 2px 6px; color: #64748b;">Standard Sealed</span>`);
                }
                return `<div style="display: flex; gap: 4px; align-items: center; height: 100%;">${chips.join('')}</div>`;
            }
        },
        // 7. Stock Status & Warning Pill
        {
            headerName: "Availability",
            field: "stock_status",
            width: 140,
            cellRenderer: (params) => {
                const data = params.data;
                const inStock = data.in_stock && !data.is_dead_link;
                const status = escapeHtml(data.stock_status || "In Stock");
                const bg = inStock ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)";
                const textCol = inStock ? "#34d399" : "#fb7185";
                const border = inStock ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)";
                return `
                    <span style="padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; background: ${bg}; color: ${textCol}; border: 1px solid ${border};">
                        ${status}
                    </span>
                `;
            }
        },
        // 8. Pinned Right: 1-Click Interactive PayPal Trigger
        {
            headerName: "Action",
            field: "action",
            pinned: "right",
            width: 160,
            cellRenderer: (params) => {
                const data = params.data;
                const disabled = !data.in_stock || data.is_dead_link;
                const btnText = disabled ? "Out of Stock" : "Pay with PayPal";
                const bg = disabled ? "#334155" : "linear-gradient(135deg, #0070ba, #003087)";
                const cursor = disabled ? "not-allowed" : "pointer";
                const opacity = disabled ? "0.6" : "1.0";

                return `
                    <div style="display: flex; align-items: center; justify-content: center; height: 100%;">
                        <button 
                            type="button" 
                            class="ag-paypal-btn" 
                            data-listing-id="${escapeHtml(data.id)}"
                            data-merchant="${escapeHtml(data.merchant)}"
                            data-price="${escapeHtml(data.tco_conv)}"
                            style="background: ${bg}; color: #ffffff; border: none; border-radius: 6px; padding: 5px 12px; font-size: 11px; font-weight: 700; cursor: ${cursor}; opacity: ${opacity};"
                            ${disabled ? "disabled" : ""}
                        >
                            ${btnText}
                        </button>
                    </div>
                `;
            }
        }
    ];

    const gridOptions = {
        columnDefs: columnDefs,
        rowData: [],
        theme: 'quartz-dark',
        rowHeight: 52,
        headerHeight: 40,
        pagination: true,
        paginationPageSize: 10,
        paginationPageSizeSelector: [10, 20, 50],
        enableCellTextSelection: true,
        suppressCellFocus: false,
        defaultColDef: {
            resizable: true,
            sortable: true
        },
        onRowClicked: (event) => {
            // Optional row click handling
        }
    };

    // Global listener for embedded AG Grid buttons
    gridDiv.addEventListener('click', (e) => {
        const btn = e.target.closest('.ag-paypal-btn');
        if (btn && !btn.disabled) {
            const listingId = btn.getAttribute('data-listing-id');
            const merchant = btn.getAttribute('data-merchant');
            const price = btn.getAttribute('data-price');
            handleGridCheckout(listingId, merchant, price);
        }
    });

    gridApi = agGrid.createGrid(gridDiv, gridOptions);
    return gridApi;
}

export function updateGridData(rows) {
    if (gridApi) {
        gridApi.setGridOption('rowData', rows || []);
    }
}

export function filterGrid(query) {
    if (gridApi) {
        gridApi.setGridOption('quickFilterText', query || '');
    }
}

export function exportGridCsv() {
    if (gridApi) {
        gridApi.exportDataAsCsv({
            fileName: `ProductFind_Audit_${new Date().toISOString().slice(0, 10)}.csv`
        });
        showToast("Exported multi-agent comparison matrix as CSV.", "success");
    }
}

async function handleGridCheckout(listingId, merchant, price) {
    showToast(`Initializing 1-Click PayPal checkout for ${merchant} (${price})...`, "info");
    try {
        const res = await fetch('/api/paypal/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount: parseFloat(price.replace(/[^0-9.]/g, '')) || 299.99,
                item_name: `ProductFind Verified: ${merchant}`,
                currency: "USD"
            })
        });
        if (res.ok) {
            const data = await res.json();
            showToast(`PayPal Order Created: ${data.id}. Opening Section 13 Dispute Dossier...`, "success");
            openDossierModal(data.id, merchant, price);
        } else {
            showToast("Failed to initialize PayPal Order.", "error");
        }
    } catch (err) {
        showToast(`Checkout Error: ${err.message}`, "error");
    }
}
