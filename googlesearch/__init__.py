#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import time
import random


ABSTRACT_MAX_LENGTH = 300

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

ddg_base_url = "https://html.duckduckgo.com"
ddg_search_url = "https://html.duckduckgo.com/html/?q="


class SearchSession:
    def __init__(self):
        self.session = requests.Session()
        self._update_headers()
    
    def _update_headers(self, ua=None):
        if ua is None:
            ua = random.choice(user_agents)
        self.session.headers = {
            **HEADERS,
            "User-Agent": ua,
        }
    
    def _get_random_delay(self):
        return random.uniform(1, 3)


def parse_html(html_content, rank_start=0):
    from urllib.parse import urlparse, parse_qs, unquote
    
    soup = BeautifulSoup(html_content, "html.parser")
    results = []

    search_results = soup.select("a.result__a")

    for elem in search_results:
        try:
            title = elem.get_text(strip=True)
            url = elem.get("href", "")

            if not title or not url or url == "#":
                continue

            if "//duckduckgo.com/l/?" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "uddg" in params:
                    url = unquote(params["uddg"][0])
            
            if "duckduckgo.com/y.js" in url or url.startswith("/"):
                continue

            snippet_elem = elem.find_parent("div", class_="result")
            if snippet_elem:
                snippet_elem = snippet_elem.select_one("a.result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            else:
                snippet = ""

            if ABSTRACT_MAX_LENGTH and len(snippet) > ABSTRACT_MAX_LENGTH:
                snippet = snippet[:ABSTRACT_MAX_LENGTH] + "..."

            rank_start += 1
            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "rank": rank_start,
            })

        except Exception as e:
            continue

    next_btn = soup.select_one("a.result__a[rel=next]")
    next_url = None
    if next_btn:
        next_url = ddg_search_url + requests.utils.quote(next_btn.get("data-url", ""))

    return results, next_url


def search(keyword, num_results=10, debug=0):
    if not keyword:
        return None

    client = SearchSession()
    list_result = []
    page = 1
    next_url = ddg_search_url + requests.utils.quote(keyword)

    while len(list_result) < num_results:
        time.sleep(client._get_random_delay())

        try:
            response = client.session.get(next_url, timeout=15)
            
            if response.status_code != 200:
                if debug:
                    print(f"Page {page}: status {response.status_code}")
                break

            data, next_url = parse_html(response.text, rank_start=len(list_result))
            
            if data:
                list_result += data
                if debug:
                    print(f"---searching [{keyword}], page {page}, got {len(data)} results, total: {len(list_result)}")
            else:
                if debug:
                    print(f"---no results on page {page}")
            
            if not next_url or len(data) == 0:
                break

            page += 1

        except requests.exceptions.RequestException as e:
            if debug:
                print(f"Request error: {e}")
            break
        except Exception as e:
            if debug:
                print(f"Error: {e}")
            break

    final_results = list_result[:num_results] if len(list_result) > num_results else list_result

    if debug:
        print(f"---search [{keyword}] finished. total results: {len(final_results)}")

    return final_results


def run():
    prompt = """
duckduckgo-search: Scrape DuckDuckGo Search Results (No API Key Required)

Usage:
    python -m googlesearch "keyword" [num_results] [debug]

Example:
    from googlesearch import search
    results = search("coffee", num_results=10, debug=1)
    for r in results:
        print(f"{r['rank']}. {r['title']}")
        print(f"   {r['url']}")
"""
    print(prompt)

    if len(sys.argv) > 1:
        keyword = sys.argv[1]
        num_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        debug = int(sys.argv[3]) if len(sys.argv) > 3 else 0

        print(f"\n---start search: [{keyword}], expected results: [{num_results}]")
        results = search(keyword, num_results=num_results, debug=debug)

        if results:
            print(f"\nTotal results: {len(results)}")
            for r in results:
                print(f"{r['rank']}. {r['title']}")
                print(f"   {r['url']}")
                print(f"   {r['snippet'][:100]}...")
                print()
        else:
            print("No results found.")
    else:
        keyword = input("Enter keyword: ").strip()
        if keyword:
            results = search(keyword, debug=1)


if __name__ == "__main__":
    run()