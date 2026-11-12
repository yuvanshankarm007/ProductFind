"""
SSRF-Safe Pre-Click URL Verification Utility for ProductFind Sentinel.
Checks outbound merchant/citation links via lightweight HTTP HEAD -> GET probes
before the buyer clicks "Buy Now".
"""

import ipaddress
import socket
import time
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
import ssl

try:
    import certifi
    _FAST_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _FAST_SSL_CTX = True

_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}


def _is_safe_public_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if not host or host in _BLOCKED_HOSTS:
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            # Domain name — optionally guard obvious local suffixes
            if host.endswith(".local") or host.endswith(".internal"):
                return False
        return True
    except Exception:
        return False


async def verify_url_live(url: str, timeout_s: float = 2.5) -> Dict[str, Any]:
    """
    Verify an external merchant or citation URL with HEAD (fallback to streaming GET).
    Returns telemetry dict: {url, verified, reachable, http_status, final_url, latency_ms, verified_at}.
    """
    verified_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not url or not _is_safe_public_url(url):
        return {
            "url": url,
            "verified": False,
            "reachable": False,
            "http_status": None,
            "final_url": url,
            "latency_ms": 0,
            "verified_at": verified_at,
            "reason": "Blocked or non-public URL scheme/host",
        }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    t0 = time.perf_counter()
    status_code = None
    final_url = url
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_s),
            follow_redirects=True,
            verify=_FAST_SSL_CTX,
        ) as client:
            resp = await client.head(url, headers=headers)
            status_code = resp.status_code
            final_url = str(resp.url)
            if status_code in (403, 405, 501):
                async with client.stream("GET", url, headers=headers) as get_resp:
                    status_code = get_resp.status_code
                    final_url = str(get_resp.url)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "url": url,
            "verified": False,
            "reachable": False,
            "http_status": status_code,
            "final_url": final_url,
            "latency_ms": latency_ms,
            "verified_at": verified_at,
            "reason": str(exc)[:120],
        }

    latency_ms = int((time.perf_counter() - t0) * 1000)
    # 2xx / 3xx / anti-bot 403/429 on major retailers (Amazon/BestBuy) still prove the host/path exists;
    # 404 / 410 / 5xx indicates a dead or broken link.
    reachable = status_code is not None and status_code < 400
    not_dead = status_code is not None and status_code not in (404, 410) and status_code < 500
    return {
        "url": url,
        "verified": bool(not_dead),
        "reachable": bool(reachable),
        "http_status": status_code,
        "final_url": final_url,
        "latency_ms": latency_ms,
        "verified_at": verified_at,
    }


async def verify_urls_batch(urls: List[str], timeout_s: float = 2.0) -> Dict[str, Dict[str, Any]]:
    """Verify multiple unique URLs concurrently."""
    import asyncio
    unique_urls = [u for u in dict.fromkeys(urls) if u]
    if not unique_urls:
        return {}
    results = await asyncio.gather(*(verify_url_live(u, timeout_s=timeout_s) for u in unique_urls))
    return dict(zip(unique_urls, results))
