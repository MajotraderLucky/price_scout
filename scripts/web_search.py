#!/usr/bin/env python3
"""
Web Search API for Price Scout Bot

DuckDuckGo-based price search with JSON output for Rust integration.
Now with real price extraction from known stores using Playwright.

Usage:
    python3 web_search.py search --query "рогатка centershot" --max-results 10
    python3 web_search.py search --query "рогатка centershot" --fetch-prices  # Extract real prices

Output: JSON with search results including prices extracted from snippets or pages.
"""

import argparse
import json
import sys
import re
from urllib.parse import urlparse

try:
    from duckduckgo_search import DDGS
except ImportError:
    print(json.dumps({"query": "", "results": [], "error": "duckduckgo-search not installed"}))
    sys.exit(1)

# Try to import store_parsers for real price extraction
STORE_PARSERS_AVAILABLE = False
try:
    from store_parsers import fetch_price, SUPPORTED_STORES, extract_domain
    STORE_PARSERS_AVAILABLE = True
except ImportError:
    SUPPORTED_STORES = set()
    pass  # Will use snippet prices only

# Try to import store_discovery for candidate tracking
STORE_DISCOVERY_AVAILABLE = False
_discovery = None
try:
    import os
    from store_discovery import StoreDiscovery
    _db_url = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/price_scout")
    _discovery = StoreDiscovery(_db_url)
    STORE_DISCOVERY_AVAILABLE = True
except ImportError:
    pass  # No candidate tracking


# Aggregators and price comparison sites (not real shops - exclude from results)
AGGREGATORS = {
    "steel-gun.ru",
    "price.ru",
    "e-katalog.ru",
    "sravni.com",
    "goods-price.ru",
    "nadavi.ru",
}

# Known shops with their display names
KNOWN_SHOPS = {
    # Major marketplaces
    "ozon.ru": "Ozon",
    "wildberries.ru": "Wildberries",
    "market.yandex.ru": "Яндекс.Маркет",
    "aliexpress.ru": "AliExpress",
    "aliexpress.com": "AliExpress",
    # Electronics
    "dns-shop.ru": "DNS",
    "mvideo.ru": "М.Видео",
    "citilink.ru": "Ситилинк",
    "eldorado.ru": "Эльдорадо",
    "regard.ru": "Регард",
    "technopark.ru": "Технопарк",
    "svyaznoy.ru": "Связной",
    "holodilnik.ru": "Холодильник.ру",
    "onlinetrade.ru": "Онлайн Трейд",
    # Specialized
    "centershot.ru": "Centershot",
    "archer-style.ru": "Archer Style",
    "vseinstrumenti.ru": "ВсеИнструменты",
    "leroymerlin.ru": "Леруа Мерлен",
    "sportmaster.ru": "Спортмастер",
    "decathlon.ru": "Декатлон",
    "220-volt.ru": "220 Вольт",
    "petrovich.ru": "Петрович",
    "maxidom.ru": "Максидом",
    # General
    "beru.ru": "Беру",
    "goods.ru": "goods.ru",
    "sbermegamarket.ru": "СберМегаМаркет",
}


def extract_prices(text: str) -> list:
    """Extract prices from text using regex patterns."""
    patterns = [
        # Standard Russian price formats
        r'(\d{1,3}(?:\s?\d{3})*)\s*(?:₽|руб\.?|RUB|р\.)',
        # Price after "цена" keyword
        r'(?:цена|price|стоимость)[:\s]*(\d{1,3}(?:\s?\d{3})*)',
        # Price before "рублей"
        r'(\d{1,3}(?:\s?\d{3})*)\s*(?:рублей|рубля)',
        # Just numbers that look like prices (fallback)
        r'(?:от|от\s+|за\s+)(\d{1,3}(?:\s?\d{3})*)',
    ]

    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Clean the price string
            price_str = match.replace(" ", "").replace("\u00a0", "")
            if price_str.isdigit():
                price = int(price_str)
                # Filter reasonable prices (100 RUB to 10M RUB)
                if 100 < price < 10_000_000:
                    prices.append(price)

    return sorted(set(prices))


def get_base_domain(domain: str) -> str:
    """Extract base domain from subdomain (krasnoyarsk.tempgun.ru -> tempgun.ru)"""
    parts = domain.split('.')
    if len(parts) >= 2:
        # Return last two parts (domain.tld)
        return '.'.join(parts[-2:])
    return domain


def search_prices(query: str, max_results: int = 20, fetch_real_prices: bool = True, track_candidates: bool = True) -> dict:
    """
    Search for prices using DuckDuckGo.

    Args:
        query: Search query
        max_results: Maximum number of results
        fetch_real_prices: If True, fetch real prices from known stores using Playwright
        track_candidates: If True, track unknown stores with prices as candidates for auto-import

    Returns:
        Dict with query, results, and error
    """
    results = {
        "query": query,
        "results": [],
        "error": None,
        "verified_count": 0,
        "candidates_tracked": 0,
    }
    seen_domains = set()  # For deduplication

    try:
        with DDGS() as ddgs:
            # Simple search without "купить...цена" - avoids rate limiting
            search_results = list(ddgs.text(
                query,
                max_results=max_results
            ))

        for r in search_results:
            url = r.get("href", "")
            title = r.get("title", "")
            snippet = r.get("body", "")

            # Parse domain
            domain = urlparse(url).netloc.replace("www.", "")

            # Skip aggregators and price comparison sites
            is_aggregator = any(agg in domain for agg in AGGREGATORS)
            if is_aggregator:
                continue

            # Deduplicate by base domain (krasnoyarsk.tempgun.ru -> tempgun.ru)
            base_domain = get_base_domain(domain)
            if base_domain in seen_domains:
                continue
            seen_domains.add(base_domain)

            # Extract prices from title and snippet (fallback)
            combined_text = f"{title} {snippet}"
            prices = extract_prices(combined_text)
            verified = False

            # Identify shop
            shop_name = None
            for shop_domain, name in KNOWN_SHOPS.items():
                if shop_domain in domain:
                    shop_name = name
                    break

            results["results"].append({
                "title": title[:150] if title else "",
                "url": url,
                "domain": domain,
                "shop": shop_name,
                "snippet": snippet[:200] if snippet else "",
                "prices": prices,
                "verified": verified,
            })

        # Fetch real prices from known stores (if enabled)
        if fetch_real_prices and STORE_PARSERS_AVAILABLE:
            for result in results["results"][:5]:  # Limit to top 5 for speed
                domain = result["domain"]

                # Check if this store is supported (domain contains store name)
                store_supported = any(store in domain for store in SUPPORTED_STORES)
                if not store_supported:
                    continue

                try:
                    price_data = fetch_price(result["url"], timeout=30)
                    if price_data.get("price"):
                        result["prices"] = [price_data["price"]]
                        result["verified"] = True
                        results["verified_count"] += 1
                    elif price_data.get("error"):
                        # Log error but keep snippet prices
                        result["fetch_error"] = price_data["error"]
                except Exception as e:
                    # Keep snippet prices on error
                    result["fetch_error"] = str(e)

        # Track store candidates for auto-import
        if track_candidates and STORE_DISCOVERY_AVAILABLE and _discovery:
            for result in results["results"]:
                domain = result["domain"]
                url = result["url"]
                has_prices = bool(result.get("prices"))

                # Skip known stores and shops without prices
                is_known_store = result.get("shop") is not None
                is_supported = any(store in domain for store in SUPPORTED_STORES)

                if not is_known_store and not is_supported and has_prices:
                    try:
                        candidate_id = _discovery.track_candidate(domain, url, price_found=True)
                        if candidate_id:
                            results["candidates_tracked"] += 1
                    except Exception:
                        pass  # Don't fail search due to tracking errors

    except Exception as e:
        results["error"] = str(e)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Web Search API for Price Scout Bot"
    )
    parser.add_argument(
        "command",
        choices=["search"],
        help="Command to execute"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Search query"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum number of results (default: 20)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="json",
        help="Output format"
    )
    parser.add_argument(
        "--fetch-prices",
        action="store_true",
        default=True,
        help="Fetch real prices from known stores using Playwright (default: True)"
    )
    parser.add_argument(
        "--no-fetch-prices",
        action="store_true",
        help="Disable real price fetching (faster, snippet prices only)"
    )
    parser.add_argument(
        "--no-track-candidates",
        action="store_true",
        help="Disable tracking store candidates for auto-import"
    )

    args = parser.parse_args()

    # Determine if we should fetch real prices
    fetch_prices = args.fetch_prices and not args.no_fetch_prices
    track_candidates = not args.no_track_candidates

    if args.command == "search":
        result = search_prices(args.query, args.max_results, fetch_real_prices=fetch_prices, track_candidates=track_candidates)

        if args.output == "pretty":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # Compact JSON for Rust parsing
            print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
