# Devpost Submission: ProductFind
### Bidirectional Multi-Agent Commerce Swarm with PayPal Buyer Protection & AG Grid Intelligence
*Built for the [PayPal AI Hackathon on Devpost](https://paypalaihackathon.devpost.com/)*

---

## 🎯 Target Hackathon Tracks & Sponsor Categories
- 🛡️ **Core Track:** Best Use of PayPal AI & Buyer Protection / Pay Later Integration
- 🏆 **Sponsor Bounty:** **Best Use of AG Grid** (High-Performance Multi-Agent Comparison Matrix)

---

## 💡 Inspiration
Consumers are conditioned to hunt for the lowest "sticker price." But in e-commerce, the lowest price is frequently an expensive trap:
- A $298 laptop listing might be an unauthorized grey-market import with **zero factory warranty**.
- A third-party seller might enforce a hidden **20% restocking fee** and a restrictive 14-day return window.
- Protection plans (ADP) often hide **$100 deductibles** or exclude liquid spills in lengthy PDF fine print.
- International orders add **18.5% customs duties** and **3.5% bank foreign transaction fees**.
- Unverified couriers deliver sealed packages with zero **Open Box Delivery inspection**, leaving buyers exposed to counterfeit swap scams.

We built **ProductFind** to look beyond the sticker price: an intelligent multi-agent swarm that interrogates fine-print warranties, audits merchant reputation, estimates delivery windows, verifies COD and Open Box delivery, forecasts price trajectories, and displays the entire comparison in an enterprise-grade **AG Grid matrix**—seamlessly backed by **PayPal Buyer Protection** and **PayPal Pay in 4**.

---

## 🧠 The Core Breakthrough: Autonomous Skill Acquisition (Zero Memorization)
> *"Real intelligence isn’t about memorizing answers — it’s knowing what to do when the problem changes."*

Traditional shopping scrapers rely on brittle, hardcoded CSS selectors and memorized schemas. When an AI encounters a novel, unindexed merchant, a foreign regional marketplace, or a brand-new boutique store, traditional tools hallucinate or crash.

ProductFind implements an **Autonomous Skill Acquisition Engine (Voyager / Reflexion Architecture)** that learns new skills on the fly:
1. **Dynamic Perception & Discovery:** When encountering an unfamiliar merchant (e.g. Croma in India, Newegg in the US, MediaMarkt in Germany, or an unindexed Shopify store), the agent analyzes DOM structures, Schema.org JSON-LD microdata, and fine-print text at test time.
2. **Self-Reflective Skill Synthesis:** The swarm autonomously generates an executable parsing and policy-auditing skill (`AdaptiveSkill`).
3. **Invariant Self-Verification:** The agent checks return windows, restocking fee percentages, warranty durations, and COD terms against logical invariants. If ambiguous, it self-reflects and enforces conservative risk bounds.
4. **Persistent Skill Vault (`backend/skills_vault/`):** Acquired skills are saved into a persistent library, allowing the swarm to continuously grow smarter with every search.
5. **Autonomous PayPal Section 13 Shield:** For novel, unfamiliar merchants, the swarm automatically generates an unforgeable cryptographic **PayPal Buyer Protection Dossier** citing **PayPal User Agreement § 13.1 & § 13.2**, guaranteeing 100% dispute protection for buyers venturing outside mainstream retailers.

---

## 🧠 What it Does
**ProductFind** is an autonomous, bidirectional multi-agent commerce application. When a user queries a product, specialized AI agents collaborate over a shared blackboard:

1. **Scout Swarm (Tier 1):** Concurrently gathers listings across domestic & global retailers (Amazon, Best Buy, Walmart, Flipkart, Refurbished Outlets), capturing delivery windows, COD availability, and open box policies.
2. **Specialist Processing Swarm (Tier 2):**
   - **Warranty & ADP Agent:** Parses complex policy clauses for OEM duration, accidental drop/spill coverage, and deductibles.
   - **Merchant Trust Sentinel:** Generates a 0–100 Trust Score based on seller authorization, return friction, and dispute history.
   - **Currency FX & Customs Duty Inspector:** Detects cross-border shipments, converts live FX rates, calculates import duties, and compares 3.5% bank card foreign fees vs. PayPal native conversion.
   - **Price History & AI Prediction Agent:** Evaluates 90-day price trajectories (ATL, ATH, 90d Average) and delivers a 14-day forecast with a **BUY NOW vs WAIT** verdict.
   - **PayPal Protection Agent:** Correlates seller risks against PayPal protections. Activates **180-Day PayPal Buyer Protection** and generates **PayPal Pay in 4** installment terms.
3. **Compiler Swarm (Tier 3):** Mathematically computes a **Multi-Currency Risk-Adjusted Total Cost of Ownership (TCO)** and curates:
   - 🏆 **Optimal Value Champion:** The true sweet spot (lowest risk-adjusted TCO and verified merchant trust).
   - 🛡️ **Maximum Peace-of-Mind:** Comprehensive OEM coverage + full drops/spills ADP.
   - ⚠️ **Budget Sticker (Risk Mitigated):** Lowest upfront cash outlay, paired with a mandatory PayPal Buyer Protection alert.
4. **Interactive AG Grid Swarm Matrix:** Renders every fine-print attribute in a high-performance, filterable, sortable AG Grid with custom renderers and CSV export.
5. **Interactive PayPal Checkout:** Users can initiate and capture transactions directly using the PayPal Orders API v2 or PayPal Pay Later in any supported fiat currency.

---

## 🏆 Sponsor Bounty: Best Use of AG Grid

**ProductFind** leverages **AG Grid (Quartz Dark Theme)** as the mission-critical interactive data cockpit for consumer decision-making. 

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

## 🔄 Bidirectional Information Flow (The Secret Sauce)
Most AI applications follow brittle linear pipelines (`Input -> Step 1 -> Step 2 -> Output`). ProductFind uses a **bidirectional cyclic graph**:
- When the **Warranty Agent** detects that a retailer's ADP deductible is ambiguous, it fires a `BACKPROPAGATION_REQUEST` backwards to the **Scout Swarm** to deep-scrape the terms modal.
- When the **Merchant Trust Sentinel** discovers an aggressive restocking fee or grey-market seller, it negotiates horizontally with the **PayPal Protection Agent** to apply PayPal's 180-day dispute resolution buffer.
- The **Compilers** can challenge and re-route queries until all confidence criteria are satisfied.
- All agent negotiations stream live to the browser via **WebSockets**, allowing users to watch the agents think, debate, and verify details in real time.

---

## 🛠️ How We Built It
- **Backend & Swarm Orchestration:** Python, FastAPI, and an asynchronous Event Bus implementing the Blackboard multi-agent design pattern.
- **Cloud-Native Database & Caching:**
  - **Google Cloud Firestore (Native Mode):** Multi-region (`nam5`) durable persistence for autonomously learned merchant skills (`merchants_skills`), cryptographic PayPal dispute dossiers (`dispute_dossiers`), and order sessions (`orders`), backed by Point-in-Time Recovery (PITR).
  - **Google Cloud Memorystore (Redis):** Sub-millisecond caching for 90-day econometric trajectories and 14-day price predictions.
  - **Zero-Crash Resilience Architecture:** Transparent fallback to local encrypted disk and in-memory caches when offline or running in sandboxed demo environments.
- **Infrastructure as Code (IaC):** Modular Terraform configurations (`deploy/terraform/main.tf`, `variables.tf`, `outputs.tf`) provisioning Firestore, composite indexes, Memorystore, and least-privilege IAM service accounts.
- **Data Grid Layer:** AG Grid Community (Quartz Dark theme) with custom renderers, pinned columns, and native CSV export.
- **Multilingual Support (i18n):** Real-time localized agent traces in English, Hindi, Spanish, German, French, and Japanese.
- **Full-Duplex Communication:** WebSockets streaming real-time JSON agent traces to the frontend.
- **PayPal Integration:**
  - PayPal Orders v2 API (`/v2/checkout/orders` and `/capture`) with multi-currency support
  - PayPal Pay in 4 (BNPL) dynamic calculation matrix
  - PayPal Buyer Protection Risk-Mitigation Engine & Section 13 Cryptographic Merkle Dossier Vault
- **Cloud Deployment:** Google Cloud Platform & Render web service with automated blueprint (`render.yaml`).

---

## 🏆 Accomplishments that We're Proud Of
- **True Bidirectional Swarm:** Built an agent network where agents can query backwards, reject assumptions, and resolve ambiguities without breaking execution flow.
- **Solving the TCO Dilemma:** Demonstrated that the lowest sticker price actually has the highest Risk-Adjusted TCO due to restocking fees, lack of OEM warranty, and cross-border duties.
- **Deep PayPal Synergy:** PayPal isn't an afterthought button; it is an active risk-mitigation component of the agent's decision logic.
- **Enterprise-Grade AG Grid Integration:** Seamlessly handles multi-currency conversion, live filtering, and interactive row actions.
