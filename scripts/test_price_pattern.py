#!/usr/bin/env python3
"""
Test price extraction patterns on saved HTML
"""

import re
from pathlib import Path

html_file = Path("/home/ryazanov/Development/price_scout/data/aliexpress_debug.html")
html = html_file.read_text(encoding='utf-8')

print("Testing price patterns...")
print("=" * 80)

# Pattern 1: Original (strict)
pattern1 = r'<span[^>]*>(\d+(?:&nbsp;|\s)\d+(?:&nbsp;|\s)*₽)</span>'
matches1 = re.findall(pattern1, html)
print(f"\nPattern 1 (strict with separator): {len(matches1)} matches")
if matches1:
    print(f"  First 5: {matches1[:5]}")

# Pattern 2: More flexible (allow optional separators)
pattern2 = r'<span[^>]*>(\d[\d\s&nbsp;]*₽)</span>'
matches2 = re.findall(pattern2, html)
print(f"\nPattern 2 (flexible): {len(matches2)} matches")
if matches2:
    print(f"  First 5: {matches2[:5]}")

# Pattern 3: Just digits followed by ₽
pattern3 = r'>(\d+(?:\s|&nbsp;)*\d*(?:\s|&nbsp;)*₽)<'
matches3 = re.findall(pattern3, html)
print(f"\nPattern 3 (very flexible): {len(matches3)} matches")
if matches3:
    print(f"  First 10: {matches3[:10]}")

# Pattern 4: Looking for actual product prices (multi-digit with separators)
pattern4 = r'<span[^>]*>(\d{1,3}(?:&nbsp;|\s)\d{3}(?:&nbsp;|\s)*₽)</span>'
matches4 = re.findall(pattern4, html)
print(f"\nPattern 4 (product prices with thousands): {len(matches4)} matches")
if matches4:
    print(f"  First 5: {matches4[:5]}")

# Test cleaning function
print("\n" + "=" * 80)
print("Testing price cleaning:")

test_prices = [
    "4&nbsp;500&nbsp;₽",
    "2&nbsp;351&nbsp;₽",
    "100 000 ₽",
    "45000₽"
]

for price_str in test_prices:
    clean = price_str.replace('&nbsp;', '').replace(' ', '').replace('₽', '').strip()
    try:
        price_num = int(clean) * 100
        print(f"  '{price_str}' -> {clean} -> {price_num} kopecks ({price_num/100:.2f} RUB)")
    except ValueError as e:
        print(f"  '{price_str}' -> ERROR: {e}")

print("\n" + "=" * 80)
