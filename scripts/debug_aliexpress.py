#!/usr/bin/env python3
"""
Debug script to analyze AliExpress HTML structure
"""

import re
import time
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# URL
query = "macbook pro 16"
url = f"https://aliexpress.ru/wholesale?SearchText={quote_plus(query)}"

print(f"Testing URL: {url}")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
        ]
    )

    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        locale="ru-RU",
        timezone_id="Europe/Moscow",
    )

    page = context.new_page()

    # Apply stealth
    stealth = Stealth(
        navigator_languages_override=("ru-RU", "ru"),
        navigator_platform_override="Win32",
    )
    stealth.apply_stealth_sync(page)

    # Load page
    print("Loading page...")
    time.sleep(5)  # Initial delay
    response = page.goto(url, wait_until="domcontentloaded", timeout=60000)

    print(f"HTTP Status: {response.status}")
    print(f"Final URL: {page.url}")
    print("=" * 80)

    # Wait and scroll
    time.sleep(3)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    time.sleep(2)

    # Get HTML
    html = page.content()

    # Save to file
    output_file = "/home/ryazanov/Development/price_scout/data/aliexpress_debug.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML saved to: {output_file}")
    print(f"HTML length: {len(html)} characters")
    print("=" * 80)

    # Check for window.runParams
    if "window.runParams" in html:
        print("✓ window.runParams FOUND!")

        # Extract it
        pattern = r'window\.runParams\s*=\s*(\{.*?\});'
        match = re.search(pattern, html, re.DOTALL)

        if match:
            print(f"✓ Regex matched! Data length: {len(match.group(1))} characters")
            print("\nFirst 500 characters of runParams:")
            print(match.group(1)[:500])
        else:
            print("✗ Regex did NOT match")
    else:
        print("✗ window.runParams NOT FOUND")

    # Check for alternative data sources
    print("\n" + "=" * 80)
    print("Checking alternative data sources:")
    print("=" * 80)

    keywords = ["window.data", "window.__data", "window.__INITIAL_STATE__", "window.AE_DATA", "__state__", "runParams"]
    for keyword in keywords:
        if keyword in html:
            print(f"✓ Found: {keyword}")
        else:
            print(f"✗ Not found: {keyword}")

    # Check for CAPTCHA
    if "captcha" in html.lower() or "showcaptcha" in page.url.lower():
        print("\n⚠ CAPTCHA detected!")

    # Check for price elements (fallback)
    print("\n" + "=" * 80)
    print("Checking for price elements:")
    print("=" * 80)

    price_patterns = [
        r'\d+[,.]?\d*\s*₽',
        r'\d+[,.]?\d*\s*RUB',
        r'data-price="(\d+)"',
        r'"price":\s*(\d+)',
    ]

    for pattern in price_patterns:
        matches = re.findall(pattern, html)
        if matches:
            print(f"✓ Pattern '{pattern}': {len(matches)} matches")
            print(f"  First 5: {matches[:5]}")
        else:
            print(f"✗ Pattern '{pattern}': No matches")

    browser.close()

print("\nDebug script completed!")
