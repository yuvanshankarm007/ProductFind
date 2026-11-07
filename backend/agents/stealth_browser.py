"""
External Stealth Bot Browser & Multi-Engine Retail Search.
Inspired by open-source browser automation architectures on GitHub (Browser-Use, Crawl4AI, ScrapeGraphAI).
Provides resilient, anti-detection headless Chromium browsing and multi-engine retail discovery
to extract authentic product titles, prices, stock statuses, and verified 200 OK direct product URLs.
"""

import asyncio
import concurrent.futures
import re
import urllib.parse
import warnings
from typing import List, Dict, Any, Optional
from curl_cffi import requests as curl_requests

warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*renamed to.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*")

_DDGS_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="ddgs_scout")

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class ExternalStealthBotBrowser:
    """
    Autonomous Bot Browser that bypasses bot-detection (Cloudflare, Akamai, PerimeterX)
    using Playwright headless Chromium + curl_cffi TLS impersonation + multi-engine open-web search.
    """

    STEALTH_CHROMIUM_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--no-first-run",
        "--no-zygote",
        "--disable-gpu",
        "--hide-scrollbars",
        "--mute-audio",
    ]

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    @classmethod
    async def search_retail_products(
        cls,
        query: str,
        dest_country: str = "IN",
        max_results: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Executes stealth open-web product discovery across major retail domains (Flipkart, Amazon, Croma, Reliance Digital, etc.)
        using DDGS / primp Chrome TLS impersonation to avoid bot-blocking.
        """
        results: List[Dict[str, Any]] = []
        if not HAS_DDGS:
            return results

        dest = dest_country.upper()
        if dest == "IN":
            search_query = f"{query} buy online price in india"
        else:
            search_query = f"{query} buy online price"

        q_lower = query.lower()
        has_acc_intent = any(k in q_lower for k in [
            'case', 'cover', 'cushion', 'pad', 'cable', 'adapter', 'strap', 'guard', 'skin',
            'hinge', 'roller', 'brush', 'filter', 'attachment', 'head', 'part', 'parts',
            'spare', 'replacement', 'dock', 'charger', 'mount', 'wand', 'nozzle', 'battery',
            'ink', 'toner', 'bottle', 'refill', 'cartridge', 'ribbon', 'paper', 'printhead',
            'sleeve', 'bag', 'backpack', 'stand', 'mousepad', 'keycap', 'keycaps', 'switch',
            'switches', 'cleaning kit'
        ])
        accessory_stop_words = [
            'brush roller', 'roller brush', 'cleaner head', 'roller', 'attachment', 'wand',
            'nozzle', 'crevice tool', 'motorhead', 'hepa filter', 'filter replacement', 'dustbin',
            'replacement pad', 'ear pad', 'ear tips', 'silicone case', 'tempered glass',
            'charging cable', 'replacement battery', 'housing shell', 'trackpad replacement',
            'keyboard replacement', 'spare part', 'repair kit', 'docking station', 'mop head',
            'accessories kit', 'cleaning head', 'fluffy head',
            'ink bottle', 'ink bottles', 'refill ink', 'toner cartridge', 'ink cartridge', 'toner',
            'bottle', 'bottles', 'refill', 'refills', 'cartridge', 'cartridges', 'ribbon', 'printhead',
            'pump assembly', 'photo paper', 'glossy paper', 'sublimation ink', 'maintenance box',
            'cleaning kit', 'mount bracket', 'wall bracket', 'monitor arm', 'monitor stand', 'vesa mount',
            'mousepad', 'mouse pad', 'desk mat', 'wrist rest', 'cooling pad', 'keyboard cover'
        ]

        def _sync_ddgs():
            items = []
            try:
                with DDGS(timeout=3.0) as ddgs:
                    raw_res = list(ddgs.text(search_query, max_results=max_results * 2))
                    for r in raw_res:
                        href = r.get("href", "")
                        title = r.get("title", "")
                        body = r.get("body", "")

                        parsed = urllib.parse.urlparse(href)
                        domain = parsed.netloc.lower().replace("www.", "")

                        # Filter non-retail or dead patterns
                        if any(bad in href for bad in ["/search", "/s?k=", "search?", "searchpage", "results?"]):
                            continue
                        if any(ign in domain for ign in ["wikipedia.org", "youtube.com", "reddit.com", "quora.com", "facebook.com"]):
                            continue

                        # Filter accessories unless query has explicit accessory intent
                        t_low = title.lower()
                        if not has_acc_intent and any(w in t_low for w in accessory_stop_words):
                            continue

                        # Filter hardware spec cross-line bleed (e.g. MacBook Air on MacBook Pro / Max search)
                        if any(k in q_lower for k in ["max", "pro", "64gb", "32gb"]) and "air" in t_low:
                            continue
                        for chip in ["m1", "m2", "m3", "m4", "m5", "m6"]:
                            if chip in q_lower:
                                conflicting = [c for c in ["m1", "m2", "m3", "m4", "m5", "m6"] if c != chip]
                                if any(re.search(r'\b' + re.escape(c) + r'\b', t_low) for c in conflicting) and not re.search(r'\b' + re.escape(chip) + r'\b', t_low):
                                    continue

                        # Extract price if present in body or title with currency conversion to dest_country
                        combined_text = f"{title} {body}"
                        price_match = re.search(r'(₹|Rs\.?|INR|\$)\s*([0-9,]+(?:\.[0-9]+)?)', combined_text)
                        price = None
                        if price_match:
                            try:
                                curr_marker = price_match.group(1).lower()
                                raw_val = float(price_match.group(2).replace(",", ""))
                                is_inr = any(s in curr_marker for s in ["₹", "rs", "inr"])
                                if dest_country in ["US", "CA", "GB", "DE"] and is_inr:
                                    raw_val = round(raw_val / 86.8, 2)
                                elif dest_country == "IN" and not is_inr:
                                    raw_val = round(raw_val * 86.8, 2)
                                price = raw_val
                            except Exception:
                                price = None

                        items.append({
                            "title": title,
                            "url": href,
                            "domain": domain,
                            "price": price,
                            "snippet": body,
                            "merchant": domain.split(".")[0].capitalize(),
                            "is_direct_product": any(marker in href for marker in ["/p/", "/dp/", "/ip/", "/product/", "/itm", ".html"]),
                        })
            except Exception:
                pass
            return items

        try:
            loop = asyncio.get_event_loop()
            results = await asyncio.wait_for(loop.run_in_executor(_DDGS_EXECUTOR, _sync_ddgs), timeout=2.5)
        except Exception:
            pass

        return results

    @classmethod
    async def verify_url_live(cls, url: str, timeout: float = 4.0) -> Dict[str, Any]:
        """
        Actively verifies that a candidate product detail URL returns 200 OK and is NOT a 404 dog page,
        E002 error, or expired listing.
        """
        if not url:
            return {"is_valid": False, "status_code": 0, "reason": "Empty URL"}

        # Fast path with curl_cffi Chrome impersonation
        try:
            loop = asyncio.get_event_loop()
            def _check():
                resp = curl_requests.get(
                    url,
                    impersonate="chrome124",
                    headers={
                        "User-Agent": cls.USER_AGENT,
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9"
                    },
                    timeout=timeout,
                    allow_redirects=True
                )
                text = resp.text or ""
                code = resp.status_code

                # Check for known e-commerce failure signatures
                is_amazon_dog = "Looking for something? We're sorry" in text or "Dogs of Amazon" in text
                is_flipkart_e002 = "Something went wrong! Please try again later. E002" in text or "E002" in text
                is_croma_404 = "404 Error page not found" in text or "404 Error" in text

                is_healthy = (code == 200) and not (is_amazon_dog or is_flipkart_e002 or is_croma_404)
                fail_reason = ""
                if code in (404, 410, 500):
                    fail_reason = f"HTTP {code}"
                elif is_amazon_dog:
                    fail_reason = "Amazon 404 Dog Page"
                elif is_flipkart_e002:
                    fail_reason = "Flipkart E002 Error"
                elif is_croma_404:
                    fail_reason = "Croma 404 Error"

                return {
                    "is_valid": is_healthy,
                    "status_code": code,
                    "reason": fail_reason,
                    "text_snippet": text[:200]
                }

            return await loop.run_in_executor(None, _check)

        except Exception as e:
            return {"is_valid": False, "status_code": 0, "reason": str(e)}

    @classmethod
    async def scrape_product_with_browser(cls, url: str, timeout_ms: int = 15000) -> Dict[str, Any]:
        """
        Uses real Playwright headless Chromium browser to execute JavaScript, bypass bot detection,
        and extract live DOM properties (product title, price, in-stock status).
        """
        if not HAS_PLAYWRIGHT:
            return {"success": False, "error": "Playwright not installed"}

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=cls.STEALTH_CHROMIUM_ARGS
                )
                context = await browser.new_context(
                    user_agent=cls.USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US"
                )
                page = await context.new_page()

                # Anti-detection stealth script injection
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {} };
                """)

                response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                status = response.status if response else 0

                title = await page.title()

                # Extract JSON-LD product data if available
                json_ld_data = await page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const s of scripts) {
                        try {
                            const d = JSON.parse(s.innerText);
                            if (d['@type'] === 'Product' || d.offers) {
                                return d;
                            }
                        } catch(e) {}
                    }
                    return null;
                }""")

                # DOM price extraction fallback
                dom_price_text = await page.evaluate("""() => {
                    const priceSelectors = [
                        '.a-price .a-offscreen',
                        '.a-price-whole',
                        '._30jeq3', // Flipkart
                        '.amount',
                        '.pdp-price',
                        'span[data-testid="price"]'
                    ];
                    for (const sel of priceSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText.trim()) return el.innerText.trim();
                    }
                    return null;
                }""")

                await browser.close()

                return {
                    "success": True,
                    "status_code": status,
                    "title": title,
                    "json_ld": json_ld_data,
                    "dom_price_text": dom_price_text
                }

        except Exception as e:
            return {"success": False, "error": str(e)}


stealth_bot_browser = ExternalStealthBotBrowser()
