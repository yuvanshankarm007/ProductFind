"""
Prompt-Driven Reflexion & Negative Constraint Learning Engine.
Inspired by Voyager / Reflexion Reinforcement Architecture.
Parses natural language user prompts and feedback to extract:
1. Clean search targets (stripping prompt meta-modifiers)
2. Negative constraints (e.g. "no 404s", "in stock only", "no scams", "no accessories")
3. Dynamically compiles learned constraints into durable Commerce Instincts.
"""

import re
import time
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class PromptConstraint(BaseModel):
    """Structured negative constraints extracted from user prompts or feedback."""
    raw_prompt: str
    clean_query: str
    in_stock_only: bool = False
    no_404_dead_links: bool = False
    anti_scam: bool = False
    no_accessories: bool = False
    min_trust_score: float = 75.0
    banned_domains: List[str] = Field(default_factory=list)
    banned_keywords: List[str] = Field(default_factory=list)
    detected_intent_tags: List[str] = Field(default_factory=list)
    max_budget: Optional[float] = None
    max_budget_currency: Optional[str] = None


class PromptLearnerEngine:
    """
    NLP and Heuristic parser for extracting negative constraints from user queries
    and synthesizing durable reflex instincts for the self-healing swarm.
    """

    # Patterns matching negative constraints & preferences in natural language
    OUT_OF_STOCK_PATTERNS = [
        r"\b(?:in\s*stock\s*only|no\s*out\s*of\s*stock|available\s*only|must\s*be\s*in\s*stock|exclude\s*out\s*of\s*stock|in\s*stock)\b",
        r"\b(?:not?\s*out\s*of\s*stock|dont?\s*show(?:\s*me)?\s*(?:any\s*)?out\s*of\s*stock|without\s*(?:any\s*)?out\s*of\s*stock|skip\s*out\s*of\s*stock|hide\s*out\s*of\s*stock)\b"
    ]

    DEAD_LINK_PATTERNS = [
        r"\b(?:no|without|zero|skip|exclude|avoid|dont?\s*show(?:\s*me)?|not|or)\s*(?:any\s*)?(?:404s?|dead\s*links?|broken\s*links?|expired\s*links?|404\s*dead\s*links?)\b",
        r"\b(?:working\s*links?\s*only|valid\s*urls?\s*only|live\s*links?\s*only)\b"
    ]

    ANTI_SCAM_PATTERNS = [
        r"\b(?:no|without|avoid|skip|exclude|dont?\s*show(?:\s*me)?)\s*(?:any\s*)?(?:scams?|scam\s*stores?|shady\s*(?:sellers?|stores?|merchants?)|fraud|sketchy\s*(?:sellers?|stores?)|fake\s*products?)\b",
        r"\b(?:reputable\s*(?:sellers?|stores?|merchants?)|verified\s*only|trusted\s*only|safe\s*sellers?|authentic\s*only|official\s*stores?\s*only|genuine\s*only|no\s*counterfeits?)\b"
    ]

    ACCESSORY_HIJACK_PATTERNS = [
        r"\b(?:no|without|skip|exclude|avoid)\s*(?:any\s*)?(?:accessories|parts|brush\s*rollers?|cables?|cases?|covers?|lens\s*bundles?)\b",
        r"\b(?:full\s*(?:unit|product|laptop|headphones|camera)\s*only|actual\s*product\s*only|not?\s*an?\s*accessory|body\s*only)\b"
    ]

    REFURBISHED_PATTERNS = [
        r"\b(?:no|without|skip|exclude|avoid|dont?\s*show(?:\s*me)?|never)\s*(?:any\s*)?(?:refurbished|renewed|pre-owned|used|refurb)\b",
        r"\b(?:brand\s*new\s*only|new\s*only)\b"
    ]

    # Explicit domain ban pattern: e.g. "no ebay", "exclude indiamart", "ban shady-store.com", "do not show scam.com"
    DOMAIN_BAN_PATTERN = r"\b(?:no|exclude|ban|avoid|skip|block|do not show|don't show|dont show|filter out|without)\s+([a-zA-Z0-9.-]+\.(?:com|in|org|net|biz|co|co\.in))\b"

    @classmethod
    def parse_and_learn_from_prompt(
        cls,
        raw_prompt: str,
        instincts_vault: Optional[Any] = None
    ) -> Tuple[str, PromptConstraint, List[Dict[str, Any]]]:
        """
        Parses raw user input, extracts clean search target, activates negative constraints,
        and dynamically synthesizes newly learned instincts into the CommerceInstinctsVault.
        """
        prompt_lower = (raw_prompt or "").lower().strip()
        tags: List[str] = []
        banned_domains: List[str] = []

        in_stock = False
        no_404 = False
        anti_scam = False
        no_accessories = False

        cleaned = raw_prompt

        # 1. Detect and strip Out-of-Stock modifiers
        for pat in cls.OUT_OF_STOCK_PATTERNS:
            if re.search(pat, prompt_lower):
                in_stock = True
                tags.append("IN_STOCK_ENFORCED")
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 2. Detect and strip 404 / Dead-Link modifiers
        for pat in cls.DEAD_LINK_PATTERNS:
            if re.search(pat, prompt_lower):
                no_404 = True
                tags.append("ZERO_404_ACTIVE")
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 3. Detect and strip Scam / Fraud modifiers
        for pat in cls.ANTI_SCAM_PATTERNS:
            if re.search(pat, prompt_lower):
                anti_scam = True
                tags.append("ANTI_SCAM_SHIELD")
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 4. Detect and strip Accessory modifiers
        for pat in cls.ACCESSORY_HIJACK_PATTERNS:
            if re.search(pat, prompt_lower):
                no_accessories = True
                tags.append("ANTI_ACCESSORY_HIJACK")
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 4.5 Detect and strip Refurbished modifiers
        for pat in cls.REFURBISHED_PATTERNS:
            if re.search(pat, prompt_lower):
                tags.append("NO_REFURBISHED")
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 5. Extract specific domain bans
        domain_matches = re.findall(cls.DOMAIN_BAN_PATTERN, prompt_lower)
        for dom in domain_matches:
            banned_domains.append(dom)
            tags.append(f"BANNED_DOMAIN:{dom}")
            cleaned = re.sub(rf"\b(?:no|exclude|ban|avoid|skip|block|do not show|don't show|dont show|filter out|without)\s+{re.escape(dom)}\b", "", cleaned, flags=re.IGNORECASE)

        # 5.5 Extract natural language budget limits (e.g. "under 50k", "under 50000", "below ₹50,000", "under $800")
        max_budget: Optional[float] = None
        max_budget_curr: Optional[str] = None

        budget_patterns = [
            r"\b(?:under|below|within|less than|max(?:imum)?(?: price)?(?: of)?|budget(?: of)?)\s*(?:₹|rs\.?|inr|\$|usd|eur|€|£|gbp)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(k|lakh|lac|thousand)?\b",
            r"(?:₹|rs\.?|inr|\$|usd|eur|€|£|gbp)\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(k|lakh|lac|thousand)?\s*(?:under|below|budget|max|or less)\b",
            r"\b(?:<|<=)\s*(?:₹|rs\.?|inr|\$|usd|eur|€|£|gbp)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(k|lakh|lac|thousand)?\b"
        ]

        for b_pat in budget_patterns:
            m_budget = re.search(b_pat, prompt_lower)
            if m_budget:
                raw_val = m_budget.group(1).replace(",", "")
                multiplier_str = (m_budget.group(2) or "").lower()
                try:
                    val = float(raw_val)
                    if multiplier_str in ["k", "thousand"]:
                        val *= 1000.0
                    elif multiplier_str in ["lakh", "lac"]:
                        val *= 100000.0
                    max_budget = val
                    if any(c in prompt_lower for c in ["₹", "rs", "inr"]):
                        max_budget_curr = "INR"
                    elif any(c in prompt_lower for c in ["$", "usd"]):
                        max_budget_curr = "USD"
                    elif any(c in prompt_lower for c in ["€", "eur"]):
                        max_budget_curr = "EUR"
                    elif any(c in prompt_lower for c in ["£", "gbp"]):
                        max_budget_curr = "GBP"

                    tags.append(f"BUDGET_CAP:{int(val)}")
                    cleaned = re.sub(b_pat, "", cleaned, flags=re.IGNORECASE)
                    break
                except Exception:
                    pass

        # Clean extraneous commas, semicolons, pipes, and whitespace (preserving alphanumeric symbols like + in DS923+)
        clean_query = re.sub(r'[\,\;\|]+', ' ', cleaned)
        clean_query = re.sub(r'\s+\+\s+', ' ', clean_query)
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()

        # If stripping removed everything (e.g. user just typed "in stock only no 404s"), keep reasonable fallback
        if not clean_query:
            clean_query = "Dell Precision 7820 Workstation"

        # Construct constraints model reflecting user prompt directives
        constraint = PromptConstraint(
            raw_prompt=raw_prompt,
            clean_query=clean_query,
            in_stock_only=bool(in_stock),
            no_404_dead_links=bool(no_404),
            anti_scam=bool(anti_scam),
            no_accessories=bool(no_accessories),
            min_trust_score=80.0 if anti_scam else 75.0,
            banned_domains=banned_domains,
            detected_intent_tags=tags or ["STANDARD_SEARCH"],
            max_budget=max_budget,
            max_budget_currency=max_budget_curr
        )

        newly_learned: List[Dict[str, Any]] = []

        # 6. Dynamically register new instincts in the vault if available
        if instincts_vault:
            if in_stock:
                inst = instincts_vault.record_prompt_instinct(
                    prompt_text=raw_prompt,
                    category="PROMPT_CONSTRAINT_IN_STOCK",
                    pattern="out_of_stock_prohibited",
                    reason="Learned from user prompt: Strictly purge out-of-stock products. Only 100% in-stock inventory permitted."
                )
                newly_learned.append(inst.model_dump())

            if no_404:
                inst = instincts_vault.record_prompt_instinct(
                    prompt_text=raw_prompt,
                    category="PROMPT_CONSTRAINT_ZERO_404",
                    pattern="404_dead_links_prohibited",
                    reason="Learned from user prompt: Strictly quarantine any HTTP 404 or dead link before UI rendering."
                )
                newly_learned.append(inst.model_dump())

            if anti_scam:
                inst = instincts_vault.record_prompt_instinct(
                    prompt_text=raw_prompt,
                    category="PROMPT_CONSTRAINT_ANTI_SCAM",
                    pattern="scam_merchant_prohibited",
                    reason="Learned from user prompt: Enforce minimum 80/100 merchant trust threshold and verify PayPal Buyer Protection."
                )
                newly_learned.append(inst.model_dump())

            for dom in banned_domains:
                inst = instincts_vault.record_prompt_instinct(
                    prompt_text=raw_prompt,
                    category="USER_QUARANTINE_MERCHANT",
                    pattern=dom,
                    reason=f"Learned from user prompt: Permanently blacklisted domain '{dom}' based on user directive."
                )
                newly_learned.append(inst.model_dump())

        return clean_query, constraint, newly_learned
