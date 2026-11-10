/**
 * AG Grid Cockpit Configuration & Custom Cell Renderers (Quartz Dark Theme).
 * Features Broad Responsive Columns (Zero Horizontal Scroll), Live Quick Search,
 * Custom Cell Renderers, and Native CSV Export.
 */

import { escapeHtml, sanitizeUrl } from './security.js';
import { openDossierModal } from './merkle_modal.js';
import { openPayPalCheckoutModal } from './paypal_checkout_modal.js';
import { showToast } from './state.js';

let gridApi = null;

export function initializeAgGrid(containerId) {
    const gridDiv = document.getElementById(containerId);
    if (!gridDiv) return null;

    const columnDefs = [
        // 1. Merchant & Store (with stock status integrated)
        {
            headerName: "Merchant & Store",
            field: "merchant",
            flex: 1.2,
            minWidth: 155,
            filter: "agTextColumnFilter",
            cellRenderer: (params) => {
                const data = params.data;
                const country = escapeHtml(data.origin_country || "US");
                const store = escapeHtml(data.merchant || "Retail Partner");
                const domain = escapeHtml(data.merchant_domain || "");
                const inStock = data.in_stock && !data.is_dead_link;
                const stockPill = inStock 
                    ? `<span style="font-size: 10px; color: #34d399; font-weight: 700; margin-left: 4px;">🟢 In Stock</span>`
                    : `<span style="font-size: 10px; color: #fb7185; font-weight: 700; margin-left: 4px;">🔴 Sold Out</span>`;

                return `
                    <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; line-height: 1.3;">
                        <div style="font-weight: 700; color: #ffffff; display: flex; align-items: center;">
                            <span>${store}</span>
                            ${stockPill}
                        </div>
                        <div style="font-size: 11px; color: #94a3b8; font-family: monospace;">${domain} • ${country}</div>
                    </div>
                `;
            }
        },
        // 2. Product Title & Hardware Spec
        {
            headerName: "Product & Hardware Spec",
            field: "product_title",
            flex: 2.2,
            minWidth: 210,
            filter: "agTextColumnFilter",
            cellRenderer: (params) => {
                const data = params.data;
                const title = escapeHtml(data.product_title || "");
                const condition = escapeHtml(data.condition || "Brand New");
                const url = sanitizeUrl(data.listing_url);
                return `
                    <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; line-height: 1.3;">
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
            flex: 0.95,
            minWidth: 110,
            sortable: true,
            cellRenderer: (params) => {
                const val = escapeHtml(params.value || (params.data && (params.data.landed_outlay_conv || params.data.sticker_price_conv)) || "$0.00");
                return `<div style="display: flex; align-items: center; height: 100%; color: #94a3b8; font-family: monospace; font-size: 13px;">${val}</div>`;
            }
        },
        // 4. Mathematical Risk-Adjusted TCO
        {
            headerName: "Risk-Adjusted TCO",
            field: "tco_conv",
            flex: 1.1,
            minWidth: 130,
            sortable: true,
            cellRenderer: (params) => {
                const val = escapeHtml(params.value || "$0.00");
                return `
                    <div style="display: flex; align-items: center; height: 100%; font-weight: 800; color: #34d399; font-family: monospace; font-size: 13.5px;">
                        ${val}
                    </div>
                `;
            }
        },
        // 5. Merchant Trust Index
        {
            headerName: "Trust Index",
            field: "trust_score",
            flex: 1.0,
            minWidth: 115,
            sortable: true,
            cellRenderer: (params) => {
                const score = parseInt(params.value || 80, 10);
                const color = score >= 85 ? "#10b981" : (score >= 70 ? "#3b82f6" : "#f59e0b");
                return `
                    <div style="display: flex; align-items: center; gap: 8px; height: 100%;">
                        <div style="flex: 1; height: 6px; background: #334155; border-radius: 3px; overflow: hidden;">
                            <div style="width: ${score}%; height: 100%; background: ${color};"></div>
                        </div>
                        <span style="font-size: 11.5px; font-weight: 700; color: ${color}; font-family: monospace;">${score}/100</span>
                    </div>
                `;
            }
        },
        // 6. Service Assurance Chips (COD, Open Box, Exchange)
        {
            headerName: "Assurance Badges",
            field: "badges",
            flex: 1.25,
            minWidth: 145,
            cellRenderer: (params) => {
                const data = params.data;
                const chips = [];
                if (data.cod_available) {
                    chips.push(`<span class="chip chip-success" style="font-size: 9.5px; padding: 2px 5px;">COD</span>`);
                }
                if (data.open_box_delivery) {
                    chips.push(`<span class="chip chip-success" style="font-size: 9.5px; padding: 2px 5px;">Open Box OTP</span>`);
                }
                if (data.exchange_available) {
                    chips.push(`<span class="chip" style="font-size: 9.5px; padding: 2px 5px;">Exchange</span>`);
                }
                if (!chips.length) {
                    chips.push(`<span class="chip" style="font-size: 9.5px; padding: 2px 5px; color: #64748b;">Sealed Box</span>`);
                }
                return `<div style="display: flex; gap: 4px; align-items: center; height: 100%; flex-wrap: nowrap; overflow: hidden;">${chips.join('')}</div>`;
            }
        },
        // 7. Interactive PayPal Trigger
        {
            headerName: "Action",
            field: "action",
            pinned: "right",
            width: 140,
            minWidth: 130,
            cellRenderer: (params) => {
                const data = params.data;
                const disabled = !data.in_stock || data.is_dead_link;
                const btnText = disabled ? "Sold Out" : "Pay with PayPal";
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
                            data-title="${escapeHtml(data.product_title || '')}"
                            style="background: ${bg}; color: #ffffff; border: none; border-radius: 6px; padding: 5px 12px; font-size: 11px; font-weight: 700; cursor: ${cursor}; opacity: ${opacity}; white-space: nowrap;"
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
        autoSizeStrategy: {
            type: 'fitGridWidth'
        },
        onGridReady: (params) => {
            params.api.sizeColumnsToFit();
        }
    };

    // Global listener for embedded AG Grid buttons
    gridDiv.addEventListener('click', (e) => {
        const btn = e.target.closest('.ag-paypal-btn');
        if (btn && !btn.disabled) {
            const listingId = btn.getAttribute('data-listing-id');
            const merchant = btn.getAttribute('data-merchant');
            const price = btn.getAttribute('data-price');
            const title = btn.getAttribute('data-title') || '';
            handleGridCheckout(listingId, merchant, price, title);
        }
    });

    gridApi = agGrid.createGrid(gridDiv, gridOptions);

    window.addEventListener('resize', () => {
        if (gridApi) {
            try {
                gridApi.sizeColumnsToFit();
            } catch (_) {}
        }
    });

    return gridApi;
}

export function updateGridData(rows) {
    if (gridApi) {
        gridApi.setGridOption('rowData', rows || []);
        setTimeout(() => {
            try {
                gridApi.sizeColumnsToFit();
            } catch (_) {}
        }, 50);
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

async function handleGridCheckout(listingId, merchant, price, title) {
    openPayPalCheckoutModal(listingId, merchant, price, title);
}
