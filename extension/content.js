// ProductFind Sentinel Content Script
// Inspects Amazon/Flipkart/BestBuy DOM (including modern Flipkart classes, JSON-LD,
// search queries, and SPA navigation), queries live Sentinel backend via background worker,
// and injects the real arbitration + ReviewGrade + iFixit HUD pill.

(function () {
  let lastAuditedKey = "";

  function detectSiteContext() {
    const host = window.location.hostname.toLowerCase();
    if (host.includes("amazon.in")) return { merchant: "Amazon.in", currency: "INR", country: "IN" };
    if (host.includes("amazon.")) return { merchant: "Amazon", currency: "USD", country: "US" };
    if (host.includes("flipkart.")) return { merchant: "Flipkart", currency: "INR", country: "IN" };
    if (host.includes("bestbuy.")) return { merchant: "Best Buy", currency: "USD", country: "US" };
    return { merchant: "Retailer", currency: "USD", country: "US" };
  }

  function parseNumericPrice(raw) {
    if (!raw) return null;
    const cleaned = String(raw).replace(/[^0-9.]/g, "");
    const val = parseFloat(cleaned);
    return Number.isFinite(val) && val > 0 ? val : null;
  }

  function extractJsonLdProduct() {
    try {
      const scripts = document.querySelectorAll('script[type="application/ld+json"]');
      for (const s of scripts) {
        const parsed = JSON.parse(s.textContent || "null");
        const nodes = Array.isArray(parsed) ? parsed : [parsed];
        for (const node of nodes) {
          if (!node) continue;
          const t = String(node["@type"] || "").toLowerCase();
          if (t.includes("product") && node.name) {
            const offer = Array.isArray(node.offers) ? node.offers[0] : node.offers;
            const p = offer && (offer.price || offer.lowPrice);
            return { title: String(node.name).trim(), price: p ? String(p) : "" };
          }
        }
      }
    } catch {
      // Ignore malformed JSON-LD blocks
    }
    return null;
  }

  function cleanTitleText(raw) {
    return String(raw || "")
      .replace(/\s+/g, " ")
      .replace(/Online at Best Price.*$/i, "")
      .replace(/Buy .*? Online.*$/i, "")
      .trim();
  }

  function getProductDetails() {
    let title = "";
    let priceText = "";
    const ctx = detectSiteContext();
    const params = new URLSearchParams(window.location.search);

    // 1. Amazon product page selectors
    const amzTitle =
      document.getElementById("productTitle") ||
      document.querySelector("#title span");
    const amzPrice =
      document.querySelector(".a-price .a-offscreen") ||
      document.querySelector("#priceblock_ourprice") ||
      document.querySelector("#corePriceDisplay_desktop_feature_div .a-price-whole") ||
      document.querySelector(".apexPriceToPay .a-offscreen");
    if (amzTitle && amzTitle.textContent.trim()) {
      title = cleanTitleText(amzTitle.textContent);
      priceText = amzPrice ? amzPrice.textContent.trim() : "";
    }

    // 2. Flipkart product page selectors (modern + legacy classes)
    if (!title && ctx.merchant === "Flipkart") {
      const fkTitle =
        document.querySelector("span.VU-ZEz") ||
        document.querySelector("h1.VU-ZEz") ||
        document.querySelector("h1._6EBuvT") ||
        document.querySelector(".B_NuCI") ||
        document.querySelector("h1 span");
      const fkPrice =
        document.querySelector("div.Nx9bqj.CxhGGd") ||
        document.querySelector(".Nx9bqj") ||
        document.querySelector(".Nx9daj") ||
        document.querySelector("._30jeq3._16Jk6d") ||
        document.querySelector("._30jeq3");
      if (fkTitle && fkTitle.textContent.trim()) {
        title = cleanTitleText(fkTitle.textContent);
        priceText = fkPrice ? fkPrice.textContent.trim() : "";
      }
    }

    // 3. Best Buy product page selectors
    if (!title && ctx.merchant === "Best Buy") {
      const bbTitle =
        document.querySelector(".sku-title h1") ||
        document.querySelector("h1.heading-5") ||
        document.querySelector("h1");
      const bbPrice =
        document.querySelector("[data-testid='customer-price'] span") ||
        document.querySelector(".priceView-customer-price span");
      if (bbTitle && bbTitle.textContent.trim()) {
        title = cleanTitleText(bbTitle.textContent);
        priceText = bbPrice ? bbPrice.textContent.trim() : "";
      }
    }

    // 4. Schema.org JSON-LD fallback
    if (!title) {
      const ld = extractJsonLdProduct();
      if (ld && ld.title) {
        title = cleanTitleText(ld.title);
        if (!priceText && ld.price) priceText = ld.price;
      }
    }

    // 5. Search results page fallback (?k=... on Amazon, ?q=... on Flipkart, ?st=... on Best Buy)
    if (!title) {
      const searchInput =
        document.getElementById("twotabsearchtextbox") ||
        document.querySelector('input[name="q"]') ||
        document.querySelector('input[name="k"]') ||
        document.querySelector("#gh-search-input");
      const urlQuery = params.get("k") || params.get("q") || params.get("st") || "";
      const candidate = (searchInput && searchInput.value ? searchInput.value : urlQuery).trim();
      if (candidate.length >= 2) {
        title = candidate;
      }
    }

    return {
      title,
      price: priceText,
      numericPrice: parseNumericPrice(priceText),
      currency: ctx.currency,
      country: ctx.country,
      merchant: ctx.merchant,
    };
  }

  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "GET_PAGE_PRODUCT") {
      sendResponse(getProductDetails());
    }
  });

  function formatMoney(amount, currency) {
    if (amount == null) return "N/A";
    const symbol = currency === "INR" ? "₹" : "$";
    const locale = currency === "INR" ? "en-IN" : "en-US";
    return `${symbol}${Math.round(amount).toLocaleString(locale)}`;
  }

  function injectSentinelFloatingPill() {
    const details = getProductDetails();
    if (!details.title) return;

    const auditKey = `${window.location.href}::${details.title.slice(0, 60)}`;
    const existing = document.getElementById("sentinel-floating-pill");
    if (existing && lastAuditedKey === auditKey) return;
    if (existing) existing.remove();

    lastAuditedKey = auditKey;

    const pill = document.createElement("div");
    pill.id = "sentinel-floating-pill";
    pill.className = "sentinel-injected-badge";
    pill.innerHTML = `
      <div class="sentinel-badge-inner">
        <span class="sentinel-logo">🛡️</span>
        <div class="sentinel-info">
          <div class="sentinel-title">ProductFind <strong>Sentinel</strong></div>
          <div id="sentinel-live-status" class="sentinel-savings">Scanning multi-retailer TCO, reviews &amp; iFixit...</div>
        </div>
        <button id="sentinel-cta-btn" class="sentinel-cta">Compare</button>
        <span id="sentinel-close-badge" class="sentinel-close">&times;</span>
      </div>
    `;
    document.body.appendChild(pill);

    let targetUrl = `http://127.0.0.1:8000/?q=${encodeURIComponent(details.title.slice(0, 50))}`;
    document.getElementById("sentinel-cta-btn")?.addEventListener("click", () => {
      window.open(targetUrl, "_blank");
    });
    document.getElementById("sentinel-close-badge")?.addEventListener("click", () => {
      pill.remove();
    });

    chrome.runtime.sendMessage(
      {
        action: "SENTINEL_AUDIT_PRODUCT",
        payload: {
          title: details.title,
          pagePrice: details.numericPrice,
          currency: details.currency,
          country: details.country,
          merchant: details.merchant,
        },
      },
      (res) => {
        const statusEl = document.getElementById("sentinel-live-status");
        if (!statusEl) return;
        if (!res || !res.backend_online) {
          statusEl.textContent = "Click Compare to launch local Sentinel Cockpit audit";
          return;
        }
        targetUrl = `${res.api_base || "http://127.0.0.1:8000"}/?q=${encodeURIComponent(res.query || details.title.slice(0, 50))}`;
        const parts = [];
        if (res.savings_vs_page && res.savings_vs_page > 0) {
          parts.push(`Save ${formatMoney(res.savings_vs_page, res.currency)} on ${res.best_merchant}`);
        } else if (res.best_price) {
          parts.push(`Best TCO ${formatMoney(res.best_price, res.currency)} (${res.best_merchant})`);
        }
        if (res.review_grade) parts.push(`Reviews ${res.review_grade}`);
        if (res.ifixit_score) parts.push(`iFixit ${res.ifixit_score}/10`);
        statusEl.textContent = parts.join(" · ") || "Verified deal audit ready";
      }
    );
  }

  // Initial + delayed hydration checks + SPA URL transition watcher
  setTimeout(injectSentinelFloatingPill, 900);
  setTimeout(injectSentinelFloatingPill, 2600);
  let lastUrl = window.location.href;
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      setTimeout(injectSentinelFloatingPill, 900);
    }
  }, 1000);
})();
