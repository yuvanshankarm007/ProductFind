// ProductFind Sentinel Extension Background Service Worker
// Routes content/popup arbitration requests cleanly to the Sentinel backend API without page CORS blocks.

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

async function getApiBase() {
  try {
    const res = await chrome.storage.local.get(["sentinelBaseUrl"]);
    return (res.sentinelBaseUrl || DEFAULT_API_BASE).replace(/\/+$/, "");
  } catch {
    return DEFAULT_API_BASE;
  }
}

async function fetchJsonSafe(url, timeoutMs = 4500) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { signal: ctrl.signal });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  } finally {
    clearTimeout(id);
  }
}

async function auditProductWithBackend({ title, pagePrice, currency, country, merchant }) {
  const base = await getApiBase();
  const shortQuery = String(title || "").trim().split(/\s+/).slice(0, 7).join(" ");
  if (!shortQuery) return { backend_online: false };

  const cur = currency || (country === "IN" ? "INR" : "USD");
  const ctry = country || (cur === "INR" ? "IN" : "US");

  const [searchData, reviewData, biflData] = await Promise.all([
    fetchJsonSafe(`${base}/api/search?q=${encodeURIComponent(shortQuery)}&currency=${encodeURIComponent(cur)}&country=${encodeURIComponent(ctry)}`, 6500),
    fetchJsonSafe(`${base}/api/review-audit?q=${encodeURIComponent(shortQuery)}&store=${encodeURIComponent(merchant || "Amazon")}`, 3500),
    fetchJsonSafe(`${base}/api/bifl-score?q=${encodeURIComponent(shortQuery)}`, 3500),
  ]);

  if (!searchData && !reviewData && !biflData) {
    return { backend_online: false, query: shortQuery, api_base: base };
  }

  const options = (searchData && (searchData.final_options || searchData.deals)) || [];
  const winner = options[0] || null;
  const bestPrice = winner
    ? Number(winner.converted_cash_outlay || winner.total_cash_outlay || 0)
    : null;
  const bestMerchant = winner?.listing?.merchant || merchant || "Best Verified Channel";

  let savingsVsPage = null;
  if (bestPrice && pagePrice && Number(pagePrice) > bestPrice) {
    savingsVsPage = Number((Number(pagePrice) - bestPrice).toFixed(2));
  }

  return {
    backend_online: true,
    api_base: base,
    query: shortQuery,
    currency: cur,
    best_merchant: bestMerchant,
    best_price: bestPrice,
    savings_vs_page: savingsVsPage,
    winner_url: winner?.listing?.listing_url || `${base}/?q=${encodeURIComponent(shortQuery)}`,
    review_grade: reviewData?.letter_grade || null,
    adjusted_rating: reviewData?.adjusted_honest_rating || null,
    ifixit_score: biflData?.ifixit_score || null,
  };
}

chrome.runtime.onInstalled.addListener(() => {
  console.log("[Sentinel Extension] Live Arbitrage Service Worker installed.");
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request?.action === "SENTINEL_AUDIT_PRODUCT") {
    auditProductWithBackend(request.payload || {})
      .then((res) => sendResponse(res))
      .catch(() => sendResponse({ backend_online: false }));
    return true; // keep channel open for async response
  }
});
