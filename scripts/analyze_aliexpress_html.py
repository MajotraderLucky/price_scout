#!/usr/bin/env python3
"""
Analyze AliExpress HTML structure to find price selectors
"""

import re
from pathlib import Path

html_file = Path("/home/ryazanov/Development/price_scout/data/aliexpress_debug.html")
html = html_file.read_text(encoding='utf-8')

print("Analyzing AliExpress HTML structure...")
print("=" * 80)

# Find all occurrences of ₽ symbol with surrounding HTML
pattern = r'(.{0,200}₽.{0,200})'
matches = re.findall(pattern, html)

print(f"\nFound {len(matches)} price patterns")
print("\nFirst 3 examples with context:\n")

for i, match in enumerate(matches[:3], 1):
    print(f"Example {i}:")
    print(match)
    print("\n" + "-" * 80 + "\n")

# Look for common div/span patterns around prices
print("\nLooking for common HTML patterns around prices:")
print("=" * 80)

# Extract div/span tags around ₽
price_html_pattern = r'<(div|span)[^>]*>([^<]*₽[^<]*)</\1>'
price_tags = re.findall(price_html_pattern, html)

if price_tags:
    print(f"\nFound {len(price_tags)} direct price tags:")
    for tag, content in price_tags[:5]:
        print(f"  <{tag}>{content}</{tag}>")
else:
    print("\nNo direct price tags found. Prices might be in nested structure.")

# Look for data-price or similar attributes
data_price_pattern = r'data-price[^=]*="([^"]*)"'
data_prices = re.findall(data_price_pattern, html, re.IGNORECASE)

if data_prices:
    print(f"\nFound {len(data_prices)} data-price attributes:")
    print(f"  First 5: {data_prices[:5]}")
else:
    print("\nNo data-price attributes found")

# Look for JSON-LD or structured data
jsonld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
jsonld_matches = re.findall(jsonld_pattern, html, re.DOTALL)

if jsonld_matches:
    print(f"\nFound {len(jsonld_matches)} JSON-LD blocks")
    import json
    for i, jsonld in enumerate(jsonld_matches[:2], 1):
        try:
            data = json.loads(jsonld)
            print(f"\nJSON-LD block {i}:")
            print(f"  Type: {data.get('@type', 'unknown')}")
            if 'offers' in data:
                print(f"  Has offers!")
        except json.JSONDecodeError:
            continue
else:
    print("\nNo JSON-LD structured data found")

# Look for Next.js data or similar
nextjs_pattern = r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>'
nextjs_matches = re.findall(nextjs_pattern, html, re.DOTALL)

if nextjs_matches:
    print(f"\n✓ Found __NEXT_DATA__ block!")
    import json
    try:
        data = json.loads(nextjs_matches[0])
        print(f"  Keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        print(f"  Failed to parse: {e}")
else:
    print("\n✗ No __NEXT_DATA__ found")

print("\n" + "=" * 80)
print("Analysis complete!")
