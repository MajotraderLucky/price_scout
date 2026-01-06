#!/usr/bin/env python3
"""
Find product card structure in AliExpress HTML
"""

import re
from pathlib import Path

html_file = Path("/home/ryazanov/Development/price_scout/data/aliexpress_debug.html")
html = html_file.read_text(encoding='utf-8')

print("Looking for product card structure...")
print("=" * 80)

# Find product prices with proper format (excluding promotional "-300₽")
price_pattern = r'<span[^>]*>(\d+(?:&nbsp;\d+)*\s*₽)</span>'
prices = re.findall(price_pattern, html)

print(f"\nFound {len(prices)} product prices:")
for i, price in enumerate(prices[:10], 1):
    clean_price = price.replace('&nbsp;', ' ')
    print(f"  {i}. {clean_price}")

# Find product titles/names near prices
# Look for larger context around prices
print("\n" + "=" * 80)
print("Extracting product cards with context:\n")

# Pattern to find product card div with price
card_pattern = r'<div[^>]*class="[^"]*"[^>]*>(.*?<span[^>]*>\d+(?:&nbsp;\d+)*\s*₽</span>.*?)</div>'
cards = re.findall(card_pattern, html, re.DOTALL)

print(f"Found {len(cards)} potential product cards")

if cards:
    # Analyze first few cards
    for i, card in enumerate(cards[:3], 1):
        print(f"\nCard {i} (truncated to 500 chars):")
        print(card[:500])
        print("...")
        print("\n" + "-" * 80)

# Look for title patterns
print("\n" + "=" * 80)
print("Looking for product titles...")

# Common title patterns in e-commerce
title_patterns = [
    r'<h\d[^>]*>(.*?)</h\d>',  # Headers
    r'<a[^>]*title="([^"]*)"[^>]*>',  # Links with title attribute
    r'<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>',  # Divs with "title" in class
    r'<span[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</span>',  # Spans with "title" in class
]

for pattern_desc, pattern in zip(
    ["Headers", "Link titles", "Div titles", "Span titles"],
    title_patterns
):
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
    if matches:
        print(f"\n{pattern_desc}: {len(matches)} matches")
        # Show first 5 non-empty matches
        clean_matches = [m.strip()[:100] for m in matches if m.strip()][:5]
        for j, match in enumerate(clean_matches, 1):
            print(f"  {j}. {match}")

# Look for data attributes that might contain product info
print("\n" + "=" * 80)
print("Looking for data attributes...")

data_patterns = [
    r'data-product-id="([^"]*)"',
    r'data-sku="([^"]*)"',
    r'data-spm="([^"]*)"',
    r'data-item-id="([^"]*)"',
]

for pattern in data_patterns:
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        attr_name = pattern.split('="')[0]
        print(f"\n{attr_name}: {len(matches)} matches")
        print(f"  First 5: {matches[:5]}")

print("\n" + "=" * 80)
print("Analysis complete!")
