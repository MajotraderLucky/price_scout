#!/usr/bin/env python3
"""
Web Search API for Price Scout Bot

DuckDuckGo-based price search with JSON output for Rust integration.

Usage:
    python3 web_search.py search --query "рогатка centershot" --max-results 10

Output: JSON with search results including prices extracted from snippets.
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


def search_prices(query: str, max_results: int = 20) -> dict:
    """Search for prices using DuckDuckGo."""
    results = {
        "query": query,
        "results": [],
        "error": None
    }

    try:
        with DDGS() as ddgs:
            # Search with Russian locale and price-related keywords
            search_query = f"купить {query} цена"
            search_results = list(ddgs.text(
                search_query,
                region="ru-ru",
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

            # Extract prices from title and snippet
            combined_text = f"{title} {snippet}"
            prices = extract_prices(combined_text)

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
                "prices": prices
            })

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

    args = parser.parse_args()

    if args.command == "search":
        result = search_prices(args.query, args.max_results)

        if args.output == "pretty":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # Compact JSON for Rust parsing
            print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
