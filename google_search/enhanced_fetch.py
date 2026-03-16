#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced web fetch with SSRF protection, caching, and content extraction
Reference: OpenClaw web-fetch implementation
"""

import socket
import ipaddress
from urllib3.util import parse_url
from urllib.parse import urlparse
import time
import hashlib
import json
from typing import Optional, Dict, Any, Tuple

import requests
from bs4 import BeautifulSoup

logger = __import__("logging").getLogger(__name__)

# ============ Constants ============
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_CHARS = 50_000
DEFAULT_MAX_RESPONSE_BYTES = 2_000_000
DEFAULT_MAX_REDIRECTS = 3
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes
CHROME_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Blocked hostnames
BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
}

# Memory cache
FETCH_CACHE: Dict[str, Dict[str, Any]] = {}


# ============ SSRF Protection ============


def is_private_ip_address(ip: str) -> bool:
    """Check if IP is private/internal/special-use"""
    try:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
        )
    except ValueError:
        return True  # Fail closed for invalid IPs


def is_blocked_hostname(hostname: str) -> bool:
    """Check if hostname is blocked"""
    normalized = hostname.lower().strip()

    if normalized in BLOCKED_HOSTNAMES:
        return True

    blocked_suffixes = (".localhost", ".local", ".internal")
    if normalized.endswith(blocked_suffixes):
        return True

    return False


def assert_public_hostname(hostname: str) -> None:
    """Assert hostname is public (not blocked)"""
    if is_blocked_hostname(hostname):
        raise ValueError(f"Blocked hostname: {hostname}")

    try:
        addresses = socket.getaddrinfo(
            hostname, None, socket.AF_INET, socket.SOCK_STREAM
        )
        for family, socktype, proto, canonname, sockaddr in addresses:
            ip = sockaddr[0]
            if is_private_ip_address(ip):
                raise ValueError(f"Blocked: {hostname} resolves to private IP {ip}")
    except socket.gaierror as e:
        raise ValueError(f"DNS resolution failed: {hostname}") from e


def create_ssrf_protected_session() -> requests.Session:
    """Create a requests session with SSRF protection"""
    session = requests.Session()

    original_send = session.send

    def wrapped_send(request, **kwargs):
        parsed = urlparse(request.url)
        hostname = parsed.hostname

        if hostname:
            assert_public_hostname(hostname)

        return original_send(request, **kwargs)

    session.send = wrapped_send
    return session


# ============ Content Extraction ============


def html_to_markdown(html: str) -> Tuple[str, Optional[str]]:
    """Simple HTML to Markdown converter"""
    title = None
    title_match = BeautifulSoup(html, "lxml").title
    if title_match and title_match.string:
        title = title_match.string.strip()

    text = html
    text = BeautifulSoup(text, "lxml").get_text(separator="\n", strip=True)
    text = "\n".join([line for line in text.split("\n") if line.strip()])

    return text, title


def extract_readability_content(
    html: str, url: str, extract_mode: str = "markdown"
) -> Optional[Dict[str, Any]]:
    """
    Extract readable content from HTML using simple heuristics
    Fallback to basic extraction if fails
    """
    MAX_HTML_CHARS = 1_000_000

    if len(html) > MAX_HTML_CHARS:
        html = html[:MAX_HTML_CHARS]

    try:
        soup = BeautifulSoup(html, "lxml")

        title = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        for tag in soup(
            ["script", "style", "noscript", "iframe", "nav", "footer", "header"]
        ):
            tag.decompose()

        main_content = None
        for selector in [
            "article",
            "main",
            ".post-content",
            ".article-content",
            ".content",
        ]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = soup.body if soup.body else soup

        text = main_content.get_text(separator="\n", strip=True)
        text = "\n".join([line for line in text.split("\n") if line.strip()])

        if extract_mode == "text":
            text = text[:DEFAULT_MAX_CHARS]

        return {
            "text": text,
            "title": title,
        }
    except Exception as e:
        logger.warning(f"Readability extraction failed: {e}")
        return None


def truncate_text(value: str, max_chars: int) -> Tuple[str, bool]:
    """Truncate text to max_chars"""
    if len(value) <= max_chars:
        return value, False
    return value[:max_chars], True


# ============ Cache ============


def normalize_cache_key(key: str) -> str:
    """Normalize cache key"""
    return hashlib.md5(key.encode()).hexdigest()


def read_cache(key: str) -> Optional[Dict[str, Any]]:
    """Read from cache"""
    entry = FETCH_CACHE.get(key)
    if not entry:
        return None

    if time.time() > entry.get("expires_at", 0):
        FETCH_CACHE.pop(key, None)
        return None

    return entry.get("value")


def write_cache(
    key: str, value: Dict[str, Any], ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
) -> None:
    """Write to cache"""
    FETCH_CACHE[key] = {
        "value": value,
        "expires_at": time.time() + ttl_seconds,
    }

    while len(FETCH_CACHE) > 100:
        oldest_key = min(FETCH_CACHE.keys(), key=lambda k: FETCH_CACHE[k]["expires_at"])
        FETCH_CACHE.pop(oldest_key, None)


# ============ Main Fetch Function ============


def fetch_url(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    extract_mode: str = "markdown",
    use_cache: bool = True,
    cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
) -> Dict[str, Any]:
    """
    Fetch URL content with SSRF protection, caching, and content extraction

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_chars: Maximum characters to return
        max_redirects: Maximum redirects to follow
        extract_mode: "markdown" or "text"
        use_cache: Enable caching
        cache_ttl: Cache TTL in seconds

    Returns:
        Dict with content or error
    """
    start_time = time.time()

    if use_cache:
        cache_key = normalize_cache_key(f"fetch:{url}:{extract_mode}:{max_chars}")
        cached = read_cache(cache_key)
        if cached:
            cached["cached"] = True
            logger.info(f"[fetch_url] Cache hit: {url}")
            return cached

    try:
        parsed = parse_url(url)
        if parsed.scheme not in ("http", "https"):
            return {
                "success": False,
                "error": "Invalid URL: must be http or https",
                "url": url,
            }

        if parsed.host:
            assert_public_hostname(parsed.host)

    except ValueError as e:
        logger.error(f"[fetch_url] SSRF protection blocked: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": url,
        }

    logger.info(f"[fetch_url] Fetching URL: {url}")

    headers = {
        "User-Agent": CHROME_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    session = create_ssrf_protected_session()
    session.max_redirects = max_redirects

    try:
        response = session.get(
            url, headers=headers, timeout=timeout, allow_redirects=True
        )

        if response.status_code != 200:
            logger.warning(f"[fetch_url] HTTP {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "url": url,
                "status": response.status_code,
            }

        content_type = response.headers.get("Content-Type", "")
        content_length = len(response.content)

        if content_length > DEFAULT_MAX_RESPONSE_BYTES:
            logger.warning(f"[fetch_url] Response too large: {content_length} bytes")
            return {
                "success": False,
                "error": f"Response too large: {content_length} bytes (max: {DEFAULT_MAX_RESPONSE_BYTES})",
                "url": url,
            }

        final_url = str(response.url)

        if "text/html" in content_type:
            extracted = extract_readability_content(
                response.text, final_url, extract_mode
            )

            if not extracted:
                extracted = {
                    "text": response.text[:DEFAULT_MAX_CHARS],
                    "title": None,
                }

            text, truncated = truncate_text(extracted.get("text", ""), max_chars)
            title = extracted.get("title")

            logger.info(
                f"[fetch_url] Success: {url}, title: {title[:50] if title else 'N/A'}"
            )

            result = {
                "success": True,
                "url": url,
                "finalUrl": final_url,
                "status": response.status_code,
                "contentType": content_type.split(";")[0].strip(),
                "title": title,
                "extractMode": extract_mode,
                "extractor": "readability",
                "text": text,
                "truncated": truncated,
                "length": len(text),
                "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tookMs": int((time.time() - start_time) * 1000),
            }

        elif "application/json" in content_type:
            try:
                text = json.dumps(response.json(), indent=2, ensure_ascii=False)
            except:
                text = response.text

            text, truncated = truncate_text(text, max_chars)

            result = {
                "success": True,
                "url": url,
                "finalUrl": final_url,
                "status": response.status_code,
                "contentType": content_type.split(";")[0].strip(),
                "extractor": "json",
                "text": text,
                "truncated": truncated,
                "length": len(text),
                "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tookMs": int((time.time() - start_time) * 1000),
            }

        else:
            text = f"[Binary content: {content_length} bytes, type: {content_type}]"

            result = {
                "success": True,
                "url": url,
                "finalUrl": final_url,
                "status": response.status_code,
                "contentType": content_type.split(";")[0].strip(),
                "extractor": "raw",
                "text": text,
                "truncated": False,
                "length": len(text),
                "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tookMs": int((time.time() - start_time) * 1000),
            }

        if use_cache:
            write_cache(cache_key, result, cache_ttl)

        return result

    except requests.exceptions.Timeout:
        logger.error(f"[fetch_url] Timeout: {url}")
        return {"success": False, "error": "Timeout", "url": url}
    except requests.exceptions.TooManyRedirects:
        logger.error(f"[fetch_url] Too many redirects: {url}")
        return {"success": False, "error": "Too many redirects", "url": url}
    except requests.exceptions.RequestException as e:
        logger.error(f"[fetch_url] Error: {e}")
        return {"success": False, "error": str(e), "url": url}
    except Exception as e:
        logger.error(f"[fetch_url] Error: {e}")
        return {"success": False, "error": str(e), "url": url}


def clear_cache() -> int:
    """Clear the cache, return number of entries cleared"""
    count = len(FETCH_CACHE)
    FETCH_CACHE.clear()
    return count


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_fetch.py <url> [extract_mode]")
        print("  extract_mode: markdown (default) or text")
        sys.exit(1)

    test_url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "markdown"

    result = fetch_url(test_url, extract_mode=mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
