// ProductFind Sentinel Content Script
// Inspects Amazon/Flipkart/BestBuy DOM, queries live Sentinel backend via background worker,
// and injects real arbitration + ReviewGrade + iFixit HUD pill.

(function () {
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

  function getProductDetails() {
    let title = "";
    let priceText = "";
    const ctx = detectSiteContext();

    // Amazon
    const amzTitle = document.getElementById("productTitle");
    const amzPrice =
      document.querySelector(".a-price .a-offscreen") ||
      document.querySelector("#priceblock_ourprice") ||
      document.querySelector("#corePriceDisplay_desktop_feature_div .a-price-whole");
    if (amzTitle) {
      title = amzTitle.textContent.trim();
      priceText = amzPrice ? amzPrice.textContent.trim() : "";
    }

    // Flipkart
    const fkTitle = document.querySelector(".B_NuCI") || document.querySelector("span.VU-ZEz");
    const fkPrice = document.querySelector("._30jeq3._16Jk6d") || document.querySelector(".Nx9daj");
    if (!title && fkTitle) {
      title = fkTitle.textContent.trim();
      priceText = fkPrice ? fkPrice.textContent.trim() : "";
    }

    // Best Buy
    const bbTitle = document.querySelector(".sku-title h1") || document.querySelector("h1.heading-5");
    const bbPrice = document.querySelector("[data-testid='customer-price'] span") || document.querySelector(".priceView-customer-price span");
    if (!title && bbTitle) {
      title = bbTitle.textContent.trim();
      priceText = bbPrice ? bbPrice.textContent.trim() : "";
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
    if (document.getElementById("sentinel-floating-pill")) return;

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

  setTimeout(injectSentinelFloatingPill, 1200);
})();
