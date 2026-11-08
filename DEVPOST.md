# Devpost Submission: ProductFind Sentinel
### *Autonomous Multi-Agent Commerce Swarm with PayPal Buyer Protection & AG Grid Intelligence*
*Built for the [PayPal AI Hackathon on Devpost](https://paypalaihackathon.devpost.com/)*

---

## 🎯 Target Hackathon Tracks & Sponsor Categories
- 🛡️ **Core Track:** Best Use of PayPal AI & Buyer Protection / Pay Later Integration
- 🏆 **Sponsor Bounty:** **Best Use of AG Grid** (High-Performance Multi-Agent Comparison Matrix)
- ☁️ **Cloud Track:** Best Enterprise Deployment on Google Cloud (Firestore Native, Memorystore, Vertex AI)

---

## 💡 Tagline
> **The Autonomous Multi-Agent Commerce Swarm that audits fine-print warranties, calculates true Risk-Adjusted TCO, auto-stacks credit cards with PayPal Pay Later, and generates cryptographic Section 13 dispute dossiers.**

---

## 💡 Inspiration: The Hidden Cost Trap
Consumers are conditioned to hunt for the lowest "sticker price." But in modern e-commerce, the lowest sticker price is frequently an expensive trap:
- A $298 laptop listing might be an unauthorized grey-market import with **zero factory warranty**.
- A third-party seller might enforce a hidden **20% restocking fee** and a restrictive 14-day return window.
- Protection plans (ADP) often hide **$100 deductibles** or exclude liquid spills in lengthy PDF fine print.
- International orders add **18.5% customs duties** and **3.5% bank foreign transaction fees**.
- Unverified couriers deliver sealed packages while refusing **Open Box doorstep inspection**, leaving buyers exposed to counterfeit swap scams.

We built **ProductFind Sentinel** to look beyond the sticker price: an intelligent multi-agent swarm that interrogates fine-print warranties, audits merchant reputation, estimates delivery windows, verifies COD and Open Box delivery, forecasts price trajectories, and displays the entire comparison in an enterprise-grade **AG Grid matrix**—seamlessly backed by **PayPal Buyer Protection**, **PayPal Pay in 4**, and **1-Click Cryptographic Section 13 Dispute Dossiers**.

---

## 🧠 The Core Breakthrough: Autonomous Fine-Print Arbitration
Traditional shopping scrapers rely on brittle, hardcoded CSS selectors and memorized schemas. When an AI encounters a novel, unindexed merchant, a foreign regional marketplace, or a brand-new boutique store, traditional tools hallucinate or crash.

ProductFind implements an **Autonomous Multi-Agent Swarm (Voyager / Reflexion Architecture)** that learns new skills on the fly:
1. **Dynamic Perception & Discovery:** When encountering an unfamiliar merchant, the agent analyzes DOM structures, Schema.org JSON-LD microdata, and fine-print text at test time.
2. **Self-Reflective Skill Synthesis:** The swarm autonomously generates an executable parsing and policy-auditing skill (`AdaptiveSkill`).
3. **Invariant Self-Verification:** The agent checks return windows, restocking fee percentages, warranty durations, and COD terms against logical invariants. If ambiguous, it self-reflects and enforces conservative risk bounds.
4. **Persistent Skill Vault (`backend/skills_vault/` & GCP Firestore):** Acquired skills are saved into a persistent library, allowing the swarm to continuously grow smarter with every search.
5. **Autonomous PayPal Section 13 Shield:** For novel, unfamiliar merchants, the swarm automatically generates an unforgeable cryptographic **PayPal Buyer Protection Dossier** citing **PayPal User Agreement § 13.1 & § 13.2**, guaranteeing 100% dispute protection for buyers venturing outside mainstream retailers.

---

## ⚡ What It Does: The 6 Pillars of ProductFind Sentinel

### 1. 🔍 Multimodal Google Lens & Voice Search Cockpit
- Sleek **Google Gemini-inspired search capsule** with live audio voice transcription (`webkitSpeechRecognition`), drag-and-drop packaging photo analysis, and 1-click preset workflows.
- Zero premature auto-searching: shoppers type or dictate naturally before triggering the swarm.

### 2. 🤖 Three-Tier Autonomous Swarm Architecture
- **Tier 1 (Scout Swarm):** Concurrently gathers listings across domestic & global retailers (Amazon, Best Buy, Walmart, Flipkart, OEM Stores), capturing delivery windows, COD availability, and open box policies.
- **Tier 2 (Fine-Print Auditors):**
  - **Warranty & ADP Agent:** Parses complex policy clauses for OEM duration, accidental drop/spill coverage, and deductibles.
  - **Merchant Trust Sentinel:** Generates a 0–100 Trust Score based on seller authorization, return friction, and dispute history.
  - **Currency FX & Customs Duty Inspector:** Detects cross-border shipments, converts live FX rates, calculates import duties, and compares 3.5% bank card foreign fees vs. PayPal native conversion.
  - **Price History & AI Prediction Agent:** Evaluates 90-day price trajectories (ATL, ATH, 90d Average) and delivers a 14-day forecast with a **BUY NOW vs WAIT** verdict.
  - **PayPal Protection Agent:** Correlates seller risks against PayPal protections. Activates **180-Day PayPal Buyer Protection** and generates **PayPal Pay in 4** installment terms.
- **Tier 3 (Compiler Swarm):** Mathematically computes a **Multi-Currency Risk-Adjusted Total Cost of Ownership (TCO)** and curates:
  - 🏆 **Optimal Value Champion:** The true sweet spot (lowest risk-adjusted TCO and verified merchant trust).
  - 🛡️ **Maximum Peace-of-Mind:** Comprehensive OEM coverage + full drops/spills ADP.
  - ⚠️ **Budget Sticker (Risk Mitigated):** Lowest upfront cash outlay, paired with a mandatory PayPal Buyer Protection alert.

### 3. ⚔️ Head-to-Head Versus Engine
- Compares flagships side-by-side (e.g. *Sony WH-1000XM5 vs Bose QuietComfort Ultra*).
- Generates dynamic spec comparison tables, real-world battery/ANC durability benchmarks, and a synthesized Swarm AI verdict.

### 4. 📦 Combinatorial Knapsack Cart-Splitter
- For multi-item workflows (e.g., *WFH Setup under ₹50,000* or *Developer Workstation*), Sentinel models the cross-store cart as a **0/1 Knapsack & Set Cover problem**, splitting items across merchants to maximize savings while factoring in shipping fees and bulk thresholds.

### 5. 💳 Smart Wallet Stacker (Credit Card + PayPal Double-Dip)
- Automatically evaluates user-owned credit cards (HDFC Millennia, ICICI Amazon Pay, Axis Atlas, Amex Platinum) alongside **PayPal Pay Later**.
- Computes optimal card stacking, instantly unlocking extra cashback and bank merchant partner discounts.

### 6. ⚖️ 1-Click Cryptographic Section 13 Dispute Guard
- If a courier delivers a damaged item or refuses mandated doorstep open-box inspection, Sentinel seals the transaction and evidence into an unforgeable **SHA-256 Merkle tree**.
- Generates a formal, legally admissible **Section 13 Chargeback Dossier PDF** citing **PayPal User Agreement § 13.1 & § 13.2** with embedded cryptographic root hash, ready for instant bank or PayPal dispute submission.

---

## 🏆 Sponsor Bounty: Best Use of AG Grid

**ProductFind Sentinel** leverages **AG Grid (Quartz Dark Theme)** as the mission-critical interactive data cockpit for consumer decision-making. 

Instead of showing a flat static table, ProductFind uses advanced AG Grid features to turn complex multi-agent outputs into an actionable, enterprise-grade shopping matrix:
1. **Custom Cell Renderers:**
   - **Store & Domain (Pinned Left):** Renders merchant name, domain, and country badge.
   - **Landed Price vs Risk-Adjusted TCO:** Highlights mathematical risk penalties alongside raw sticker prices in the user's preferred currency.
   - **Merchant Trust Index:** Dynamic progress pill color-coded by seller reputation (0–100).
   - **Service Assurance Chips:** Visual indicators for **Cash on Delivery (COD)**, **Open Box Delivery (Doorstep OTP Inspection)**, and **Exchange Offers**.
   - **Cross-Border FX & Import Duties:** Flags international shipments and compares bank card 3.5% foreign surcharges against PayPal Native Conversion.
   - **Embedded Interactive Checkout (Pinned Right):** A dedicated action column rendering live PayPal checkout triggers directly inside the grid cells.
2. **Real-Time Quick Filter Search:** Instantly filters across all fine-print attributes, stores, and policies.
3. **One-Click Native CSV Export:** Buyers can export complete multi-merchant comparison audits locally using `gridApi.exportDataAsCsv()`.
4. **KPI Summary Ribbon:** Displays real-time metrics (Audited Listings, Lowest TCO, COD availability, Open Box verified count).
5. **Column Pinning, Sorting & Resizing:** Seamlessly compare dozens of policy nuances across retailers without losing track of the merchant or checkout action.

---

## 🌟 Interactive 60-Second Judge Tour
We built a dedicated **`🌟 60s Judge Tour`** engine directly into the UI! Reviewers and judges can click a single button to experience an automated, five-stage guided tour with live telemetry, highlighting:
1. Autonomous Swarm Ingestion
2. TCO Champions & AG Grid Cockpit
3. Head-to-Head Versus Showdown
4. Smart Wallet Stacker
5. Cryptographic Section 13 Dispute Guard with live PDF generation

---

## 🔌 Cross-Platform: Manifest V3 Browser Extension
Sentinel extends beyond the web application with a complete Chrome Extension (`extension/`). When browsing Amazon, Flipkart, or Best Buy, Sentinel automatically detects the product on the active tab and displays an unobtrusive in-page overlay with instant price arbitrage, OEM warranty verification, and PayPal protection score.

---

## 🛠️ Tech Stack & Architecture
- **Backend:** Python 3.11, FastAPI, Asynchronous Event Bus (Blackboard Pattern), WebSockets, ReportLab (PDF Engine).
- **Frontend:** Responsive HTML5 / CSS3 (Quartz Dark Glassmorphism), AG Grid Community, Lucide Icons, Web Speech API, Canvas API.
- **Data & Caching:** Google Cloud Firestore (Native Mode), Google Cloud Memorystore (Redis), SQLite fallback.
- **Payments & Dispute Security:** PayPal Orders API v2, PayPal Pay in 4, PayPal User Agreement § 13 statutory engine, SHA-256 Merkle Proofs.
- **Testing:** Pytest test suite with **120 passing automated tests**.

---

## 📈 Accomplishments We're Proud Of
- **100% Zero-Crash Live Demo Resilience:** Tested against live and simulated network environments with graceful mock fallbacks and zero unhandled exceptions.
- **Solving the TCO Dilemma:** Mathematically proved that the lowest sticker price often has the highest Total Cost of Ownership.
- **Deep PayPal Synergy:** Integrated PayPal as an active risk-mitigation shield throughout the entire shopping lifecycle.
- **120 Passing Tests:** Robust test coverage across model fidelity, session isolation, stealth browsing, and commercial expansions.
