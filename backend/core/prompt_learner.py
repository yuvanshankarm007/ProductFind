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


class PromptLearnerEngine:
    """
    NLP and Heuristic parser for extracting negative constraints from user queries
    and synthesizing durable reflex instincts for the self-healing swarm.
    """

    # Patterns matching negative constraints & preferences in natural language
    OUT_OF_STOCK_PATTERNS = [
        r"\b(in\s*stock\s*only|no\s*out\s*of\s*stock|available\s*only|must\s*be\s*in\s*stock|exclude\s*out\s*of\s*stock|in\s*stock)\b",
        r"\b(not?\s*out\s*of\s*stock|dont?\s*show\s*out\s*of\s*stock)\b"
    ]

    DEAD_LINK_PATTERNS = [
        r"\b(no\s*404s?|no\s*dead\s*links?|working\s*links?\s*only|zero\s*404|exclude\s*404s?|valid\s*urls?\s*only)\b",
        r"\b(dont?\s*give\s*me\s*404|no\s*broken\s*links?)\b"
    ]

    ANTI_SCAM_PATTERNS = [
        r"\b(no\s*scams?|avoid\s*scams?|reputable\s*(?:sellers?|stores?|merchants?)|verified\s*only|trusted\s*only|no\s*shady|safe\s*sellers?)\b",
        r"\b(no\s*counterfeits?|authentic\s*only|official\s*stores?\s*only|genuine\s*only)\b"
    ]

    ACCESSORY_HIJACK_PATTERNS = [
        r"\b(no\s*accessories|no\s*parts|full\s*(?:unit|product|laptop|headphones)\s*only|no\s*brush\s*rollers?|no\s*cables?)\b",
        r"\b(actual\s*product\s*only|not?\s*an?\s*accessory)\b"
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

        # 5. Extract specific domain bans
        domain_matches = re.findall(cls.DOMAIN_BAN_PATTERN, prompt_lower)
        for dom in domain_matches:
            banned_domains.append(dom)
            tags.append(f"BANNED_DOMAIN:{dom}")
            cleaned = re.sub(rf"\b(?:no|exclude|ban|avoid|skip|block|do not show|don't show|dont show|filter out|without)\s+{re.escape(dom)}\b", "", cleaned, flags=re.IGNORECASE)

        # Clean extraneous commas, hyphens, and whitespace
        clean_query = re.sub(r'[\,\;\|\+]+', ' ', cleaned)
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
            detected_intent_tags=tags or ["STANDARD_SEARCH"]
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
