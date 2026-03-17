#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Search engines for web search
Support: DuckDuckGo, Bing, Google Custom Search API, Baidu
"""

import sys
import io
import logging

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote, urlparse, parse_qs
import base64
import json


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


__version__ = "2.1.0"

ABSTRACT_MAX_LENGTH = 300

# Engine rotation index for load balancing
_engine_index = 0
_engine_lock = __import__("threading").Lock()

# Default engines: rotation engines + fallback engines
ROTATION_ENGINES = ["duckduckgo", "bing"]  # Rotated for load balancing
FALLBACK_ENGINES = ["baidu"]  # Always at the end as fallback
DEFAULT_ENGINES = ROTATION_ENGINES + FALLBACK_ENGINES


class DuckDuckGoSearch:
    """DuckDuckGo HTML search engine"""

    NAME = "duckduckgo"
    BASE_URL = "https://html.duckduckgo.com/html/?q="

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            **self.HEADERS,
            "User-Agent": random.choice(self.user_agents),
        }

    def search(self, keyword, num_results=10):
        results = []
        url = self.BASE_URL + quote(keyword)

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                logger.warning(
                    f"[DuckDuckGo] Request failed with status {response.status_code}"
                )
                return results

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select("a.result__a")

            for item in items:
                title = item.get_text(strip=True)
                href = item.get("href", "")

                if not title or not href or href == "#":
                    continue

                if "//duckduckgo.com/l/?" in href:
                    parsed = urlparse(href)
                    params = parse_qs(parsed.query)
                    if "uddg" in params:
                        href = params["uddg"][0]

                if "duckduckgo.com/y.js" in href or href.startswith("/"):
                    continue

                snippet_elem = item.find_parent("div", class_="result")
                snippet = ""
                if snippet_elem:
                    snippet_elem = snippet_elem.select_one("a.result__snippet")
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)

                if len(snippet) > ABSTRACT_MAX_LENGTH:
                    snippet = snippet[:ABSTRACT_MAX_LENGTH] + "..."

                results.append(
                    {
                        "title": title,
                        "url": href,
                        "snippet": snippet,
                        "engine": self.NAME,
                    }
                )

                if len(results) >= num_results:
                    break

        except requests.exceptions.RequestException as e:
            logger.error(f"[DuckDuckGo] Request error: {e}")
        except Exception as e:
            logger.error(f"[DuckDuckGo] Parse error: {e}")

        return results[:num_results]


class BingSearch:
    """Bing search engine"""

    NAME = "bing"
    BASE_URL = "https://www.bing.com/search?q="

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.cookies.set("SRCHHPGUSR", "ADLT=OFF&NRSLT=50")
        self.session.headers = {
            **self.HEADERS,
            "User-Agent": random.choice(self.user_agents),
            "Referer": "https://www.bing.com",
        }

    def search(self, keyword, num_results=10):
        results = []
        url = self.BASE_URL + quote(keyword)

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                logger.warning(
                    f"[Bing] Request failed with status {response.status_code}"
                )
                return results

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select("li.b_algo h2 a")

            for item in items:
                title = item.get_text(strip=True)
                href = item.get("href", "")

                if not title or not href:
                    continue

                if "/ck/a?" in href:
                    try:
                        parsed = urlparse(href)
                        params = parse_qs(parsed.query)
                        if "u" in params:
                            href = base64.b64decode(params["u"][0]).decode("utf-8")
                    except:
                        pass

                if href.startswith("/"):
                    continue

                snippet_elem = item.find_parent("li", class_="b_algo")
                snippet = ""
                if snippet_elem:
                    snippet_elem = snippet_elem.select_one("div.b_caption p")
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)

                if len(snippet) > ABSTRACT_MAX_LENGTH:
                    snippet = snippet[:ABSTRACT_MAX_LENGTH] + "..."

                results.append(
                    {
                        "title": title,
                        "url": href,
                        "snippet": snippet,
                        "engine": self.NAME,
                    }
                )

                if len(results) >= num_results:
                    break

        except requests.exceptions.RequestException as e:
            logger.error(f"[Bing] Request error: {e}")
        except Exception as e:
            logger.error(f"[Bing] Parse error: {e}")

        return results[:num_results]


class GoogleSearchAPI:
    """Google Custom Search API"""

    NAME = "google_api"
    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key=None, cse_id=None):
        self.api_key = api_key
        self.cse_id = cse_id

    def search(self, keyword, num_results=10):
        results = []

        if not self.api_key or not self.cse_id:
            logger.warning("[Google API] API key or CSE ID not configured")
            return results

        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": keyword,
            "num": min(num_results, 10),
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            if response.status_code != 200:
                logger.warning(
                    f"[Google API] Request failed with status {response.status_code}"
                )
                return results

            data = response.json()
            items = data.get("items", [])

            for item in items:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "engine": self.NAME,
                    }
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"[Google API] Request error: {e}")
        except Exception as e:
            logger.error(f"[Google API] Parse error: {e}")

        return results[:num_results]


class BaiduSearch:
    """Baidu search engine"""

    NAME = "baidu"
    BASE_URL = "https://www.baidu.com/s?ie=utf-8&wd="

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            **self.HEADERS,
            "User-Agent": random.choice(self.user_agents),
            "Referer": "https://www.baidu.com",
        }

    def search(self, keyword, num_results=10):
        results = []
        url = self.BASE_URL + quote(keyword)

        try:
            response = self.session.get(url, timeout=15)
            response.encoding = "utf-8"

            if response.status_code != 200:
                logger.warning(
                    f"[Baidu] Request failed with status {response.status_code}"
                )
                return results

            soup = BeautifulSoup(response.text, "lxml")
            items = soup.select("div.c-container h3.c-title a")

            for item in items:
                title = item.get_text(strip=True)
                href = item.get("href", "")

                if not title or not href or href.startswith("/"):
                    continue

                snippet_elem = item.find_parent("div", class_="c-container")
                snippet = ""
                if snippet_elem:
                    snippet_elem = snippet_elem.select_one("div.c-abstract")
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)

                if len(snippet) > ABSTRACT_MAX_LENGTH:
                    snippet = snippet[:ABSTRACT_MAX_LENGTH] + "..."

                results.append(
                    {
                        "title": title,
                        "url": href,
                        "snippet": snippet,
                        "engine": self.NAME,
                    }
                )

                if len(results) >= num_results:
                    break

        except requests.exceptions.RequestException as e:
            logger.error(f"[Baidu] Request error: {e}")
        except Exception as e:
            logger.error(f"[Baidu] Parse error: {e}")

        return results[:num_results]


def search(
    keyword,
    num_results=10,
    engines=None,
    google_api_key=None,
    google_cse_id=None,
    debug=0,
    rotate_engines=True,
):
    """
    Search using multiple engines in sequence

    Args:
        keyword: Search query
        num_results: Number of results to return
        engines: List of engine names to use, in order
        google_api_key: Google Custom Search API key (deprecated)
        google_cse_id: Google Custom Search Engine ID (deprecated)
        rotate_engines: Enable engine rotation for load balancing (default: True)

    Returns:
        List of search results
    """
    global _engine_index

    if not keyword:
        return []

    if engines is None:
        # Use default engines: rotation engines + fallback engines
        # Rotation: duckduckgo, bing (round-robin)
        # Fallback: baidu (always last)
        if rotate_engines and len(ROTATION_ENGINES) > 1:
            with _engine_lock:
                rotation = _engine_index % len(ROTATION_ENGINES)
                _engine_index = (_engine_index + 1) % len(ROTATION_ENGINES)
            # Rotate front engines, keep fallback at end
            rotated_front = ROTATION_ENGINES[rotation:] + ROTATION_ENGINES[:rotation]
            engines = rotated_front + FALLBACK_ENGINES
            logger.info(
                f"[rotate] Starting from engine: {engines[0]}, fallback: {FALLBACK_ENGINES[0]}"
            )
        else:
            engines = DEFAULT_ENGINES.copy()

    all_results = []
    used_urls = set()

    logger.info(f"Starting search for: {keyword}")
    logger.info(f"Using engines: {engines}")

    for engine_name in engines:
        logger.info(f"Trying engine: {engine_name}")

        try:
            if engine_name == "duckduckgo":
                engine = DuckDuckGoSearch()
                results = engine.search(keyword, num_results)

            elif engine_name == "bing":
                engine = BingSearch()
                results = engine.search(keyword, num_results)

            elif engine_name == "google_api":
                logger.warning(
                    "[google_api] Deprecated and removed. Use duckduckgo, bing, or baidu instead."
                )
                continue

            elif engine_name == "baidu":
                engine = BaiduSearch()
                results = engine.search(keyword, num_results)

            else:
                logger.warning(f"Unknown engine: {engine_name}")
                continue

            if results:
                for r in results:
                    if r["url"] not in used_urls:
                        used_urls.add(r["url"])
                        r["rank"] = len(all_results) + 1
                        all_results.append(r)

                logger.info(
                    f"[{engine_name}] Got {len(results)} results, total unique: {len(all_results)}"
                )

                if len(all_results) >= num_results:
                    logger.info(
                        f"Got enough results ({len(all_results)}), stopping search"
                    )
                    break
            else:
                logger.info(f"[{engine_name}] No results found, trying next engine")

        except Exception as e:
            logger.error(f"[{engine_name}] Error: {e}")
            continue

        if len(all_results) < num_results:
            time.sleep(random.uniform(0.5, 1.5))

    logger.info(f"Search completed. Total results: {len(all_results)}")
    return all_results[:num_results]


def fetch_url(url, timeout=15):
    """
    Fetch content from a URL

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Dict with content or error
    """
    logger.info(f"Fetching URL: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    try:
        response = requests.get(
            url, headers=headers, timeout=timeout, allow_redirects=True
        )

        if response.status_code != 200:
            logger.warning(f"[fetch_url] HTTP {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "url": url,
            }

        content_type = response.headers.get("Content-Type", "")

        if "text/html" in content_type:
            soup = BeautifulSoup(response.text, "lxml")

            title = ""
            if soup.title:
                title = soup.title.string or ""

            text = soup.get_text(separator="\n", strip=True)
            text = "\n".join([line for line in text.split("\n") if line.strip()])[
                :10000
            ]

            logger.info(f"[fetch_url] Success: {url}, title: {title[:50]}")

            return {
                "success": True,
                "url": response.url,
                "title": title,
                "content_type": content_type,
                "text": text,
                "raw_html": response.text[:50000],
            }
        else:
            logger.info(f"[fetch_url] Non-HTML content: {content_type}")
            return {
                "success": True,
                "url": response.url,
                "content_type": content_type,
                "text": f"[Binary content: {len(response.content)} bytes]",
            }

    except requests.exceptions.Timeout:
        logger.error(f"[fetch_url] Timeout: {url}")
        return {"success": False, "error": "Timeout", "url": url}
    except requests.exceptions.RequestException as e:
        logger.error(f"[fetch_url] Error: {e}")
        return {"success": False, "error": str(e), "url": url}
    except Exception as e:
        logger.error(f"[fetch_url] Error: {e}")
        return {"success": False, "error": str(e), "url": url}


class GoogleSearch:
    """OOP style Google Search"""

    def __init__(self, params=None, **kwargs):
        self.params = params or {}
        self.params.update(kwargs)
        self.results = None

    def get_dict(self, num_results=10):
        query = self.params.get("q") or self.params.get("keyword")
        engines = self.params.get("engines")
        api_key = self.params.get("api_key")
        cse_id = self.params.get("cse_id")
        self.results = search(
            query,
            num_results=num_results,
            engines=engines,
            google_api_key=api_key,
            google_cse_id=cse_id,
        )
        return self.results

    def get_json(self, num_results=10):
        return self.get_dict(num_results)


def run():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║         Web Search API - Multiple Engines                    ║
║         DuckDuckGo / Bing / Google API / Baidu              ║
╚═══════════════════════════════════════════════════════════════╝
""")

    if len(sys.argv) > 1:
        keyword = sys.argv[1]
        num_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10

        results = search(keyword, num_results=num_results, debug=1)

        for r in results:
            print(f"\n[{r['engine']}] {r['rank']}. {r['title']}")
            print(f"   {r['url']}")


if __name__ == "__main__":
    run()
