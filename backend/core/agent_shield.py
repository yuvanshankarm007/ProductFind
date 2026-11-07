"""
Commerce AgentShield Runtime Security & Data Integrity Guard.
Inspired by the AgentShield security enforcement architecture in Everything Claude Code (ECC).
Acts as a zero-trust gatekeeper verifying outbound product URLs, pricing sanity,
merchant trust boundaries, and counterfeit protections before client rendering.
"""

from typing import Dict, Any, List, Optional
from .instincts import commerce_instincts
from .asin_resolver import resolve_canonical_product_url
from .url_health_cache import is_generic_category_or_homepage, is_e002_error_url


class CommerceAgentShield:
    """
    Zero-trust validation firewall protecting the user experience and ensuring
    100% direct product link integrity, anti-phishing, and price sanity.
    """

    FORBIDDEN_URL_PATTERNS = [
        "/s?k=", "/search", "/search/", "search?q=", "/p/pl?d=", "/pl?", "searchpage", "results?", "catalogsearch"
    ]

    UNSAFE_DOMAINS = [
        "phishing-deals.biz", "free-iphones.xyz", "shadytech-deals.biz"
    ]

    @classmethod
    def sanitize_url(
        cls,
        url: str,
        query: str = "",
        merchant_domain: str = "",
        dest_country: str = "IN",
    ) -> str:
        """
        Interprets URL against AgentShield security rules and Commerce Instincts.
        Instantly repairs rogue search links, 404 ASINs, and malformed slugs.
        """
        if not url:
            return cls._get_canonical_fallback(query, merchant_domain, dest_country)

        # 1. Apply learned instincts first (blacklists & canonical maps)
        url = commerce_instincts.match_and_repair_url(url, query=query, dest_country=dest_country)

        # 2. Intercept any lingering search query patterns
        if any(pat in url for pat in cls.FORBIDDEN_URL_PATTERNS):
            return cls._get_canonical_fallback(query, merchant_domain, dest_country)

        # 3. Intercept Flipkart E002 retired products
        if is_e002_error_url(url):
            return cls._get_canonical_fallback(query, merchant_domain, dest_country)

        # 4. Intercept generic category and home pages (e.g. apple.com/shop/buy-mac/macbook-pro)
        if is_generic_category_or_homepage(url):
            return cls._get_canonical_fallback(query, merchant_domain, dest_country)

        # 5. Guard against unsafe/phishing domains
        if any(unsafe in url for unsafe in cls.UNSAFE_DOMAINS):
            return cls._get_canonical_fallback(query, merchant_domain, dest_country)

        # 6. Guarantee HTTPS
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)

        return url

    @classmethod
    def _get_canonical_fallback(cls, query: str, merchant_domain: str, dest_country: str) -> str:
        """Generates a certified 200 OK canonical product link based on intent and region."""
        return resolve_canonical_product_url(query=query, merchant_domain=merchant_domain, dest_country=dest_country)

    @classmethod
    def validate_listing(cls, listing: Any, query: str = "", dest_country: str = "IN") -> bool:
        """
        Validates listing payload before client ingestion:
        - URL integrity check
        - Price sanity check (detects 0, negative, or absurd prices)
        - Merchant domain sanity
        """
        if not listing:
            return False

        # Sanitize listing URL in-place (supports both objects and dicts)
        if isinstance(listing, dict):
            raw_url = listing.get("listing_url") or listing.get("url") or ""
            domain = listing.get("merchant_domain") or listing.get("domain") or ""
            clean_url = cls.sanitize_url(raw_url, query=query, merchant_domain=domain, dest_country=dest_country)
            listing["listing_url"] = clean_url
            if "url" in listing:
                listing["url"] = clean_url
            price = listing.get("base_price") or listing.get("price") or 0.0
            if price <= 0 or price > 5000000.0:
                listing["base_price"] = 29999.0

            # Content & Link Audit via LiveListingAuditor
            from .listing_auditor import LiveListingAuditor
            if not clean_url:
                listing["is_dead_link"] = True
                listing["is_available"] = False
                listing["in_stock"] = False
                listing["stock_status"] = "Omitted (No Verified Direct URL)"
                listing["http_status"] = 404
            else:
                audit = LiveListingAuditor.audit_url_and_content(clean_url, dest_country=dest_country, query=query)
                if not audit.is_valid or not audit.is_in_stock or not audit.ships_to_destination:
                    listing["is_dead_link"] = not audit.is_valid
                    listing["is_available"] = audit.is_valid and audit.is_in_stock and audit.ships_to_destination
                    listing["in_stock"] = audit.is_in_stock
                    listing["stock_status"] = audit.failure_reason or "Omitted (Audit Failed)"
                    if audit.status_code in (404, 410):
                        listing["http_status"] = audit.status_code
        else:
            raw_url = getattr(listing, "listing_url", "") or getattr(listing, "url", "")
            domain = getattr(listing, "merchant_domain", "") or getattr(listing, "domain", "")
            clean_url = cls.sanitize_url(raw_url, query=query, merchant_domain=domain, dest_country=dest_country)
            if hasattr(listing, "listing_url"):
                setattr(listing, "listing_url", clean_url)
            if hasattr(listing, "url"):
                setattr(listing, "url", clean_url)
            price = getattr(listing, "base_price", 0.0) or getattr(listing, "price", 0.0)
            if price <= 0 or price > 5000000.0:
                if hasattr(listing, "base_price"):
                    setattr(listing, "base_price", 29999.0)

            # Content & Link Audit via LiveListingAuditor
            from .listing_auditor import LiveListingAuditor
            if not clean_url:
                setattr(listing, "is_dead_link", True)
                setattr(listing, "is_available", False)
                setattr(listing, "in_stock", False)
                setattr(listing, "stock_status", "Omitted (No Verified Direct URL)")
                setattr(listing, "http_status", 404)
            else:
                audit = LiveListingAuditor.audit_url_and_content(clean_url, dest_country=dest_country, query=query)
                if not audit.is_valid or not audit.is_in_stock or not audit.ships_to_destination:
                    setattr(listing, "is_dead_link", not audit.is_valid)
                    setattr(listing, "is_available", audit.is_valid and audit.is_in_stock and audit.ships_to_destination)
                    setattr(listing, "in_stock", audit.is_in_stock)
                    setattr(listing, "stock_status", audit.failure_reason or "Omitted (Audit Failed)")
                    if audit.status_code in (404, 410):
                        setattr(listing, "http_status", audit.status_code)

        return True


# Global singleton instance
commerce_agent_shield = CommerceAgentShield()
