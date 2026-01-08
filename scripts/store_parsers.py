#!/usr/bin/env python3
"""
Store-specific price parsers for web search integration.

Extracts prices from product pages using Playwright and store-specific parsers.
Designed to be used by web_search.py for verified price extraction.

Usage:
    from store_parsers import fetch_price, SUPPORTED_STORES

    result = fetch_price("https://www.centershot.ru/catalog/rogatki/123/")
    # Returns: {"price": 1900, "available": True, "store": "centershot", "error": None}
"""

import re
import sys
from typing import Dict, Optional
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    from playwright_stealth import Stealth
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright playwright-stealth", file=sys.stderr)
    sys.exit(1)


# === Store Parsers ===

def parse_centershot(html: str) -> Optional[Dict]:
    """Parse Centershot.ru - hunting accessories store"""
    # CSS selector .product-purchase_price-value
    css_prices = []
    for match in re.finditer(r'product-purchase_price-value[^>]*>([^<]+)<', html):
        price_text = match.group(1)
        clean = re.sub(r'[^\d]', '', price_text)
        if clean.isdigit():
            price = int(clean)
            if 100 < price < 100000:
                css_prices.append(price)

    if css_prices:
        return {"price": min(css_prices), "available": True}

    # Schema.org fallback
    for match in re.finditer(r'itemprop="price"\s+content="(\d+)"', html):
        price = int(match.group(1))
        if 100 < price < 100000:
            return {"price": price, "available": True}

    # Generic price pattern
    for match in re.findall(r'(\d[\d\s\u00a0]*\d)\s*(?:₽|руб|&#8381;)', html):
        clean = re.sub(r'[\s\u00a0]', '', match)
        if clean.isdigit():
            price = int(clean)
            if 500 < price < 100000:
                return {"price": price, "available": True}

    return None


def parse_regard(html: str) -> Optional[Dict]:
    """Parse Regard.ru - electronics store"""
    prices = []

    # Schema.org price
    for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html, re.IGNORECASE):
        price = int(match)
        if 1000 < price < 500000:
            prices.append(price)

    # CSS selector for price
    for match in re.findall(r'class="[^"]*price[^"]*"[^>]*>[\s]*([0-9\s]+)[\s]*(?:₽|руб)', html):
        clean = re.sub(r'\s', '', match)
        if clean.isdigit():
            price = int(clean)
            if 1000 < price < 500000:
                prices.append(price)

    if prices:
        return {"price": min(prices), "available": True}

    return None


def parse_ozon(html: str) -> Optional[Dict]:
    """Parse Ozon.ru - marketplace"""
    prices = []

    # JSON-LD price
    for match in re.findall(r'"price":\s*"?(\d+)"?', html):
        price = int(match)
        if 100 < price < 1000000:
            prices.append(price)

    # Price in kopecks (Ozon sometimes uses this)
    for match in re.findall(r'"price":\s*(\d{5,})', html):
        price = int(match)
        if price > 10000:  # Likely kopecks
            price = price // 100
        if 100 < price < 1000000:
            prices.append(price)

    # Visible price patterns
    for match in re.findall(r'(\d[\d\s\u00a0]*\d)\s*(?:₽|руб)', html):
        clean = re.sub(r'[\s\u00a0]', '', match)
        if clean.isdigit():
            price = int(clean)
            if 100 < price < 1000000:
                prices.append(price)

    if prices:
        return {"price": min(prices), "available": True}

    return None


def parse_yandex_market(html: str) -> Optional[Dict]:
    """Parse Yandex Market"""
    prices = []

    # Price patterns
    for match in re.findall(r'"price":\s*(\d+)', html):
        price = int(match)
        if 100 < price < 1000000:
            prices.append(price)

    # Visible prices
    for match in re.findall(r'(\d[\d\s\u00a0]+)\s*₽', html):
        clean = re.sub(r'[\s\u00a0]', '', match)
        if clean.isdigit():
            price = int(clean)
            if 100 < price < 1000000:
                prices.append(price)

    if prices:
        return {"price": min(prices), "available": True}

    return None


def parse_sportmaster(html: str) -> Optional[Dict]:
    """Parse Sportmaster.ru"""
    prices = []

    # Schema.org
    for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html, re.IGNORECASE):
        price = int(match)
        if 100 < price < 100000:
            prices.append(price)

    # JSON price in various formats
    for match in re.findall(r'"price":\s*"?(\d+)"?', html):
        price = int(match)
        if 100 < price < 100000:
            prices.append(price)

    # Sportmaster specific: data-price attribute
    for match in re.findall(r'data-price="(\d+)"', html):
        price = int(match)
        if 100 < price < 100000:
            prices.append(price)

    # Price in class="price" elements
    for match in re.findall(r'class="[^"]*price[^"]*"[^>]*>\s*(\d[\d\s\u00a0]*)', html):
        clean = re.sub(r'[\s\u00a0]', '', match)
        if clean.isdigit():
            price = int(clean)
            if 100 < price < 100000:
                prices.append(price)

    # Visible price with currency
    for match in re.findall(r'(\d[\d\s\u00a0]+)\s*(?:₽|руб|рублей)', html):
        clean = re.sub(r'[\s\u00a0]', '', match)
        if clean.isdigit():
            price = int(clean)
            if 100 < price < 100000:
                prices.append(price)

    # Price in "за X рублей" format (common in Sportmaster)
    for match in re.findall(r'за\s+(\d[\d\s\u00a0]*)\s*(?:₽|руб|рублей)', html):
        clean = re.sub(r'[\s\u00a0]', '', match)
        if clean.isdigit():
            price = int(clean)
            if 100 < price < 100000:
                prices.append(price)

    if prices:
        return {"price": min(prices), "available": True}

    return None


def parse_generic(html: str) -> Optional[Dict]:
    """Generic parser for unknown stores"""
    prices = []

    # Schema.org
    for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html, re.IGNORECASE):
        price = int(match)
        if 100 < price < 1000000:
            prices.append(price)

    # JSON price
    for match in re.findall(r'"price":\s*"?(\d+)"?', html):
        price = int(match)
        if 100 < price < 1000000:
            prices.append(price)

    # Visible price with currency
    for match in re.findall(r'(\d[\d\s\u00a0]+)\s*(?:₽|руб|RUB)', html):
        clean = re.sub(r'[\s\u00a0]', '', match)
        if clean.isdigit():
            price = int(clean)
            if 100 < price < 1000000:
                prices.append(price)

    if prices:
        return {"price": min(prices), "available": True}

    return None


# === Store Configuration ===

STORE_CONFIG = {
    "centershot.ru": {
        "parser": parse_centershot,
        "stealth": False,
        "delay": 2,
    },
    "regard.ru": {
        "parser": parse_regard,
        "stealth": True,
        "delay": 3,
    },
    "ozon.ru": {
        "parser": parse_ozon,
        "stealth": True,
        "delay": 5,
        "skip": True,  # Often blocked
    },
    "market.yandex.ru": {
        "parser": parse_yandex_market,
        "stealth": True,
        "delay": 5,
    },
    "sportmaster.ru": {
        "parser": parse_sportmaster,
        "stealth": False,
        "delay": 2,
    },
    "wildberries.ru": {
        "parser": parse_generic,
        "stealth": True,
        "delay": 3,
        "skip": True,  # Complex JS rendering
    },
}

# Stores that are supported (not skipped)
SUPPORTED_STORES = {k for k, v in STORE_CONFIG.items() if not v.get("skip")}


def extract_domain(url: str) -> str:
    """Extract base domain from URL (www.example.com -> example.com)"""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return domain


def fetch_price(url: str, timeout: int = 30) -> Dict:
    """
    Fetch price from URL using appropriate parser.

    Args:
        url: Product page URL
        timeout: Request timeout in seconds

    Returns:
        Dict with keys: price, available, store, error
    """
    domain = extract_domain(url)

    # Find matching store config
    config = None
    store_name = None
    for store_domain, store_config in STORE_CONFIG.items():
        if store_domain in domain:
            config = store_config
            store_name = store_domain
            break

    if not config:
        return {
            "price": None,
            "available": None,
            "store": domain,
            "error": "Unknown store",
        }

    if config.get("skip"):
        return {
            "price": None,
            "available": None,
            "store": store_name,
            "error": "Store skipped (rate limiting)",
        }

    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)

            # Create context with stealth if needed
            if config.get("stealth"):
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                stealth = Stealth()
                stealth.apply_stealth(context)
            else:
                context = browser.new_context()

            page = context.new_page()

            # Navigate with timeout
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

            # Wait for delay (let JS render)
            if config.get("delay"):
                page.wait_for_timeout(config["delay"] * 1000)

            # Get HTML
            html = page.content()

            browser.close()

            # Parse with store-specific parser
            parser = config.get("parser", parse_generic)
            result = parser(html)

            if result:
                return {
                    "price": result["price"],
                    "available": result.get("available", True),
                    "store": store_name,
                    "error": None,
                }
            else:
                return {
                    "price": None,
                    "available": None,
                    "store": store_name,
                    "error": "Price not found in HTML",
                }

    except PlaywrightTimeout:
        return {
            "price": None,
            "available": None,
            "store": store_name,
            "error": f"Timeout after {timeout}s",
        }
    except Exception as e:
        return {
            "price": None,
            "available": None,
            "store": store_name,
            "error": str(e),
        }


# === CLI for testing ===

if __name__ == "__main__":
    import json
    import argparse

    parser = argparse.ArgumentParser(description="Fetch price from URL")
    parser.add_argument("url", help="Product page URL")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = fetch_price(args.url, args.timeout)

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result["error"]:
            print(f"Error: {result['error']}")
        elif result["price"]:
            print(f"Store: {result['store']}")
            print(f"Price: {result['price']} RUB")
            print(f"Available: {result['available']}")
        else:
            print("Price not found")
