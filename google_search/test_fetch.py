#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to fetch URL content
"""

import requests
import json

url = "https://www.zhihu.com/question/626789498"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

print(f"Fetching URL: {url}")
print("=" * 60)

try:
    response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', '')}")
    print(f"Content-Length: {len(response.content)}")
    print(f"Final URL: {response.url}")
    print("=" * 60)
    
    if response.status_code == 200:
        print("Success! Got HTML content.")
        preview = response.text[:2000]
        print(f"Content Preview:\n{preview}")
        
    else:
        print(f"Error: HTTP {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("Error: Timeout")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Error: {e}")
