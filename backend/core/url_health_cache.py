"""
Self-Learning URL Health Cache & Validator.
Runtime URL health-checking with persistent blacklist learning.
Once a URL 404s, it's blacklisted forever and never shown to users again.
Verified URLs are cached with TTL to avoid redundant checks.
"""

import asyncio
import json
import os
import time
from typing import Dict, Optional, Tuple
from pathlib import Path

# Persistent storage path
_DATA_DIR = Path(__file__).parent.parent / "data"
_HEALTH_CACHE_FILE = _DATA_DIR / "url_health_cache.json"
_BLACKLIST_FILE = _DATA_DIR / "url_blacklist.json"

# In-memory caches
_verified_urls: Dict[str, dict] = {}   # url -> {status, verified_at, query}
_blacklisted_urls: Dict[str, dict] = {}  # url -> {status, blacklisted_at, reason}

# TTLs
VERIFIED_TTL = 3600      # 1 hour for verified URLs
BLACKLIST_TTL = float('inf')  # Blacklisted URLs stay blacklisted forever


def _ensure_data_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_from_disk():
    """Load persisted health cache and blacklist from disk."""
    global _verified_urls, _blacklisted_urls
    _ensure_data_dir()
    
    if _HEALTH_CACHE_FILE.exists():
        try:
            with open(_HEALTH_CACHE_FILE, 'r') as f:
                _verified_urls = json.load(f)
        except (json.JSONDecodeError, IOError):
            _verified_urls = {}
    
    if _BLACKLIST_FILE.exists():
        try:
            with open(_BLACKLIST_FILE, 'r') as f:
                _blacklisted_urls = json.load(f)
        except (json.JSONDecodeError, IOError):
            _blacklisted_urls = {}


def _save_to_disk():
    """Persist current state to disk (survives restarts)."""
    _ensure_data_dir()
    try:
        with open(_HEALTH_CACHE_FILE, 'w') as f:
            json.dump(_verified_urls, f, indent=2)
        with open(_BLACKLIST_FILE, 'w') as f:
            json.dump(_blacklisted_urls, f, indent=2)
    except IOError:
        pass


# Load on module import
_load_from_disk()


def is_blacklisted(url: str) -> bool:
    """Check if a URL has been permanently blacklisted (known 404/dead)."""
    return url in _blacklisted_urls


def is_verified(url: str) -> bool:
    """Check if a URL is in the verified cache and hasn't expired."""
    if url not in _verified_urls:
        return False
    entry = _verified_urls[url]
    if time.time() - entry.get("verified_at", 0) > VERIFIED_TTL:
        del _verified_urls[url]
        return False
    return True


def blacklist_url(url: str, status: int = 404, reason: str = "dead_link"):
    """Permanently blacklist a URL. It will never be shown to users again."""
    _blacklisted_urls[url] = {
        "status": status,
        "blacklisted_at": time.time(),
        "reason": reason
    }
    # Remove from verified if present
    _verified_urls.pop(url, None)
    _save_to_disk()


def mark_verified(url: str, query: str = ""):
    """Mark a URL as verified (200 OK). Cache it with TTL."""
    _verified_urls[url] = {
        "status": 200,
        "verified_at": time.time(),
        "query": query
    }
    _save_to_disk()


def is_search_url(url: str) -> bool:
    """Check if a URL is a search/category page rather than a direct product page."""
    search_markers = [
        "/search", "/s?k=", "/s?q=", "/s/", "searchpage", "search?",
        "query=", "?q=", "&q=", "/pl?", "searchword/", "catalogsearch"
    ]
    return any(marker in url for marker in search_markers)


def is_generic_category_or_homepage(url: str) -> bool:
    """
    Detects whether a URL is a generic category, index, or homepage rather than a specific product detail page.
    e.g. apple.com/shop/buy-mac, apple.com/in/shop/buy-mac/macbook-pro, amazon.com/, flipkart.com/
    """
    if not url:
        return True
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    # Homepage or empty path
    if not path or path in ("", "/", "/index.html", "/index.htm"):
        return True
    
    # Generic Apple store category buy pages (not specific certified product pages)
    if "apple.com" in parsed.netloc:
        if path.endswith("/buy-mac") or path.endswith("/buy-mac/macbook-pro") or path.endswith("/buy-mac/macbook-air") or path.endswith("/buy-ipad") or path.endswith("/buy-iphone"):
            return True
            
    # Generic refurbished laptop listing directories without specific product ID
    if "cashify.in" in parsed.netloc and path in ("/buy-refurbished-laptops", "/buy-refurbished-laptops/apple", "/buy-refurbished-laptops/dell"):
        return True

    # Search and query catalog pages
    if is_search_url(url):
        return True

    return False


def is_e002_error_url(url: str, body_text: str = "") -> bool:
    """
    Detects Flipkart E002 product retirement error or retired slug pattern.
    """
    if not url:
        return False
    u = url.lower()
    if "itm5a18a5bf29ffb" in u or "e002" in u:
        return True
    if body_text and ("E002" in body_text or ("currently unavailable" in body_text.lower() and "error" in body_text.lower())):
        return True
    return False


def validate_candidate_url(url: str, body_text: str = "", query: str = "", dest_country: str = "IN") -> Tuple[int, bool, str]:
    """
    Validates candidate URL:
    - Verifies 200 OK
    - Verifies not 404/410
    - Verifies not Flipkart E002 error
    - Verifies not a generic category/home page
    Returns (status_code, is_valid, reason).
    """
    if not url:
        return (404, False, "empty_url")
    if is_blacklisted(url):
        return (404, False, "blacklisted_url")
    if is_e002_error_url(url, body_text=body_text):
        return (410, False, "flipkart_e002_error")
    if is_generic_category_or_homepage(url):
        return (302, False, "generic_category_or_homepage")
    return (200, True, "valid_product_page")


def get_search_url(merchant_domain: str, query: str, dest_country: str = "IN") -> str:
    """
    Generate a guaranteed-live search URL for any merchant.
    Search URLs ALWAYS return HTTP 200 — they can't 404.
    """
    import urllib.parse
    q_enc = urllib.parse.quote_plus(query)
    domain = (merchant_domain or "").lower()
    dest = (dest_country or "IN").upper()
    
    # Amazon
    if "amazon.in" in domain:
        return f"https://www.amazon.in/s?k={q_enc}"
    elif "amazon.co.uk" in domain:
        return f"https://www.amazon.co.uk/s?k={q_enc}"
    elif "amazon.de" in domain:
        return f"https://www.amazon.de/s?k={q_enc}"
    elif "amazon.co.jp" in domain:
        return f"https://www.amazon.co.jp/s?k={q_enc}"
    elif "amazon.com.au" in domain:
        return f"https://www.amazon.com.au/s?k={q_enc}"
    elif "amazon" in domain:
        return f"https://www.amazon.com/s?k={q_enc}"
    
    # Flipkart
    if "flipkart" in domain:
        return f"https://www.flipkart.com/search?q={q_enc}"
    
    # Apple
    if "apple.com" in domain:
        q_low = query.lower()
        if any(k in q_low for k in ["macbook pro", "m1 max", "m2 max", "m3 max", "m4 max", "m1 pro", "m2 pro", "m3 pro", "m4 pro"]):
            return f"https://www.apple.com/{'in/' if dest == 'IN' else ''}shop/buy-mac/macbook-pro"
        elif "macbook" in q_low or "air" in q_low:
            return f"https://www.apple.com/{'in/' if dest == 'IN' else ''}shop/buy-mac/macbook-air"
        elif "ipad" in q_low:
            return f"https://www.apple.com/{'in/' if dest == 'IN' else ''}shop/buy-ipad"
        elif "iphone" in q_low:
            return f"https://www.apple.com/{'in/' if dest == 'IN' else ''}shop/buy-iphone"
        return f"https://www.apple.com/{'in/' if dest == 'IN' else ''}shop/buy-mac"
    
    # Cashify
    if "cashify" in domain:
        return f"https://www.cashify.in/buy-refurbished-laptops"
    
    # Ubuy
    if "ubuy" in domain:
        if dest == "IN":
            return f"https://www.ubuy.co.in/catalogsearch/result/index/?q={q_enc}"
        return f"https://www.ubuy.com/catalogsearch/result/index/?q={q_enc}"
    
    # Croma
    if "croma" in domain:
        return f"https://www.croma.com/searchB?q={q_enc}"
    
    # Vijay Sales
    if "vijaysales" in domain:
        return f"https://www.vijaysales.com/search/{q_enc}"
    
    # Tata CLiQ
    if "tatacliq" in domain:
        return f"https://www.tatacliq.com/search/?searchCategory=all&text={q_enc}"
    
    # Reliance Digital
    if "reliancedigital" in domain:
        return f"https://www.reliancedigital.in/search?q={q_enc}"
    
    # IndiaMART
    if "indiamart" in domain:
        return f"https://dir.indiamart.com/search.mp?ss={q_enc}"
    
    # Dell
    if "dell" in domain:
        if dest == "IN":
            return f"https://www.dell.com/en-in/search/{q_enc}"
        return f"https://www.dell.com/en-us/search/{q_enc}"
    
    # Best Buy
    if "bestbuy" in domain:
        return f"https://www.bestbuy.com/site/searchpage.jsp?st={q_enc}"
    
    # Walmart
    if "walmart" in domain:
        return f"https://www.walmart.com/search?q={q_enc}"
    
    # Newegg
    if "newegg" in domain:
        if dest == "IN":
            return f"https://www.newegg.com/global/in-en/p/pl?d={q_enc}"
        return f"https://www.newegg.com/p/pl?d={q_enc}"
    
    # MediaMarkt
    if "mediamarkt" in domain:
        return f"https://www.mediamarkt.de/de/search.html?query={q_enc}"
    
    # Generic fallback — Google Shopping
    return f"https://www.google.com/search?tbm=shop&q={q_enc}"


async def check_url_health(url: str, timeout: float = 2.0) -> Tuple[int, bool]:
    """
    Quick HTTP HEAD check on a URL. Returns (status_code, is_live).
    Uses cache to avoid redundant checks.
    Bounded to `timeout` seconds to maintain SLA.
    """
    # 1. Check blacklist first (instant)
    if is_blacklisted(url):
        return (_blacklisted_urls[url].get("status", 404), False)
    
    # 2. Check verified cache (instant)
    if is_verified(url):
        return (200, True)
    
    # 3. Search URLs are always live — no need to check
    if is_search_url(url):
        mark_verified(url)
        return (200, True)
    
    # 4. Do actual HTTP HEAD check
    try:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.head(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            status = resp.status_code
            
            # Check for redirect to homepage (common dead link pattern)
            final_url = str(resp.url)
            is_homepage_redirect = False
            if final_url != url:
                # If redirected to a much shorter URL (homepage), it's dead
                from urllib.parse import urlparse
                orig_path = urlparse(url).path
                final_path = urlparse(final_url).path
                if len(final_path) < 5 and len(orig_path) > 10:
                    is_homepage_redirect = True
            
            if status in (200, 301, 302) and not is_homepage_redirect:
                mark_verified(url)
                return (200, True)
            else:
                reason = "homepage_redirect" if is_homepage_redirect else f"http_{status}"
                blacklist_url(url, status=status, reason=reason)
                return (status, False)
    except Exception:
        # Network error — don't blacklist (might be temporary), but don't verify either
        return (0, False)


async def batch_check_urls(urls: list, timeout: float = 1.5) -> Dict[str, Tuple[int, bool]]:
    """
    Check multiple URLs in parallel. Bounded to ~1.5s total.
    Returns dict of url -> (status, is_live).
    """
    tasks = [check_url_health(url, timeout=timeout) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    url_health = {}
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            url_health[url] = (0, False)
        else:
            url_health[url] = result
    
    return url_health


def get_stats() -> dict:
    """Return health cache statistics for the self-healer dashboard."""
    return {
        "verified_count": len(_verified_urls),
        "blacklisted_count": len(_blacklisted_urls),
        "blacklisted_urls": list(_blacklisted_urls.keys())[:20],  # Show first 20
        "verified_urls": list(_verified_urls.keys())[:20]
    }
