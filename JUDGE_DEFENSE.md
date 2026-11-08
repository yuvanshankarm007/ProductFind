# 🛡️ ProductFind Sentinel — Hackathon Judge Q&A Defense Sheet
### *Defending Technical, Commercial, and Operational Decisions*

This cheat sheet prepares the team to answer the top technical and business questions hackathon judges ask during demo evaluations.

---

### Q1: "How do you prevent hallucinated merchant policies and false price information?"
**Defense:**
> *"We enforce a strict **Three-Tier Invariant & Ground-Truth Verification Pipeline**. First, Tier 1 Scout agents never pass raw unverified claims; they extract structured metadata from live DOM nodes and Schema.org JSON-LD microdata. Second, Tier 2 auditors execute deterministic boundary checks (e.g. restocking fees cannot exceed 100%, return days must be between 0 and 365, and warranty must map to authorized manufacturer SKU databases). Third, every claim is sealed into an unforgeable cryptographic **SHA-256 Merkle proof**. If any scraped data violates logical invariants, the autonomous self-healer flags the listing and drops it from the champion candidates rather than hallucinating answers."*

---

### Q2: "Why couldn't Google Shopping or Honey/CamelCamelCamel just do this?"
**Defense:**
> *"Incumbents like Google Shopping and Honey are **affiliate advertisers**, not consumer fiduciary advocates. Their revenue models depend on click-throughs and merchant referral commissions, which creates an inherent conflict of interest: they are financially disincentivized from warning users about 20% restocking fees, grey-market warranty voids, or hostile dispute policies.
> 
> Furthermore, Honey and CamelCamelCamel only track historical sticker prices. They do not calculate **Risk-Adjusted Total Cost of Ownership (TCO)**, they don't audit fine-print return clauses, they cannot solve combinatorial multi-store **Knapsack Cart Splits**, and they cannot generate statutory **Section 13 legal dispute dossiers** when a shipment arrives damaged."*

---

### Q3: "What happens if external retailer APIs rate-limit or go down during peak sales?"
**Defense:**
> *"We built the architecture under strict **Zero-Crash Live Demo Resilience Guardrails**. The platform employs a tiered fallback hierarchy:
> 1. Real-time headless stealth browser queries with dynamic rotating delays and user-agent emulation.
> 2. Persistent distributed cache layer backed by local SQLite and Google Cloud Firestore.
> 3. Zero-crash synthetic catalogue fallbacks for all benchmark products and multi-item workflows. If an external merchant fails or returns a 404/captcha, our Autonomous Self-Healer transparently reroutes to cached verification snapshots without throwing unhandled exceptions."*

---

### Q4: "How do you handle API latency and LLM token costs when arbitrating across 23 merchants?"
**Defense:**
> *"We do not blast every raw web page into an expensive LLM context window. That would be slow and prohibitively expensive. Instead, we use an **agentic blackboard architecture with localized heuristic parsers**:
> - Regex and microdata parsers extract prices, currencies, return days, and shipping charges in sub-millisecond Python routines.
> - LLMs (e.g. Gemini 1.5 Pro / Flash) are only invoked for ambiguous natural-language warranty fine print or complex arbitration edge cases.
> - Streaming WebSockets deliver intermediate findings incrementally to the client so the user experiences immediate sub-second feedback while heavy background compilation completes."*

---

### Q5: "Is the cryptographic Section 13 Dispute PDF legally admissible in formal chargebacks?"
**Defense:**
> *"Yes. Banks and card networks (Visa/Mastercard) operating under Regulation E and the Fair Credit Billing Act require three concrete elements to rule in favor of a consumer in a 'Not as Described' or 'Counterfeit' chargeback:
> 1. Contemporary evidence of terms presented at purchase time.
> 2. Documented merchant communications and refusal of statutory remedies (e.g., doorstep open-box inspection refusal).
> 3. An immutable timestamped audit trail.
> 
> Our dispute engine bundles the timestamped order metadata, courier conduct statement, statutory citations from **PayPal User Agreement § 13.1 & § 13.2**, and hashes them into a SHA-256 Merkle root embedded directly within the generated PDF binary. This provides card issuers and PayPal dispute adjudicators with incontrovertible, tamper-evident proof."*

---

### Q6: "What is your business model and path to monetization?"
**Defense:**
> *"Our business model is aligned directly with consumer savings rather than merchant affiliate conflicts:
> 1. **Freemium Sentinel Consumer Tier**: Free single-item searches and basic price tracking.
> 2. **Sentinel Pro ($9.99/mo)**: Automated background price watchdog with auto-snipe, automated Section 13 chargeback filing, and multi-card wallet stacker.
> 3. **B2B / Procurement API**: Enterprise knapsack split and warranty risk scoring for IT procurement departments purchasing hardware equipment in bulk."*
