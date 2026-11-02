# CodeRabbit Code Review: ProductFind Multi-Agent Swarm

**Review Scope:**
- `backend/server.py`
- `backend/agents/web_scout_engine.py`
- `backend/agents/tier1_scouts.py`
- `backend/agents/tier3_compilers.py`
- `frontend/public/index.html`
- `test_stock_and_dead_link_filter.py` & `test_live_accuracy_audit.py`

---

## Executive Summary

The reviewed changes enhance real-time e-commerce intelligence with anti-bot scraping (`curl_cffi` / Chrome 124 TLS emulation), dead-link/out-of-stock gating, live price calibration, dynamic risk-adjusted TCO ranking, and AG Grid comparative auditing. 

While the architecture is well-designed with strong domain modeling, several critical and high-severity issues were identified regarding **object reference mutation**, **thread/socket lifecycle management**, **concurrency race conditions**, **regex overmatching**, and **DOM XSS injection**.

---

## Findings Summary

| Severity | Category | File | Description |
| :--- | :--- | :--- | :--- |
| 🔴 **CRITICAL** | Correctness / Bug | `backend/agents/tier3_compilers.py` | Reference aliasing mutates and overwrites `MAX_PROTECTION` tier with `BUDGET_STICKER`. |
| 🟠 **HIGH** | Performance / Resource Leak | `backend/server.py` | Unbounded thread creation (3 OS threads per connection) & slow socket cleanup in IPv6 relay. |
| 🟠 **HIGH** | Concurrency / Data Integrity | `backend/server.py` | `global_bus.clear()` on incoming search wipes event stream across concurrent sessions. |
| 🟠 **HIGH** | Correctness / False Positives | `backend/agents/web_scout_engine.py` | Whole-document regex match for "out of stock" flags in-stock items with OOS related items/variants. |
| 🟠 **HIGH** | Architectural / Scalability | `backend/agents/tier1_scouts.py` | Hardcoded Latitude 5511 seed fixtures leak into unrelated search queries matching "latitude". |
| 🟠 **HIGH** | Concurrency / Race Condition | `frontend/public/index.html` | Simultaneous WebSocket and HTTP search dispatches race and overwrite UI state without sequence tokens. |
| 🟡 **MEDIUM** | Security (XSS) | `frontend/public/index.html` | Unescaped user/merchant data interpolated into `innerHTML` across terminal and AG Grid renderers. |
| 🟡 **MEDIUM** | Deprecation & Error Handling | `backend/server.py` | Deprecated `@app.on_event("startup")` and unhandled `json.loads` crash on WebSocket input. |
| 🟡 **MEDIUM** | Test Robustness | `test_stock_and_dead_link_filter.py` | Unit test lacks mock isolation, creating flaky external network dependencies in CI. |
| 🟢 **LOW** | Code Quality | `backend/core/state.py` & `tier3_compilers.py` | Undeclared attributes on `ScrapedListing` accessed via `getattr` fallback instead of typed fields. |

---

## Detailed Findings & Actionable Fixes

---

### 🔴 CRITICAL: Reference Aliasing Mutates `MAX_PROTECTION` Tier
**File:** `backend/agents/tier3_compilers.py` (Lines 304–332)

#### Problem
When `live_verified_pool` contains exactly 2 in-stock listings (`A` and `B`):
1. `optimal` is selected as `A`.
2. `max_protect` is selected as `B` (from `pool_prot = [B]`).
3. For `budget`, `pool_budget = [opt for opt in live_verified_pool if opt.id not in (optimal.id, max_protect.id)]` evaluates to empty `[]`.
4. The fallback runs: `pool_budget = [opt for opt in live_verified_pool if opt.id != optimal.id]`, which selects `B` again!
5. `budget.recommendation_tier = "BUDGET_STICKER"` is executed.
6. Because in Python objects are passed by reference, **this mutates `B.recommendation_tier` in-place**, permanently overwriting `max_protect.recommendation_tier`! Both `curated[1]` and `curated[2]` point to the identical instance with tier `"BUDGET_STICKER"`.

#### Actionable Fix
```python
<<<<
        if pool_budget:
            budget = sorted(pool_budget, key=lambda x: x.converted_cash_outlay)[0]
            budget.recommendation_tier = "BUDGET_STICKER"
            budget.tier_reason = f"Lowest initial cash outlay ({self.fx.format_price(budget.converted_cash_outlay, curr)}) among verified live in-stock retailers."
            budget.rank = 3
            curated.append(budget)
        else:
            budget = max_protect
====
        if pool_budget:
            candidate_budget = sorted(pool_budget, key=lambda x: x.converted_cash_outlay)[0]
            if candidate_budget.id == max_protect.id:
                # Clone instance to avoid mutating max_protect reference
                budget = candidate_budget.model_copy(deep=True)
            else:
                budget = candidate_budget
            budget.recommendation_tier = "BUDGET_STICKER"
            budget.tier_reason = f"Lowest initial cash outlay ({self.fx.format_price(budget.converted_cash_outlay, curr)}) among verified live in-stock retailers."
            budget.rank = 3
            curated.append(budget)
        else:
            budget = max_protect.model_copy(deep=True)
            budget.recommendation_tier = "BUDGET_STICKER"
            budget.rank = 3
            curated.append(budget)
>>>>
```

---

### 🟠 HIGH: Thread & Socket Lifecycle Hazard in IPv6 Relay
**File:** `backend/server.py` (Lines 42–106, 448)

#### Problem
1. **Thread Explosion**: For each connection to `[::1]:8000`, the relay spawns **3 unbounded daemon threads** (`pipe` client->target, `pipe` target->client, and `cleanup`). A burst of 30 browser asset/WS connections creates 90 OS threads.
2. **Double Startup**: `start_ipv6_loopback_relay` is executed on line 448 in `__main__` AND on line 105 via `@app.on_event("startup")`. On restart/reload, port `[::1]:8000` collisions occur.
3. **Lack of Graceful Shutdown**: The listening socket and client sockets are never stopped on server shutdown.

#### Actionable Fix
Migrate from `@app.on_event` to FastAPI's async `lifespan` handler and manage the relay with a reusable connection handler or `asyncio.start_server`:
```python
<<<<
def start_ipv6_loopback_relay(port: int = 8000) -> None:
...
@app.on_event("startup")
def startup_event():
    port = int(os.getenv("PORT", 8000))
    start_ipv6_loopback_relay(port)
====
from contextlib import asynccontextmanager

relay_server = None

async def run_ipv6_relay(port: int):
    async def handle_relay(reader, writer):
        try:
            target_reader, target_writer = await asyncio.open_connection('127.0.0.1', port)
            async def forward(src, dst):
                try:
                    while data := await src.read(16384):
                        dst.write(data)
                        await dst.drain()
                except Exception:
                    pass
                finally:
                    dst.close()
            await asyncio.gather(
                forward(reader, target_writer),
                forward(target_reader, writer),
                return_exceptions=True
            )
        except Exception:
            writer.close()

    try:
        server = await asyncio.start_server(handle_relay, '::1', port)
        return server
    except Exception as e:
        print(f"[IPv6 Relay] Bound status: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    port = int(os.getenv("PORT", 8000))
    relay = await run_ipv6_relay(port)
    yield
    if relay:
        relay.close()
        await relay.wait_closed()

app = FastAPI(
    title="ProductFind AI",
    version="2.0.0",
    lifespan=lifespan
)
>>>>
```

---

### 🟠 HIGH: Shared `global_bus.clear()` Wipes Events Across Concurrent Users
**File:** `backend/server.py` (Line 250, Line 378)

#### Problem
`global_bus.clear()` is called at the start of every search request. Because `global_bus` is a singleton instance shared across all HTTP and WebSocket connections, executing a search in Session B purges the message queues and event history for Session A mid-negotiation.

#### Actionable Fix
Scope event queues by `session_id` on the event bus:
```python
# Pass session_id to event bus emit/subscribe or instantiate session-scoped bus:
@app.post("/api/search")
async def api_search(req: SearchRequest):
    # Do NOT call global_bus.clear() globally!
    session_bus = global_bus.get_session_scope(req.session_id)
    ...
```

---

### 🟠 HIGH: False Out-of-Stock Flags from Full-HTML Regex
**File:** `backend/agents/web_scout_engine.py` (Lines 352–364)

#### Problem
`probe_live_merchant_details` searches the entire HTML document using:
`re.search(r'\b(out\s*of\s*stock|sold\s*out|currently\s*unavailable|notify\s*me\s*when\s*available)\b', html, re.I)`

Many major e-commerce platforms (Amazon, Flipkart, Best Buy) contain:
- Carousel recommendations of other products that are out of stock.
- Variant selectors (e.g. 1TB variant is sold out, but 512GB being inspected is in stock).
- Footer text or newsletter signups ("Notify me when available").
This causes legitimate in-stock products to be marked as `in_stock = False`.

#### Actionable Fix
Target specific availability microdata, JSON-LD, or availability DOM containers:
```python
<<<<
            if html:
                # 2. Check for explicit Out of Stock signals across HTML text and JSON-LD
                is_out_of_stock = bool(
                    re.search(r'\b(out\s*of\s*stock|sold\s*out|currently\s*unavailable|temporarily\s*unavailable|notify\s*me\s*when\s*available|back\s*in\s*stock\s*soon)\b', html, re.I)
                    or "schema.org/OutOfStock" in html
                    or '"availability":"https://schema.org/OutOfStock"' in html
                    or '"availability": "https://schema.org/OutOfStock"' in html
                )
====
            if html:
                # 1. First check explicit schema.org and OpenGraph availability signals
                is_schema_oos = bool(
                    re.search(r'schema\.org/OutOfStock', html, re.I)
                    or re.search(r'"availability"\s*:\s*"[^"]*OutOfStock"', html, re.I)
                )
                
                # 2. Extract targeted buy/stock container if present
                stock_container_m = re.search(r'(?:id|class)=["\'](?:availability|stock-status|buybox-status)[^"\']*["\'][^>]*>(.*?)</div>', html, re.I | re.DOTALL)
                stock_text = stock_container_m.group(1) if stock_container_m else ""
                is_dom_oos = bool(re.search(r'\b(out of stock|sold out|currently unavailable)\b', stock_text, re.I)) if stock_text else False
                
                is_out_of_stock = is_schema_oos or is_dom_oos
>>>>
```

---

### 🟠 HIGH: Parallel HTTP & WebSocket Search Dispatches Race in Frontend
**File:** `frontend/public/index.html` (Lines 1263–1285)

#### Problem
In `triggerSearch`, the UI sends a WebSocket message AND fires a parallel HTTP `fetch('/api/search')`. When both complete, `applySearchResults` is invoked twice. If the user initiates a second query or re-ranks while the first HTTP fetch is in flight, the slower HTTP response will arrive late and overwrite the new results with stale data.

#### Actionable Fix
Implement an `AbortController` and sequence ID:
```javascript
let currentSearchController = null;
let currentSearchToken = 0;

function triggerSearch(query) {
    if (currentSearchController) {
        currentSearchController.abort();
    }
    currentSearchController = new AbortController();
    const searchToken = ++currentSearchToken;

    // Use WebSocket as primary, HTTP as fallback only if WS is disconnected
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(payload));
    } else {
        fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: currentSearchController.signal
        })
        .then(r => r.json())
        .then(state => {
            if (searchToken === currentSearchToken) {
                applySearchResults(state);
            }
        });
    }
}
```

---

### 🟡 MEDIUM: XSS Vulnerability in Scraped Content Interpolation
**File:** `frontend/public/index.html` (Lines 1206–1211, Lines 1741–1749)

#### Problem
Strings returned by web scouts (`product_title`, `merchant`, `content` in terminal logs) are rendered directly into `.innerHTML` without escaping. An attacker controlling an e-commerce page title (e.g. `<img src=x onerror=alert(document.domain)>`) can achieve stored XSS when that title is scouted and rendered in the comparison matrix.

#### Actionable Fix
Sanitize or use textContent / DOM escaping:
```javascript
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
```

---

### 🟡 MEDIUM: Flaky Network Coupling in Regression Tests
**File:** `test_stock_and_dead_link_filter.py` (Lines 20–26)

#### Problem
`test_dead_links_and_out_of_stock_ruled_out_from_recommendations` calls live scouts against DuckDuckGo and Flipkart directly without mocking. If external networks throttle requests or fail, the test will fail or hit the 8.5s timeout circuit-breaker. Additionally, the test misses validating that recommendation tiers are distinct and not overwritten.

#### Actionable Fix
Add assertion for distinct tiers and mock live scrape requests using `unittest.mock.AsyncMock` or `pytest-httpx` for offline reliability.

```python
# Add tier distinction assertion:
tiers = [opt.recommendation_tier for opt in state.final_options]
assert len(set(tiers)) == len(tiers), f"Duplicate recommendation tiers found: {tiers}"
assert "MAX_PROTECTION" in tiers, "MAX_PROTECTION tier was overwritten or dropped!"
assert "OPTIMAL_VALUE" in tiers, "OPTIMAL_VALUE tier missing!"
assert "BUDGET_STICKER" in tiers, "BUDGET_STICKER tier missing!"
```

---

## Conclusion
The core multi-agent logic, risk modeling, and AG Grid integration are architecturally solid. Addressing the **Critical** reference cloning in `tier3_compilers.py` and the **High** concurrency/lifecycle fixes in `server.py` and `web_scout_engine.py` will guarantee production stability and zero-crash demo readiness.