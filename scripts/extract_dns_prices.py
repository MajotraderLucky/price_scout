#!/usr/bin/env python3
"""
DNS-Shop Price Extractor
Извлекает названия и коды товаров из сохранённого HTML,
затем получает цены через веб-поиск
"""

import re
import sys
import json
from pathlib import Path


def extract_products_from_html(html_path: str) -> list[dict]:
    """Извлекает информацию о товарах из HTML"""
    html = Path(html_path).read_text(encoding='utf-8', errors='ignore')
    products = []

    # Паттерн для извлечения карточек товаров
    # data-product="UUID" data-code="CODE"
    product_pattern = re.compile(
        r'data-product="([^"]+)"[^>]*data-code="(\d+)".*?'
        r'catalog-product__name[^>]*href="([^"]+)"[^>]*><span>([^<]+)',
        re.DOTALL
    )

    for match in product_pattern.finditer(html):
        uuid, code, url, name = match.groups()
        # Извлекаем краткое название
        short_name = name.split('[')[0].strip()

        # Извлекаем характеристики
        specs_match = re.search(r'\[([^\]]+)\]', name)
        specs = specs_match.group(1) if specs_match else ''

        # Извлекаем RAM и SSD
        ram_match = re.search(r'RAM\s*(\d+)\s*ГБ', specs)
        ssd_match = re.search(r'SSD\s*(\d+)\s*ГБ', specs)

        products.append({
            'code': code,
            'uuid': uuid,
            'url': f"https://www.dns-shop.ru{url}",
            'name': short_name,
            'full_name': name,
            'ram': ram_match.group(1) if ram_match else None,
            'ssd': ssd_match.group(1) if ssd_match else None
        })

    return products


def extract_catalog_info(html_path: str) -> dict:
    """Извлекает общую информацию о каталоге из JSON.stringify"""
    html = Path(html_path).read_text(encoding='utf-8', errors='ignore')

    match = re.search(r'JSON\.stringify\((\{[^}]+\}[^)]+)\)', html)
    if match:
        try:
            raw = match.group(1).replace('\\/', '/')
            data = json.loads(raw)
            return {
                'name': data.get('name'),
                'low_price': data.get('offers', {}).get('lowPrice'),
                'high_price': data.get('offers', {}).get('highPrice'),
                'count': data.get('offers', {}).get('offerCount'),
                'rating': data.get('aggregateRating', {}).get('ratingValue'),
                'reviews': data.get('aggregateRating', {}).get('reviewCount')
            }
        except json.JSONDecodeError:
            pass
    return {}


def main():
    if len(sys.argv) < 2:
        html_path = '/tmp/dns_macbook_source.html'
    else:
        html_path = sys.argv[1]

    if not Path(html_path).exists():
        print(f"[!] Файл не найден: {html_path}")
        sys.exit(1)

    # Извлекаем общую информацию
    catalog = extract_catalog_info(html_path)

    print("=" * 60)
    print(f"  DNS-SHOP: {catalog.get('name', 'Каталог')}")
    print("=" * 60)

    if catalog:
        print(f"\n  Диапазон цен: {catalog.get('low_price', 0):,} - {catalog.get('high_price', 0):,} ₽")
        print(f"  Моделей: {catalog.get('count', 'N/A')}")
        print(f"  Рейтинг: {catalog.get('rating', 'N/A')}/5 ({catalog.get('reviews', 0):,} отзывов)")

    # Извлекаем товары
    products = extract_products_from_html(html_path)

    print(f"\n  Найдено товаров на странице: {len(products)}")
    print()
    print("-" * 60)

    # Группируем по модели
    models = {}
    for p in products:
        model_key = p['name']
        if model_key not in models:
            models[model_key] = []
        models[model_key].append(p)

    # Выводим уникальные модели
    print(f"\n{'Код':<10} {'RAM':<6} {'SSD':<8} {'Модель'}")
    print("-" * 60)

    for model_name, variants in sorted(models.items(), key=lambda x: x[0]):
        for p in variants:
            ram = f"{p['ram']}GB" if p['ram'] else "?"
            ssd = f"{p['ssd']}GB" if p['ssd'] else "?"
            # Truncate name for display
            display_name = model_name[:40] if len(model_name) > 40 else model_name
            print(f"{p['code']:<10} {ram:<6} {ssd:<8} {display_name}")

    # Выводим JSON для дальнейшей обработки
    print("\n" + "=" * 60)
    print("JSON данные сохранены в: /tmp/dns_products.json")

    output = {
        'catalog': catalog,
        'products': products
    }

    with open('/tmp/dns_products.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
