# Devpost Submission: ProductFind

**Tagline:** Bidirectional Multi-Agent Commerce Swarm that analyzes warranty, accidental damage protection (ADP), and merchant reliability to compute True Cost of Ownership—backed by PayPal Buyer Protection and Pay Later.

---

## 💡 Inspiration
Consumers are conditioned to hunt for the lowest "sticker price." But in e-commerce, the lowest price is frequently an expensive trap:
- A $298 laptop listing might be an unauthorized grey-market import with **zero factory warranty**.
- A third-party seller might enforce a hidden **20% restocking fee** and a restrictive 14-day return window.
- Protection plans (ADP) often hide **$100 deductibles** or exclude liquid spills in lengthy PDF fine print.

We realized that price comparison engines are fundamentally flawed because they treat all listings equally. We wanted to build an intelligent shopping agent that looks beyond the price tag to evaluate **warranty, accidental damage protection (ADP), return guarantees, and merchant trust**—and crucially, connects the consumer to **PayPal Buyer Protection** to neutralize unvetted seller risks.

---

## 🧠 What it Does
**ProductFind** is an autonomous, bidirectional multi-agent commerce application. When a user queries a product, a swarm of specialized AI agents collaborate over a shared blackboard:

1. **Scout Swarm (Tier 1):** Concurrently gathers listings across multiple retail ecosystems (Amazon, Best Buy, Walmart, Flipkart, Refurbished Outlets).
2. **Specialist Processing Swarm (Tier 2):**
   - **Warranty & ADP Agent:** Parses complex policy clauses for OEM duration, accidental drop/spill coverage, and deductibles.
   - **Merchant Trust Sentinel:** Generates a 0–100 Trust Score based on seller authorization, return friction, and dispute history.
   - **PayPal Protection Agent:** Correlates merchant risks against PayPal capabilities. If a seller has high dispute probability or restocking fees, the agent explicitly highlights **PayPal Buyer Protection** as an essential shield, while generating **PayPal Pay in 4** installment schedules.
3. **Compiler Swarm (Tier 3):** Mathematically computes a **Risk-Adjusted Total Cost of Ownership (TCO)** and synthesizes 3 clear options:
   - 🏆 **Optimal Value Champion:** The true sweet spot (lowest risk-adjusted TCO and verified merchant trust).
   - 🛡️ **Maximum Peace-of-Mind:** Comprehensive OEM coverage + full drops/spills ADP.
   - ⚠️ **Budget Sticker (Risk Mitigated):** Lowest upfront cash outlay, paired with a mandatory PayPal Buyer Protection alert.
4. **Interactive PayPal Checkout:** Users can initiate and capture transactions directly using the PayPal Orders API v2 or PayPal Pay Later.

---

## 🔄 Bidirectional Information Flow (The Secret Sauce)
Most AI applications follow brittle linear pipelines (`Input -> Step 1 -> Step 2 -> Output`). PayPal Sentinel uses a **bidirectional cyclic graph**:
- When the **Warranty Agent** detects that a retailer's ADP deductible is ambiguous, it fires a `BACKPROPAGATION_REQUEST` backwards to the **Scout Swarm** to deep-scrape the terms modal.
- When the **Merchant Trust Sentinel** discovers an aggressive restocking fee or grey-market seller, it negotiates horizontally with the **PayPal Protection Agent** to apply PayPal's 180-day dispute resolution buffer.
- The **Compilers** can challenge and re-route queries until all confidence criteria are satisfied.
- All agent negotiations stream live to the browser via **WebSockets**, allowing users to watch the agents think, debate, and verify details in real time.

---

## 🛠️ How We Built It
- **Backend & Swarm Orchestration:** Python, FastAPI, and an asynchronous Event Bus implementing the Blackboard multi-agent design pattern.
- **Full-Duplex Communication:** WebSockets streaming real-time JSON agent traces to the frontend.
- **PayPal Integration:**
  - PayPal Orders v2 API (`/v2/checkout/orders` and `/capture`)
  - PayPal Pay in 4 (BNPL) dynamic calculation matrix
  - PayPal Buyer Protection Risk-Mitigation Engine
- **Frontend:** Responsive dashboard built with Tailwind CSS, Lucide icons, and live agent terminal streams.

---

## 🏆 Accomplishments that We're Proud Of
- **True Bidirectional Swarm:** Built an agent network where agents can query backwards, reject assumptions, and resolve ambiguities without breaking execution flow.
- **Solving the TCO Dilemma:** Demonstrated that the lowest sticker price (e.g. Walmart open box at $298.50) actually had the highest Risk-Adjusted TCO ($402.51) due to restocking fees and lack of OEM warranty.
- **Deep PayPal Synergy:** PayPal isn't an afterthought button; it is an active risk-mitigation component of the agent's decision logic.

---

## 🔮 What's Next for ProductFind
- Direct integration with PayPal Fastlane for 1-click accelerated checkout.
- Automated agentic dispute filing through PayPal's Resolution Center API if delivery delays occur.
- Expanding real-time crawling to global regional marketplaces.
