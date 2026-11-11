/**
 * Price Trajectory Chart & Sparkline Generator — Animated Gradient SVG Edition.
 * Features smooth bezier curves, animated gradient fills, ATL/ATH markers,
 * momentum indicator, pulsing live-price dot, and inline sparklines for deal cards.
 */

import { escapeHtml } from './security.js';

export function renderPriceTrajectory(analytics, containerId) {
    const container = document.getElementById(containerId);
    if (!container || !analytics) return;

    const points = analytics.history_points || [];
    if (!points.length) {
        container.innerHTML = `<div style="color:#94a3b8;font-size:12px;padding:1rem;text-align:center;">No price trajectory data available.</div>`;
        return;
    }

    const prices = points.map(p => p.price);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const range = (maxP - minP) || 1.0;

    const W = 600, H = 160, PX = 44, PY = 24;
    const uid = `chart_${Math.random().toString(36).slice(2, 8)}`;
    const step = (W - PX * 2) / Math.max(points.length - 1, 1);

    const coords = points.map((p, i) => {
        const x = Math.round((PX + i * step) * 10) / 10;
        const y = Math.round((H - PY - ((p.price - minP) / range) * (H - PY * 2)) * 10) / 10;
        return { x, y, price: p.price, date: p.date || '', label: p.event_label || '' };
    });

    // Smooth bezier cubic path
    function bezierPath(pts) {
        if (pts.length < 2) return pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
        let d = `M${pts[0].x},${pts[0].y}`;
        for (let i = 1; i < pts.length; i++) {
            const prev = pts[i - 1], cur = pts[i];
            const cpx = (prev.x + cur.x) / 2;
            d += ` C${cpx},${prev.y} ${cpx},${cur.y} ${cur.x},${cur.y}`;
        }
        return d;
    }

    const pathD = bezierPath(coords);
    const areaD = pathD + ` L${coords[coords.length - 1].x},${H - PY} L${coords[0].x},${H - PY} Z`;

    const atlIdx = prices.indexOf(minP);
    const athIdx = prices.indexOf(maxP);
    const latestIdx = coords.length - 1;

    const curr = analytics.target_currency || 'INR';
    const verdict = analytics.buy_verdict || 'FAIR VALUE';
    const verdictColor = verdict === 'BUY NOW' ? '#34d399' : verdict === 'WAIT' ? '#f59e0b' : '#38bdf8';

    // Grid price labels
    const gridLines = [0, 0.25, 0.5, 0.75, 1].map(f => {
        const gy = PY + f * (H - PY * 2);
        const price = maxP - f * range;
        return `<line x1="${PX}" y1="${gy.toFixed(1)}" x2="${W - PX}" y2="${gy.toFixed(1)}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4 4"/>
                <text x="${PX - 5}" y="${(gy + 3).toFixed(1)}" fill="#475569" font-size="8" text-anchor="end" font-family="monospace">${price >= 1000 ? (price / 1000).toFixed(0) + 'k' : Math.round(price)}</text>`;
    }).join('');

    // Date labels (sparse)
    const step2 = Math.max(1, Math.floor(coords.length / 4));
    const dateLabels = coords.filter((_, i) => i % step2 === 0 || i === coords.length - 1).map(c =>
        `<text x="${c.x}" y="${H - 5}" fill="#475569" font-size="8" text-anchor="middle" font-family="monospace">${escapeHtml(c.date.substring(0, 6))}</text>`
    ).join('');

    const svg = `<svg id="${uid}" viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;overflow:visible;" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="${uid}_grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${verdictColor}" stop-opacity="0.32"/>
      <stop offset="100%" stop-color="${verdictColor}" stop-opacity="0.03"/>
    </linearGradient>
    <filter id="${uid}_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="${uid}_clip">
      <rect x="${PX}" y="${PY - 2}" width="${W - PX * 2}" height="${H - PY * 2 + 4}"/>
    </clipPath>
  </defs>

  ${gridLines}

  <path d="${areaD}" fill="url(#${uid}_grad)" clip-path="url(#${uid}_clip)"/>
  <path d="${pathD}" fill="none" stroke="${verdictColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#${uid}_glow)" clip-path="url(#${uid}_clip)"/>

  ${atlIdx >= 0 ? `
  <line x1="${coords[atlIdx].x}" y1="${coords[atlIdx].y}" x2="${coords[atlIdx].x}" y2="${H - PY}" stroke="#34d399" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>
  <circle cx="${coords[atlIdx].x}" cy="${coords[atlIdx].y}" r="6" fill="#34d399" stroke="#0f172a" stroke-width="2"/>
  <text x="${coords[atlIdx].x}" y="${coords[atlIdx].y - 10}" fill="#34d399" font-size="9" text-anchor="middle" font-weight="bold" font-family="monospace">ATL</text>` : ''}

  ${athIdx >= 0 && athIdx !== atlIdx ? `
  <line x1="${coords[athIdx].x}" y1="${coords[athIdx].y}" x2="${coords[athIdx].x}" y2="${H - PY}" stroke="#f43f5e" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>
  <circle cx="${coords[athIdx].x}" cy="${coords[athIdx].y}" r="6" fill="#f43f5e" stroke="#0f172a" stroke-width="2"/>
  <text x="${coords[athIdx].x}" y="${coords[athIdx].y - 10}" fill="#f43f5e" font-size="9" text-anchor="middle" font-weight="bold" font-family="monospace">ATH</text>` : ''}

  ${coords.map(c => `<circle cx="${c.x}" cy="${c.y}" r="3" fill="${verdictColor}" stroke="#0f172a" stroke-width="1.5" opacity="0.85"><title>${escapeHtml(c.date)}: ${curr} ${c.price.toLocaleString()}</title></circle>`).join('')}

  <circle cx="${coords[latestIdx].x}" cy="${coords[latestIdx].y}" r="5" fill="${verdictColor}" stroke="#0f172a" stroke-width="2">
    <animate attributeName="r" values="5;9;5" dur="2s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <circle cx="${coords[latestIdx].x}" cy="${coords[latestIdx].y}" r="4.5" fill="${verdictColor}" stroke="#0f172a" stroke-width="2"/>

  ${dateLabels}
</svg>`;

    const atl = analytics.all_time_low ? `${curr} ${Number(analytics.all_time_low).toLocaleString()}` : 'N/A';
    const ath = analytics.all_time_high ? `${curr} ${Number(analytics.all_time_high).toLocaleString()}` : 'N/A';
    const avg = analytics.avg_90d_price ? `${curr} ${Number(analytics.avg_90d_price).toLocaleString()}` : 'N/A';
    const confidence = analytics.prediction_confidence || 85;

    const firstP = prices[0], lastP = prices[prices.length - 1];
    const momentum = lastP < firstP ? '📉' : lastP > firstP ? '📈' : '➡️';
    const momentumPct = firstP ? (((lastP - firstP) / firstP) * 100).toFixed(1) : '0.0';
    const momentumColor = lastP < firstP ? '#34d399' : lastP > firstP ? '#f43f5e' : '#94a3b8';

    container.innerHTML = `
<div style="display:flex;flex-direction:column;gap:14px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
    <div style="display:flex;gap:18px;flex-wrap:wrap;">
      <div>
        <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">All-Time Low</div>
        <div style="font-size:14px;font-weight:800;color:#34d399;font-family:monospace;">${atl}</div>
      </div>
      <div>
        <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">90-Day Avg</div>
        <div style="font-size:14px;font-weight:800;color:#60a5fa;font-family:monospace;">${avg}</div>
      </div>
      <div>
        <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">All-Time High</div>
        <div style="font-size:14px;font-weight:800;color:#f43f5e;font-family:monospace;">${ath}</div>
      </div>
      <div>
        <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Momentum</div>
        <div style="font-size:14px;font-weight:800;color:${momentumColor};font-family:monospace;">${momentum} ${momentumPct}%</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <span style="background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.35);color:${verdictColor};font-size:11px;font-weight:800;padding:4px 12px;border-radius:9999px;">VERDICT: ${escapeHtml(verdict)}</span>
      <span style="font-size:10px;color:#64748b;">${confidence}% confidence</span>
    </div>
  </div>
  <div style="background:rgba(11,15,25,0.6);border:1px solid #1e293b;border-radius:10px;padding:14px;position:relative;">
    ${svg}
  </div>
  ${analytics.prediction_explanation ? `<div style="font-size:11.5px;color:#94a3b8;line-height:1.5;padding:8px 12px;background:rgba(56,189,248,0.04);border-left:2px solid rgba(56,189,248,0.3);border-radius:4px;">${escapeHtml(analytics.prediction_explanation)}</div>` : ''}
</div>`;
}

/**
 * Render a compact inline sparkline for deal cards (pure SVG string).
 */
export function renderSparkline(prices, width = 80, height = 28) {
    if (!prices || prices.length < 2) return '';
    const minP = Math.min(...prices), maxP = Math.max(...prices);
    const range = (maxP - minP) || 1;
    const sx = width / (prices.length - 1);
    const coords = prices.map((p, i) => `${(i * sx).toFixed(1)},${((1 - (p - minP) / range) * (height - 4) + 2).toFixed(1)}`);
    const trendDown = prices[prices.length - 1] < prices[0];
    const color = trendDown ? '#34d399' : '#f43f5e';
    const lx = coords[coords.length - 1].split(',');
    return `<svg viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" style="display:inline-block;vertical-align:middle;"><polyline points="${coords.join(' ')}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${lx[0]}" cy="${lx[1]}" r="2.5" fill="${color}"/></svg>`;
}
