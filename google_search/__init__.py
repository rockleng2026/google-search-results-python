#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Search - Web Search API
"""

from .search_engine import search, fetch_url, GoogleSearch

__version__ = "2.0.0"
__all__ = ['search', 'fetch_url', 'GoogleSearch']