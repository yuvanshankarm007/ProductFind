// ProductFind Sentinel Content Script
// Inspects retailer DOM, queries Sentinel arbitration backend, and injects floating HUD pill.

(function () {
  function getProductDetails() {
    let title = "";
    let price = "";

    // Amazon
    const amzTitle = document.getElementById("productTitle");
    const amzPrice = document.querySelector(".a-price .a-offscreen") || document.querySelector("#priceblock_ourprice");
    if (amzTitle) {
      title = amzTitle.textContent.trim();
      price = amzPrice ? amzPrice.textContent.trim() : "";
    }

    // Flipkart
    const fkTitle = document.querySelector(".B_NuCI") || document.querySelector("span.VU-ZEz");
    const fkPrice = document.querySelector("._30jeq3._16Jk6d") || document.querySelector(".Nx9daj");
    if (fkTitle) {
      title = fkTitle.textContent.trim();
      price = fkPrice ? fkPrice.textContent.trim() : "";
    }

    return { title, price };
  }

  // Listen for messages from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "GET_PAGE_PRODUCT") {
      const details = getProductDetails();
      sendResponse(details);
    }
  });

  // Inject floating Sentinel pill on product page
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
          <div class="sentinel-savings">Arbitrating deals... Save up to ₹3,400 via OEM Direct</div>
        </div>
        <button id="sentinel-cta-btn" class="sentinel-cta">View Deals</button>
        <span id="sentinel-close-badge" class="sentinel-close">&times;</span>
      </div>
    `;

    document.body.appendChild(pill);

    document.getElementById("sentinel-cta-btn")?.addEventListener("click", () => {
      window.open(`http://127.0.0.1:8000/?q=${encodeURIComponent(details.title.slice(0, 45))}`, "_blank");
    });

    document.getElementById("sentinel-close-badge")?.addEventListener("click", () => {
      pill.remove();
    });
  }

  setTimeout(injectSentinelFloatingPill, 1200);
})();
