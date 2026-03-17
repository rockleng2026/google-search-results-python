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

API_TOKEN = os.environ.get("API_TOKEN", "")


def json_response(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        status=status,
        mimetype="application/json; charset=utf-8",
    )


def check_api_token():
    """Check if API token is valid. Returns True if token is valid or not configured."""
    if not API_TOKEN:
        return True, None

    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        token = request.headers.get("X-API-Token", "").strip()

    if not token:
        return (
            False,
            "Missing API token. Provide via 'Authorization: Bearer <token>' or 'X-API-Token: <token>' header",
        )

    if token != API_TOKEN:
        return False, "Invalid API token"

    return True, None


@app.before_request
def authenticate():
    """Authenticate requests to protected endpoints."""
    if request.path == "/health":
        return None

    valid, error = check_api_token()
    if not valid:
        logger.warning(
            f"[API] Authentication failed for {request.path} from {request.remote_addr}"
        )
        return json_response({"error": error}, 401)

    return None


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

    # Handle use_cache: JSON boolean or string "true"/"false"
    use_cache_raw = params.get("use_cache", True)
    if isinstance(use_cache_raw, bool):
        use_cache = use_cache_raw
    elif isinstance(use_cache_raw, str):
        use_cache = use_cache_raw.lower() != "false"
    else:
        use_cache = True

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
    auth_info = (
        "Enabled (API_TOKEN configured)"
        if API_TOKEN
        else "Disabled (set API_TOKEN env var to enable)"
    )
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║         Web Search API Service                             ║
║         http://{host}:{port}                                  ║
╚═══════════════════════════════════════════════════════════════╝

Endpoints:
    GET  /health           - Health check (no auth)
    GET  /web_search       - Search (alias: /search)
    POST /web_search      - Search with JSON body
    POST /web_fetch       - Fetch URL content

Authentication: {auth_info}
  Headers:
    Authorization: Bearer <token>
    or
    X-API-Token: <token>

Search Engines: duckduckgo, bing, baidu
  - Engine rotation enabled by default for load balancing
  - Specify engines via 'engines' parameter to disable rotation

Examples:
    curl "http://localhost:{port}/health"
    curl -H "Authorization: Bearer your-token" "http://localhost:{port}/web_search?q=python&num=5"
    curl -H "X-API-Token: your-token" -X POST -H "Content-Type: application/json" -d '{{"q":"python","engines":"duckduckgo,bing"}}' http://localhost:{port}/web_search
    curl -H "Authorization: Bearer your-token" -X POST -H "Content-Type: application/json" -d '{{"url":"https://www.python.org"}}' http://localhost:{port}/web_fetch

Environment Variables:
    API_TOKEN      - API Authentication Token (optional)
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
