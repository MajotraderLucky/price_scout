#!/usr/bin/env python3
"""
Test parse_aliexpress_runparams() directly on saved HTML
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Import the parser from test_scrapers
from test_scrapers import parse_aliexpress_runparams

# Load saved HTML
html_file = Path("/home/ryazanov/Development/price_scout/data/aliexpress_debug.html")
html = html_file.read_text(encoding='utf-8')

print("Testing parse_aliexpress_runparams() on saved HTML...")
print("=" * 80)

result = parse_aliexpress_runparams(html)

if result:
    print("\n✓ Parser SUCCESS!")
    print(f"  Price: {result['price']} kopecks ({result['price']/100:.2f} RUB)")
    print(f"  Name: {result['name']}")
    print(f"  Available: {result['available']}")
    print(f"  Matched products: {result['matched_products']}")
    print(f"  Total products: {result['total_products']}")
else:
    print("\n✗ Parser FAILED!")

print("=" * 80)
