/**
 * Price Trajectory Chart & Sparkline Generator.
 * Uses high-precision rounded SVG coordinates to eliminate floating-point string parsing overhead.
 */

import { escapeHtml } from './security.js';

export function renderPriceTrajectory(analytics, containerId) {
    const container = document.getElementById(containerId);
    if (!container || !analytics) return;

    const points = analytics.history_points || [];
    if (!points.length) {
        container.innerHTML = `<div style="color: #94a3b8; font-size: 12px; padding: 1rem;">No price trajectory data available.</div>`;
        return;
    }

    const prices = points.map(p => p.price);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const range = (maxP - minP) || 1.0;

    const width = 600;
    const height = 140;
    const paddingX = 40;
    const paddingY = 20;

    const step = (width - paddingX * 2) / (points.length - 1);

    // Calculate rounded SVG coordinates
    const coords = points.map((p, i) => {
        const x = Math.round((paddingX + i * step) * 10) / 10;
        const y = Math.round((height - paddingY - ((p.price - minP) / range) * (height - paddingY * 2)) * 10) / 10;
        return { x, y, price: p.price, date: p.date, label: p.event_label };
    });

    const pathData = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ');

    const svg = `
        <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; overflow: visible;">
            <!-- Grid Lines -->
            <line x1="${paddingX}" y1="${paddingY}" x2="${width - paddingX}" y2="${paddingY}" stroke="#1e293b" stroke-dasharray="3 3"/>
            <line x1="${paddingX}" y1="${height - paddingY}" x2="${width - paddingX}" y2="${height - paddingY}" stroke="#1e293b" stroke-dasharray="3 3"/>
            
            <!-- Price Trajectory Line -->
            <path d="${pathData}" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>

            <!-- Points & Labels -->
            ${coords.map(c => `
                <circle cx="${c.x}" cy="${c.y}" r="4" fill="#3b82f6" stroke="#0b0f19" stroke-width="2"/>
                <text x="${c.x}" y="${height - 4}" fill="#64748b" font-size="10" text-anchor="middle" font-family="monospace">${escapeHtml(c.date)}</text>
            `).join('')}
        </svg>
    `;

    const curr = escapeHtml(analytics.target_currency || 'USD');
    const atl = analytics.all_time_low ? `${curr} ${analytics.all_time_low.toLocaleString()}` : 'N/A';
    const ath = analytics.all_time_high ? `${curr} ${analytics.all_time_high.toLocaleString()}` : 'N/A';
    const avg = analytics.avg_90d_price ? `${curr} ${analytics.avg_90d_price.toLocaleString()}` : 'N/A';
    const verdict = escapeHtml(analytics.buy_verdict || 'FAIR VALUE');
    const confidence = analytics.prediction_confidence || 85;

    container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; gap: 12px;">
                    <div>
                        <div style="font-size: 10px; color: #64748b; text-transform: uppercase;">All-Time Low</div>
                        <div style="font-size: 13px; font-weight: 700; color: #34d399;" class="mono-font">${atl}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: #64748b; text-transform: uppercase;">90-Day Average</div>
                        <div style="font-size: 13px; font-weight: 700; color: #60a5fa;" class="mono-font">${avg}</div>
                    </div>
                    <div>
                        <div style="font-size: 10px; color: #64748b; text-transform: uppercase;">All-Time High</div>
                        <div style="font-size: 13px; font-weight: 700; color: #f43f5e;" class="mono-font">${ath}</div>
                    </div>
                </div>

                <div style="display: flex; align-items: center; gap: 6px;">
                    <span class="hud-status-badge status-optimal">VERDICT: ${verdict}</span>
                    <span style="font-size: 11px; color: #94a3b8;">(${confidence}% confidence)</span>
                </div>
            </div>

            <div style="background: rgba(11, 15, 25, 0.5); border: 1px solid #1e293b; border-radius: 8px; padding: 12px;">
                ${svg}
            </div>

            ${analytics.prediction_explanation ? `
                <div style="font-size: 12px; color: #94a3b8; line-height: 1.4;">
                    ${escapeHtml(analytics.prediction_explanation)}
                </div>
            ` : ''}
        </div>
    `;
}
