#!/usr/bin/env python3
"""
DNS-Shop HTML Parser
Извлекает цены из сохранённых HTML страниц DNS-Shop
"""

import sys
import re
import json
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


def parse_with_regex(html: str) -> list[dict]:
    """Парсинг через regex (fallback)"""
    products = []

    # Паттерн 1: JSON.stringify format (динамическая вставка JSON-LD)
    stringify_match = re.search(r'JSON\.stringify\((\{[^}]+\}[^)]+)\)', html)
    if stringify_match:
        try:
            raw = stringify_match.group(1).replace('\\/', '/')
            data = json.loads(raw)
            if 'offers' in data:
                offers = data['offers']
                products.append({
                    'name': data.get('name', 'Unknown'),
                    'price_low': offers.get('lowPrice'),
                    'price_high': offers.get('highPrice'),
                    'count': offers.get('offerCount'),
                    'currency': offers.get('priceCurrency', 'RUB'),
                    'source': 'JSON.stringify'
                })
            if 'aggregateRating' in data:
                products[-1]['rating'] = data['aggregateRating'].get('ratingValue')
                products[-1]['reviews'] = data['aggregateRating'].get('reviewCount')
        except (json.JSONDecodeError, IndexError):
            pass

    # Паттерн 2: Стандартный JSON-LD
    ld_match = re.search(r'<script type="application/ld\+json">(.+?)</script>', html, re.DOTALL)
    if ld_match:
        try:
            data = json.loads(ld_match.group(1))
            if 'offers' in data:
                offers = data['offers']
                if isinstance(offers, dict):
                    products.append({
                        'name': data.get('name', 'Unknown'),
                        'price_low': offers.get('lowPrice'),
                        'price_high': offers.get('highPrice'),
                        'count': offers.get('offerCount'),
                        'currency': offers.get('priceCurrency', 'RUB'),
                        'source': 'ld+json'
                    })
        except json.JSONDecodeError:
            pass

    # Паттерн для data-product-price
    prices = re.findall(r'data-product-price="(\d+)"', html)
    for price in prices:
        p = int(price)
        if p > 50000:  # Фильтр для ноутбуков
            products.append({'price': p, 'source': 'data-product-price'})

    # Паттерн для product-buy__price
    price_matches = re.findall(r'product-buy__price[^>]*>([^<]+)', html)
    for match in price_matches:
        clean = re.sub(r'\s+', '', match)
        if clean.isdigit():
            p = int(clean)
            if p > 50000:
                products.append({'price': p, 'source': 'product-buy__price'})

    return products


def parse_with_bs4(html: str) -> list[dict]:
    """Парсинг через BeautifulSoup"""
    soup = BeautifulSoup(html, 'html.parser')
    products = []

    # Ищем карточки товаров
    cards = soup.select('[data-id]')

    for card in cards:
        product = {}

        # ID товара
        product['id'] = card.get('data-id')

        # Цена
        price_attr = card.get('data-product-price')
        if price_attr:
            product['price'] = int(price_attr)

        # Название
        title_elem = card.select_one('.catalog-product__name, .product-info__title a')
        if title_elem:
            product['name'] = title_elem.get_text(strip=True)

        # URL
        link = card.select_one('a[href*="/product/"]')
        if link:
            product['url'] = 'https://www.dns-shop.ru' + link.get('href', '')

        if product.get('price') and product.get('price') > 50000:
            products.append(product)

    # Если карточки не найдены, пробуем JSON-LD
    if not products:
        ld_script = soup.select_one('script[type="application/ld+json"]')
        if ld_script:
            try:
                data = json.loads(ld_script.string)
                if 'offers' in data:
                    products.append({
                        'name': data.get('name'),
                        'price_low': data['offers'].get('lowPrice'),
                        'price_high': data['offers'].get('highPrice'),
                        'count': data['offers'].get('offerCount')
                    })
            except (json.JSONDecodeError, KeyError):
                pass

    return products


def main():
    if len(sys.argv) < 2:
        html_path = Path('/tmp/dns_qute/page.html')
    else:
        html_path = Path(sys.argv[1])

    if not html_path.exists():
        print(f"[!] Файл не найден: {html_path}")
        sys.exit(1)

    html = html_path.read_text(encoding='utf-8', errors='ignore')

    # Извлекаем title
    title_match = re.search(r'<title>([^<]+)</title>', html)
    if title_match:
        print(f"Страница: {title_match.group(1)[:80]}")

    print(f"Размер: {len(html):,} bytes")
    print()

    # Парсим
    if HAS_BS4:
        print("=== Парсинг через BeautifulSoup ===")
        products = parse_with_bs4(html)
    else:
        print("=== Парсинг через regex (bs4 не установлен) ===")
        products = parse_with_regex(html)

    if not products:
        print("[!] Товары не найдены")
        print()
        print("Попытка regex поиска цен:")
        products = parse_with_regex(html)

    # Выводим результаты
    seen_prices = set()
    catalog_data = None

    for p in products:
        if 'price_low' in p and 'price_high' in p:
            catalog_data = p
        elif 'price' in p:
            price = p['price']
            if price not in seen_prices:
                seen_prices.add(price)
                name = p.get('name', 'N/A')[:50]
                print(f"  {price:>10,} ₽  {name}")

    if catalog_data:
        print()
        print(f"=== {catalog_data.get('name', 'Каталог')} ===")
        print(f"  Мин. цена:  {catalog_data['price_low']:>10,} ₽")
        print(f"  Макс. цена: {catalog_data['price_high']:>10,} ₽")
        if catalog_data.get('count'):
            print(f"  Моделей:    {catalog_data['count']:>10}")
        if catalog_data.get('rating'):
            print(f"  Рейтинг:    {catalog_data['rating']}/5 ({catalog_data.get('reviews', 0):,} отзывов)")
        print(f"  Источник:   {catalog_data.get('source', 'unknown')}")

    print()
    print(f"Найдено уникальных цен: {len(seen_prices)}")


if __name__ == '__main__':
    main()
