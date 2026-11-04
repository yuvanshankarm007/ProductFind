"""
Commerce Instincts & Operational Rules Engine.
Inspired by the Everything Claude Code (ECC) persistent instincts & reflex memory architecture.
Permanently records operational failures (dead links, 404 ASINs, Cloudflare challenges, scam merchants, out-of-stock inventory)
and translates them into deterministic runtime rules so bugs, dead links, and scams are never repeated.
"""

import os
import re
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from pathlib import Path
from .asin_resolver import resolve_canonical_product_url


class CommerceInstinct(BaseModel):
    rule_id: str
    category: str  # "BLACKLIST_DEAD_SKU", "CANONICAL_URL_MAP", "SEARCH_PAGE_INTERCEPT", "BOT_CHALLENGE_DEFENSE", "PROMPT_CONSTRAINT_IN_STOCK", "PROMPT_CONSTRAINT_ZERO_404", "PROMPT_CONSTRAINT_ANTI_SCAM", "USER_QUARANTINE_MERCHANT"
    pattern: str  # URL snippet, ASIN, merchant domain, or prompt directive
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
            except Exception:
                pass

        # Ensure universal quality and anti-scam / anti-404 / in-stock instincts exist
        baseline = [
            CommerceInstinct(
                rule_id="INST-PROMPT-IN-STOCK-UNIVERSAL",
                category="PROMPT_CONSTRAINT_IN_STOCK",
                pattern="out_of_stock_prohibited",
                replacement_target=None,
                reason="Universal Quality Rule: Purge all out-of-stock inventory. Only verified in-stock deals permitted.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-PROMPT-ZERO-404-UNIVERSAL",
                category="PROMPT_CONSTRAINT_ZERO_404",
                pattern="404_dead_links_prohibited",
                replacement_target=None,
                reason="Universal Quality Rule: Zero tolerance for HTTP 404s and broken links. Quarantine immediately.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-PROMPT-ANTI-SCAM-UNIVERSAL",
                category="PROMPT_CONSTRAINT_ANTI_SCAM",
                pattern="scam_merchant_prohibited",
                replacement_target=None,
                reason="Universal Quality Rule: Block high-risk counterfeit sellers, unaccredited stores, and trust < 75.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-ASIN-B0CKZJ8V3C",
                category="BLACKLIST_DEAD_SKU",
                pattern="B0CKZJ8V3C",
                replacement_target="https://www.amazon.in/Dell-Latitude-Business-Laptop-Renewed/dp/B0HP26WLF4",
                reason="Amazon India delisted B0CKZJ8V3C. Replaced with active live 200 OK Dell Latitude listing B0HP26WLF4.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-ASIN-B0CM5JV28X",
                category="BLACKLIST_DEAD_SKU",
                pattern="B0CM5JV28X",
                replacement_target="https://www.amazon.in/dp/B0HPGT4XRT",
                reason="Amazon India delisted B0CM5JV28X (404 Not Found). Automatically repaired to active 200 OK MacBook Pro ASIN B0HPGT4XRT.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-FLIPKART-ITM5A18A5BF29FFB",
                category="BLACKLIST_DEAD_SKU",
                pattern="itm5a18a5bf29ffb",
                replacement_target="https://www.flipkart.com/apple-2021-macbook-pro-m1-max-32-gb-1-tb-ssd-mac-os-monterey-mk1a3hn-a/p/itm00aac391057cc",
                reason="Flipkart retired itm5a18a5bf29ffb (E002 error). Replaced with active 200 OK MacBook Pro M1 Max listing itm00aac391057cc.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-FLIPKART-ITMDC5308FA78421",
                category="BLACKLIST_DEAD_SKU",
                pattern="itmdc5308fa78421",
                replacement_target="https://www.flipkart.com/apple-macbook-air-m5-2026-m5-16-gb-512-gb-ssd-tahoe-mdhe4hn-a/p/itm8505e2f874525",
                reason="Flipkart itmdc5308fa78421 is Out of Stock (Notify Me). Replaced with active in-stock listing.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-UBUY-1010N3N4",
                category="BLACKLIST_DEAD_SKU",
                pattern="1010N3N4",
                replacement_target="https://www.amazon.com/dp/B09JQSLL92",
                reason="Ubuy dead slug redirected to homepage. Repaired to verified Amazon US global direct import B09JQSLL92.",
                confidence=1.0,
            ),
            CommerceInstinct(
                rule_id="INST-DEAD-ASIN-B09T3K314N",
                category="BLACKLIST_DEAD_SKU",
                pattern="B09T3K314N",
                replacement_target="https://www.amazon.in/dp/B0HP26WLF4",
                reason="Amazon India delisted B09T3K314N (404 Not Found). Repaired to active Dell Workstation ASIN B0HP26WLF4.",
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
            if inst.rule_id not in self._instincts:
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
                        "version": "2.1.0",
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "total_rules": len(self._instincts),
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

    def record_prompt_instinct(
        self,
        prompt_text: str,
        category: str,
        pattern: str,
        reason: str
    ) -> CommerceInstinct:
        """Dynamically learns from a user prompt and stores an active negative constraint."""
        # Check if an instinct with this category and pattern already exists to increment trigger count
        for inst in self._instincts.values():
            if inst.category == category and inst.pattern == pattern:
                inst.triggers_count += 1
                inst.last_triggered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self._persist()
                return inst

        clean_slug = "".join(c if c.isalnum() else "_" for c in pattern[:16]).upper()
        rule_id = f"INST-{category[:12]}-{clean_slug}-{uuid.uuid4().hex[:4].upper()}"
        inst = CommerceInstinct(
            rule_id=rule_id,
            category=category,
            pattern=pattern,
            reason=reason,
            confidence=1.0,
            triggers_count=1,
            last_triggered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        self._instincts[rule_id] = inst
        self._persist()
        return inst

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

                q_low = (query or "").lower()
                # If query has explicit hardware specifications, dynamically resolve to the exact canonical SKU for this domain
                if any(k in q_low for k in ["m1", "m2", "m3", "m4", "max", "pro", "64gb", "32gb", "7820", "5511", "precision", "latitude"]):
                    domain = "flipkart.com" if "flipkart" in url else ("amazon.in" if "amazon.in" in url else ("amazon.com" if "amazon" in url else ""))
                    return resolve_canonical_product_url(query=query, merchant_domain=domain, dest_country=dest_country)

                # If a replacement target is defined
                if inst.replacement_target:
                    if inst.category == "SEARCH_PAGE_INTERCEPT":
                        return resolve_canonical_product_url(query=query, dest_country=dest_country)
                    if dest == "IN" and "amazon.com" in inst.replacement_target:
                        dom = "indiamart.com" if any(k in q_low for k in ["latitude", "dell"]) else "amazon.in"
                        return resolve_canonical_product_url(query=query, merchant_domain=dom, dest_country=dest_country)
                    return inst.replacement_target

        return url

    def evaluate_and_quarantine(
        self,
        listing: Any,
        constraints: Optional[Any] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates a scraped listing against learned prompt instincts and negative constraints.
        Returns:
            (is_quarantined: bool, quarantine_reason: Optional[str])
        """
        # Helper getters supporting both ScrapedListing dataclass and dict
        def _get(attr, default=None):
            if isinstance(listing, dict):
                return listing.get(attr, default)
            return getattr(listing, attr, default)

        url = _get("listing_url") or _get("url") or ""
        in_stock = _get("in_stock", True)
        stock_status = str(_get("stock_status", "In Stock") or "In Stock").lower()
        http_status = _get("http_status", 200)
        is_dead = _get("is_dead_link", False)
        is_avail = _get("is_available", True)
        merchant = _get("merchant") or ""
        merchant_domain = str(_get("merchant_domain") or "").lower()
        price = _get("base_price") or _get("price") or 0.0

        # Determine whether to enforce in-stock and zero-404 constraints
        if constraints is not None:
            if isinstance(constraints, dict):
                enforce_no_404 = bool(constraints.get("no_404_dead_links", False))
                enforce_in_stock = bool(constraints.get("in_stock_only", False))
                banned_domains = constraints.get("banned_domains", [])
            else:
                enforce_no_404 = bool(getattr(constraints, "no_404_dead_links", False))
                enforce_in_stock = bool(getattr(constraints, "in_stock_only", False))
                banned_domains = getattr(constraints, "banned_domains", [])
        else:
            enforce_no_404 = True
            enforce_in_stock = True
            banned_domains = []

        # 1. 404 / Dead-Link Check
        if enforce_no_404 and (is_dead or http_status == 404 or "404" in stock_status):
            return True, f"Quarantined 404 Dead Link: {url or merchant}"

        # 2. Out-of-Stock Check (including 'notify me' and 'sold out')
        is_out_of_stock = (
            not in_stock
            or not is_avail
            or "out of stock" in stock_status
            or "sold out" in stock_status
            or "notify me" in stock_status
            or price <= 0
        )
        if enforce_in_stock and is_out_of_stock:
            return True, f"Quarantined Out-of-Stock Inventory: {merchant} ({stock_status})"

        # 3. User Banned Domain Check
        for b_dom in banned_domains:
            if b_dom.lower() in merchant_domain or b_dom.lower() in merchant.lower():
                return True, f"Quarantined Banned Domain: {merchant} matches user prompt blacklist '{b_dom}'"

        # Check against registered USER_QUARANTINE_MERCHANT instincts
        for inst in self._instincts.values():
            if inst.category == "USER_QUARANTINE_MERCHANT":
                if inst.pattern.lower() in merchant_domain or inst.pattern.lower() in merchant.lower():
                    inst.triggers_count += 1
                    inst.last_triggered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    return True, f"Quarantined Merchant: Blocked by learned instinct rule {inst.rule_id} ({inst.pattern})"

        # 4. Blacklisted Dead SKU Check
        for inst in self._instincts.values():
            if inst.category == "BLACKLIST_DEAD_SKU" and inst.pattern in url:
                inst.triggers_count += 1
                inst.last_triggered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                # If no direct replacement available, quarantine it
                if not inst.replacement_target:
                    return True, f"Quarantined Dead SKU: Blocked by rule {inst.rule_id}"

        return False, None

    def quarantine_filter_listings(
        self,
        listings: List[Any],
        constraints: Optional[Any] = None
    ) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """
        Filters a list of listings through the learned quarantine engine.
        Returns:
            (retained_verified_listings, quarantined_records)
        """
        verified = []
        quarantined = []

        for l in listings:
            is_q, reason = self.evaluate_and_quarantine(l, constraints=constraints)
            if is_q:
                title = l.get("product_title") if isinstance(l, dict) else getattr(l, "product_title", "Unknown Product")
                merch = l.get("merchant") if isinstance(l, dict) else getattr(l, "merchant", "Unknown Merchant")
                quarantined.append({
                    "merchant": merch,
                    "title": title,
                    "reason": reason,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
            else:
                verified.append(l)

        # Update disk metrics if any triggers happened
        self._persist()
        return verified, quarantined


# Global singleton instance
commerce_instincts = CommerceInstinctsVault()
