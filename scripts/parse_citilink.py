#!/usr/bin/env python3
"""
Парсер Citilink для archbook (резидентный IP)

Использование:
    python parse_citilink.py "MacBook Pro 16"
    python parse_citilink.py "iPhone 15 Pro"
"""

import re
import sys
import time
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


@dataclass
class Product:
    name: str
    price: int
    old_price: Optional[int]
    available: bool
    url: str


def search_citilink(query: str, max_results: int = 10) -> List[Product]:
    """Поиск товаров на Citilink"""

    products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        # Применяем stealth
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        # Поиск
        search_url = f"https://www.citilink.ru/search/?text={query.replace(' ', '+')}"
        print(f"[Citilink] Поиск: {query}")
        print(f"URL: {search_url}")

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # Ждём загрузки товаров
            try:
                page.wait_for_selector("[data-meta-price]", timeout=15000)
            except:
                time.sleep(5)

            html = page.content()

            # Проверяем на CAPTCHA
            if "showcaptcha" in page.url.lower():
                print("[X] CAPTCHA redirect!")
                return []

            # Парсим JSON из Next.js
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                html
            )

            if match:
                try:
                    data = json.loads(match.group(1))
                    props = data.get("props", {}).get("pageProps", {}).get("effectorValues", {})

                    for key, value in props.items():
                        if isinstance(value, dict) and "products" in value:
                            for item in value["products"][:max_results]:
                                products.append(Product(
                                    name=item.get("name", "")[:100],
                                    price=item.get("price", {}).get("price", 0),
                                    old_price=item.get("price", {}).get("old"),
                                    available=item.get("isAvailable", False),
                                    url=f"https://www.citilink.ru/product/{item.get('slug', '')}/"
                                ))
                            break
                except json.JSONDecodeError:
                    pass

            # Fallback: парсим data-meta-price атрибуты
            if not products:
                prices = re.findall(r'data-meta-price="(\d+)"', html)
                for price in prices[:max_results]:
                    products.append(Product(
                        name="Unknown",
                        price=int(price),
                        old_price=None,
                        available=True,
                        url=""
                    ))

        except Exception as e:
            print(f"[!] Ошибка: {e}")

        finally:
            browser.close()

    return products


def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"

    print("=" * 70)
    print("CITILINK PARSER (archbook)")
    print("=" * 70)

    products = search_citilink(query)

    if products:
        print(f"\n[+] Найдено товаров: {len(products)}")
        print("-" * 70)

        for i, p in enumerate(products, 1):
            status = "[+]" if p.available else "[-]"
            discount = ""
            if p.old_price and p.old_price > p.price:
                discount = f" (было {p.old_price:,})".replace(",", " ")

            print(f"{i}. {status} {p.price:,} RUB{discount}".replace(",", " "))
            print(f"   {p.name[:65]}...")
            if p.url:
                print(f"   {p.url[:65]}...")
            print()

        # Сортировка по цене
        sorted_products = sorted(products, key=lambda x: x.price)
        print("-" * 70)
        print(f"Минимальная цена: {sorted_products[0].price:,} RUB".replace(",", " "))
        print(f"Максимальная цена: {sorted_products[-1].price:,} RUB".replace(",", " "))

        # Только в наличии
        available = [p for p in products if p.available]
        if available:
            min_available = min(available, key=lambda x: x.price)
            print(f"Минимальная в наличии: {min_available.price:,} RUB".replace(",", " "))
    else:
        print("\n[X] Товары не найдены")


if __name__ == "__main__":
    main()
