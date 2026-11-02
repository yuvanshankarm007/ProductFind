### Part 1: Frontend Audit against Vercel's `react-best-practices`

The current frontend is implemented as a standalone single-page application in [`frontend/public/index.html`](file:///C:/Users/yuvan/.gemini/antigravity/scratch/ProductFind/frontend/public/index.html) (2,671 lines, 172 KB) featuring AG Grid Community (v31.3), Tailwind CSS, Lucide Icons, and real-time WebSocket event bus bindings.

Auditing this frontend architecture against Vercel’s **8 performance categories and 70 rules**:

---

#### 1. Eliminating Request Waterfalls (`async-` rules)
* **`async-parallel` (High Impact):**
  - **Current Behavior:** In `triggerSearch()`, both the WebSocket frame (`socket.send(...)`) and parallel HTTP request (`fetch('/api/search', ...)`) fire concurrently, which is good.
  - **Issue:** Modal interactions like `openDossierModal()` (line 2199) and `openPreferenceWizard()` only begin fetching secondary data (`/api/paypal/create-dossier` or `/api/skills`) *after* the click event finishes evaluating DOM state.
  - **React Recommendation:** Implement pre-fetching on button hover/focus (`bundle-preload`) or parallelize secondary fetching using React Server Components or `Promise.all` in loader functions.

---

#### 2. Bundle Size & Asset Loading (`bundle-` rules)
* **`bundle-defer-third-party` & `bundle-barrel-imports` (Critical Impact):**
  - **Current Issue:** The page loads three unbundled vendor libraries directly in `<head>`:
    1. `https://cdn.tailwindcss.com` — **Loads the entire in-browser JIT compiler** (~3.5 MB unminified runtime memory footprint).
    2. `https://unpkg.com/lucide@latest` — Loads the complete Lucide dictionary (~1,400+ icons) when only ~15 icons are ever rendered.
    3. `https://cdn.jsdelivr.net/.../ag-grid-community.min.js` — (~1.2 MB uncompressed).
  - **React / Next.js Fix:**
    - Compile Tailwind CSS at build time using the Tailwind CLI / PostCSS plugin $\rightarrow$ reduces CSS to $< 25\text{ KB}$ with zero JavaScript overhead.
    - Import Lucide icons selectively from `lucide-react`:
      ```tsx
      import { ShieldCheck, Cpu, AlertTriangle } from 'lucide-react'; // Tree-shaken at build time
      ```
      This eliminates over **95% of icon bundle weight**.

---

#### 3. Client-Side Data Fetching & Caching (`client-` rules)
* **`client-swr-dedup` (Medium-High Impact):**
  - **Current Issue:** Raw `fetch('/api/search')` and `fetch('/api/skills')` do not deduplicate in-flight requests or cache responses. Repeated identical searches result in redundant network roundtrips.
  - **React Fix:** Wrap client queries with SWR or TanStack Query:
    ```tsx
    const { data, isValidating } = useSWR(
      ['/api/search', query, country, currency],
      ([url, q, c, curr]) => fetcher(url, { q, c, curr }),
      { revalidateOnFocus: false, dedupingInterval: 5000 }
    );
    ```
* **`client-localstorage-schema` & `js-cache-storage` (Medium Impact):**
  - **Current Issue:** Lines 1090–1106 perform 5 individual synchronous `localStorage.getItem()` and `localStorage.setItem()` operations on every preference adjustment.
  - **React Fix:** Group persistent preferences into a single versioned schema:
    ```typescript
    interface UserPreferencesV1 {
      version: 1;
      language: string;
      country: string;
      currency: string;
      preferredPayment: string;
    }
    ```

---

#### 4. Re-render & State Optimization (`rerender-` rules)
* **`rerender-memo` & Global DOM Sweeps (High Impact):**
  - **Current Issue:** Every time deal cards or comparison rows are populated, `lucide.createIcons()` is called globally across the entire `document.body` (e.g., lines 1695, 1700, 2412, 2520, 2619, 2646). This triggers full DOM-tree queries on every data change.
  - **React Fix:** In React components, icons render as self-contained JSX elements (`<ShieldCheck className="w-4 h-4 text-emerald-400" />`). Zero DOM-wide attribute scanning is required.
* **`rerender-use-deferred-value` & `rerender-transitions` (Medium Impact):**
  - **Current Issue:** The dynamic risk preference sliders (`warrantyInput`, `speedInput`, `trustInput`) call `triggerLiveReRank()` via raw `input` events, competing with browser UI rendering during rapid sliding.
  - **React Fix:** Use `useDeferredValue` or `startTransition` so the slider thumb maintains 60 FPS while background arbitration re-ranks options.

---

#### 5. Rendering & JavaScript Performance (`rendering-` & `js-` rules)
* **`rendering-svg-precision` (Medium Impact):**
  - **Current Issue:** In `renderPriceAnalytics()` (lines 1336–1344), SVG coordinates are calculated using raw floating-point numbers (`x = 142.85714285714286`, `y = 84.321894102941`).
  - **Fix:** Round SVG coordinates to 1 or 2 decimal places to reduce string parsing and GPU rasterization cost:
    ```javascript
    const x = Math.round(i * step * 10) / 10;
    const y = Math.round((height - ((p.price - minP) / range) * (height - 20) - 10) * 10) / 10;
    ```
* **`js-min-max-loop` (Low-Medium Impact):**
  - **Current Issue:** In `renderComparisonMatrix()` (line 1720), the lowest TCO item is found by copying and sorting the entire array:
    ```javascript
    const lowestTcoRow = [...activeRows].sort((a,b) => parseNum(a.tco_conv) - parseNum(b.tco_conv))[0]; // O(N log N) + array clone
    ```
  - **Fix:** Use a single $O(N)$ pass without allocating an extra array:
    ```javascript
    let lowestTcoRow = activeRows[0] || null;
    for (let i = 1; i < activeRows.length; i++) {
      if (parseNum(activeRows[i].tco_conv) < parseNum(lowestTcoRow.tco_conv)) {
        lowestTcoRow = activeRows[i];
      }
    }
    ```

---

### Part 2: Code Reviewer Status

The **`code-reviewer` subagent** is actively reviewing the recent backend and test changes:
- `backend/server.py` (IPv6 TCP loopback forwarder & startup handling)
- `backend/agents/web_scout_engine.py` (Non-store domain filtering, DOM stock inspection)
- `backend/agents/tier1_scouts.py` (Merchant-URL matching, verified specialist seeds)
- `backend/agents/tier3_compilers.py` (`live_verified_pool` gating for curated slots)
- `test_stock_and_dead_link_filter.py` & `test_live_accuracy_audit.py`

I will share the CodeRabbit review findings as soon as the subagent finishes.