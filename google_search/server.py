#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Search API Service with multiple engines
"""

import sys
import io
import os

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import json
import logging
import argparse
from flask import Flask, request, jsonify, Response
from search_engine import search
from enhanced_fetch import fetch_url as enhanced_fetch_url

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")


def json_response(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        status=status,
        mimetype="application/json; charset=utf-8",
    )


@app.route("/health", methods=["GET"])
def health():
    return json_response({"status": "ok", "service": "web-search-api"})


@app.route("/web_search", methods=["GET", "POST"])
def web_search():
    """
    Web search endpoint

    GET/POST parameters:
        - q: search query (required)
        - num: number of results (optional, default 10)
        - engines: comma-separated engine list (optional)
    """
    if request.method == "GET":
        params = request.args
    else:
        params = request.json or request.form

    query = params.get("q") or params.get("keyword")
    num_results = int(params.get("num") or params.get("n") or 10)
    engines_str = params.get("engines")

    engines = None
    if engines_str:
        engines = [e.strip() for e in engines_str.split(",")]

    if not query:
        return json_response({"error": "Missing required parameter: q"}, 400)

    logger.info(
        f"[API] web_search called with q='{query}', num={num_results}, engines={engines}"
    )

    try:
        results = search(
            query,
            num_results=num_results,
            engines=engines,
            google_api_key=GOOGLE_API_KEY or params.get("api_key"),
            google_cse_id=GOOGLE_CSE_ID or params.get("cse_id"),
        )

        return json_response(
            {"success": True, "query": query, "total": len(results), "results": results}
        )

    except Exception as e:
        logger.error(f"[API] search error: {e}")
        return json_response({"error": str(e)}, 500)


@app.route("/web_fetch", methods=["GET", "POST"])
def web_fetch():
    """
    Fetch URL content endpoint

    GET/POST parameters:
        - url: URL to fetch (required)
        - timeout: request timeout (optional, default 15)
        - extract_mode: extraction mode (optional, default "markdown", values: "markdown" or "text")
        - max_chars: maximum characters to return (optional, default 50000)
        - use_cache: enable caching (optional, default true)
    """
    if request.method == "GET":
        params = request.args
    else:
        params = request.json or request.form

    url = params.get("url")
    timeout = int(params.get("timeout") or 15)
    extract_mode = params.get("extract_mode") or "markdown"
    max_chars = int(params.get("max_chars") or 50000)
    use_cache = params.get("use_cache", "true").lower() != "false"

    if not url:
        return json_response({"error": "Missing required parameter: url"}, 400)

    logger.info(f"[API] web_fetch called with url='{url}', extract_mode={extract_mode}")

    result = enhanced_fetch_url(
        url,
        timeout=timeout,
        max_chars=max_chars,
        extract_mode=extract_mode,
        use_cache=use_cache,
    )

    return json_response(result)


@app.route("/search", methods=["GET", "POST"])
def search_alias():
    """Alias for /web_search"""
    return web_search()


def run_server(host="0.0.0.0", port=25001, debug=False):
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║         Web Search API Service                             ║
║         http://{host}:{port}                                  ║
╚═══════════════════════════════════════════════════════════════╝

Endpoints:
    GET  /health           - Health check
    GET  /web_search       - Search (alias: /search)
    POST /web_search      - Search with JSON body
    POST /web_fetch       - Fetch URL content

Examples:
    curl "http://localhost:{port}/web_search?q=python&num=5"
    curl -X POST -H "Content-Type: application/json" -d '{{"q":"python","engines":"duckduckgo,bing"}}' http://localhost:{port}/web_search
    curl -X POST -H "Content-Type: application/json" -d '{{"url":"https://www.python.org"}}' http://localhost:{port}/web_fetch

Environment Variables:
    GOOGLE_API_KEY - Google Custom Search API Key
    GOOGLE_CSE_ID  - Google Custom Search Engine ID
""")
    app.run(host=host, port=port, debug=debug)


def main():
    parser = argparse.ArgumentParser(description="Web Search API Service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=25001)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()
    run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
