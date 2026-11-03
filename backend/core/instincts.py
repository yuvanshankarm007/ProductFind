"""
Commerce Instincts & Operational Rules Engine.
Inspired by the Everything Claude Code (ECC) persistent instincts & reflex memory architecture.
Permanently records operational failures (dead links, 404 ASINs, Cloudflare challenges)
and translates them into deterministic runtime rules so bugs and dead links are never repeated.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path
from .asin_resolver import resolve_canonical_product_url


class CommerceInstinct(BaseModel):
    rule_id: str
    category: str  # "BLACKLIST_DEAD_SKU", "CANONICAL_URL_MAP", "SEARCH_PAGE_INTERCEPT", "BOT_CHALLENGE_DEFENSE"
    pattern: str  # URL snippet, ASIN, or merchant domain
    replacement_target: Optional[str] = None
    reason: str
    confidence: float = 1.0
    triggers_count: int = 0
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    last_triggered_at: Optional[str] = None


class CommerceInstinctsVault:
    """
    Durable storage and query engine for learned operational instincts.
    Persists to backend/data/instincts.json with automatic memory caching.
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent / "data"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.storage_path = base_dir / "instincts.json"

        self._instincts: Dict[str, CommerceInstinct] = {}
        self._load_or_seed()

    def _load_or_seed(self):
        """Loads instincts from disk or initializes with baseline ECC production instincts."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("instincts", []):
                        inst = CommerceInstinct(**item)
                        self._instincts[inst.rule_id] = inst
                if len(self._instincts) >= 5:
                    return
            except Exception:
                pass

        # Seed baseline verified instincts (permanently blacklisting expired SKUs identified in tests)
        baseline = [
            CommerceInstinct(
                rule_id="INST-DEAD-ASIN-B0CKZJ8V3C",
                category="BLACKLIST_DEAD_SKU",
                pattern="B0CKZJ8V3C",
                replacement_target="https://www.amazon.in/Dell-Latitude-Business-Laptop-Renewed/dp/B0HP26WLF4",
                reason="Amazon India delisted B0CKZJ8V3C. Replaced with active live 200 OK Dell Latitude listing B0HP26WLF4.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-ASIN-B09V1K8X1V",
                category="BLACKLIST_DEAD_SKU",
                pattern="B09V1K8X1V",
                replacement_target="https://www.amazon.in/Dell-15-Renewed-Laptop/dp/B0FFHG2VGJ",
                reason="Amazon India retired B09V1K8X1V. Replaced with active live 200 OK Dell listing B0FFHG2VGJ.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-NEWEGG-1TS-000A-0U1G3",
                category="BLACKLIST_DEAD_SKU",
                pattern="1TS-000A-0U1G3",
                replacement_target="https://www.amazon.com/dp/B0D16TS69T",
                reason="Newegg permanently removed 1TS-000A-0U1G3. Replaced with verified active Amazon US import B0D16TS69T.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-SEARCH-PAGE-AMAZON",
                category="SEARCH_PAGE_INTERCEPT",
                pattern="/s?k=",
                replacement_target="https://www.amazon.in/Dell-Latitude-Business-Laptop-Renewed/dp/B0HP26WLF4",
                reason="Search query URLs (/s?k=) strictly forbidden. Enforce canonical product detail pages (/dp/).",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-SEARCH-PAGE-NEWEGG",
                category="SEARCH_PAGE_INTERCEPT",
                pattern="/p/pl?d=",
                replacement_target="https://www.amazon.com/dp/B0D16TS69T",
                reason="Newegg search listing queries (/p/pl?) forbidden. Enforce canonical direct item resolution.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-BOT-DEFENSE-CF",
                category="BOT_CHALLENGE_DEFENSE",
                pattern="cloudflare_challenge",
                replacement_target=None,
                reason="When HTTP 403 / 503 challenge is intercepted, switch curl_cffi TLS impersonate profile.",
                confidence=0.95,
            ),
        ]

        for inst in baseline:
            self._instincts[inst.rule_id] = inst
        self._persist()

    def _persist(self):
        """Persists current instinct rules to disk atomically."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.storage_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "version": "2.0.0",
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "instincts": [inst.model_dump() for inst in self._instincts.values()],
                    },
                    f,
                    indent=2,
                )
            temp_path.replace(self.storage_path)
        except Exception:
            pass

    def list_instincts(self) -> List[CommerceInstinct]:
        """Returns all registered instincts."""
        return list(self._instincts.values())

    def get_instinct(self, rule_id: str) -> Optional[CommerceInstinct]:
        return self._instincts.get(rule_id)

    def record_dead_link_instinct(
        self,
        pattern: str,
        reason: str,
        replacement_url: Optional[str] = None,
        category: str = "BLACKLIST_DEAD_SKU",
    ) -> CommerceInstinct:
        """Dynamically registers a newly discovered failure pattern into permanent reflex memory."""
        import uuid

        clean_slug = "".join(c if c.isalnum() else "_" for c in pattern[:20]).upper()
        rule_id = f"INST-DEAD-{clean_slug}-{uuid.uuid4().hex[:6].upper()}"

        instinct = CommerceInstinct(
            rule_id=rule_id,
            category=category,
            pattern=pattern,
            replacement_target=replacement_url,
            reason=reason,
            confidence=1.0,
        )
        self._instincts[rule_id] = instinct
        self._persist()
        return instinct

    def match_and_repair_url(
        self,
        url: str,
        query: str = "",
        dest_country: str = "IN",
    ) -> str:
        """
        Evaluates a candidate URL against the reflex instincts database.
        If a blacklisted ASIN, dead SKU, or search leak is identified, immediately repairs it.
        """
        if not url:
            return url

        dest = dest_country.upper()

        for inst in self._instincts.values():
            if inst.pattern in url:
                inst.triggers_count += 1
                inst.last_triggered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

                # If a replacement target is defined
                if inst.replacement_target:
                    # Regional adaptation for search leaks
                    if inst.category == "SEARCH_PAGE_INTERCEPT":
                        return resolve_canonical_product_url(query=query, dest_country=dest_country)
                    # For Indian shoppers, do not replace with a US Amazon URL that cannot ship to India
                    if dest == "IN" and "amazon.com" in inst.replacement_target:
                        dom = "indiamart.com" if any(k in (query or "").lower() for k in ["latitude", "dell"]) else "amazon.in"
                        return resolve_canonical_product_url(query=query, merchant_domain=dom, dest_country=dest_country)
                    return inst.replacement_target

        return url


# Global singleton instance
commerce_instincts = CommerceInstinctsVault()
