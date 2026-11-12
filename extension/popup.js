// ProductFind Sentinel Extension Popup Controller

function formatCurrency(amount, currency) {
  if (amount == null || !Number.isFinite(Number(amount))) return "--";
  const sym = currency === "INR" ? "₹" : "$";
  const locale = currency === "INR" ? "en-IN" : "en-US";
  return `${sym}${Math.round(Number(amount)).toLocaleString(locale)}`;
}

document.addEventListener("DOMContentLoaded", async () => {
  const titleEl = document.getElementById("detected-product-title");
  const merchEl = document.getElementById("detected-merchant");
  const currentPriceEl = document.getElementById("current-price");
  const sentinelPriceEl = document.getElementById("sentinel-price");
  const savingsEl = document.getElementById("deal-savings");
  const btnCockpit = document.getElementById("btn-open-cockpit");
  const btnTrack = document.getElementById("btn-track-price");

  let activeQuery = "";
  let activeCurrency = "INR";
  let activeBestPrice = 0;

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      if (tab.url.includes("amazon.in")) {
        merchEl.textContent = "Amazon.in Direct";
        activeCurrency = "INR";
      } else if (tab.url.includes("amazon.")) {
        merchEl.textContent = "Amazon Global";
        activeCurrency = "USD";
      } else if (tab.url.includes("flipkart.")) {
        merchEl.textContent = "Flipkart Marketplace";
        activeCurrency = "INR";
      } else if (tab.url.includes("bestbuy.")) {
        merchEl.textContent = "Best Buy US";
        activeCurrency = "USD";
      } else {
        merchEl.textContent = "Web Retailer";
      }

      chrome.tabs.sendMessage(tab.id, { action: "GET_PAGE_PRODUCT" }, (response) => {
        if (!response || !response.title) {
          titleEl.textContent = "Open any Amazon, Flipkart, or Best Buy product page to audit.";
          currentPriceEl.textContent = "--";
          sentinelPriceEl.textContent = "--";
          savingsEl.textContent = "Ready";
          return;
        }

        titleEl.textContent = response.title;
        activeQuery = response.title.split(/\s+/).slice(0, 7).join(" ");
        activeCurrency = response.currency || activeCurrency;
        currentPriceEl.textContent = response.price || "--";
        sentinelPriceEl.textContent = "Auditing...";
        savingsEl.textContent = "Scanning...";

        chrome.runtime.sendMessage(
          {
            action: "SENTINEL_AUDIT_PRODUCT",
            payload: {
              title: response.title,
              pagePrice: response.numericPrice,
              currency: activeCurrency,
              country: response.country,
              merchant: response.merchant,
            },
          },
          (audit) => {
            if (!audit || !audit.backend_online) {
              sentinelPriceEl.textContent = "Offline";
              savingsEl.textContent = "Start Sentinel Server";
              return;
            }
            if (audit.best_price) {
              activeBestPrice = audit.best_price;
              sentinelPriceEl.textContent = `${formatCurrency(audit.best_price, audit.currency)} (${audit.best_merchant})`;
            } else {
              sentinelPriceEl.textContent = "See Cockpit";
            }
            if (audit.savings_vs_page && audit.savings_vs_page > 0) {
              savingsEl.textContent = `-${formatCurrency(audit.savings_vs_page, audit.currency)} Saved`;
            } else if (audit.review_grade || audit.ifixit_score) {
              savingsEl.textContent = `${audit.review_grade || ""} · iFixit ${audit.ifixit_score || "-"}/10`.trim();
            } else {
              savingsEl.textContent = "Verified";
            }
          }
        );
      });
    }
  } catch (e) {
    titleEl.textContent = "Open a supported retailer tab to inspect deals.";
  }

  if (btnCockpit) {
    btnCockpit.addEventListener("click", () => {
      const target = activeQuery
        ? `http://127.0.0.1:8000/?q=${encodeURIComponent(activeQuery)}`
        : "http://127.0.0.1:8000/";
      chrome.tabs.create({ url: target });
    });
  }

  if (btnTrack) {
    btnTrack.addEventListener("click", async () => {
      const targetProduct = activeQuery || titleEl.textContent || "";
      if (!targetProduct || targetProduct.startsWith("Open ")) return;

      btnTrack.textContent = "✓ Alert Active";
      btnTrack.style.color = "#34d399";
      btnTrack.style.borderColor = "#10b981";

      const baseline = activeBestPrice > 0 ? activeBestPrice : 1000;
      try {
        await fetch("http://127.0.0.1:8000/api/alerts/subscribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product_title: targetProduct,
            target_price: Math.round(baseline * 0.94),
            current_price: Math.round(baseline),
            currency: activeCurrency,
            user_contact: "extension_user@sentinel.ai",
            channel: "browser",
          }),
        });
      } catch (err) {
        console.warn("Backend alert subscribe failed", err);
      }
    });
  }
});
