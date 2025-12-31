#!/usr/bin/env python3
"""
Поиск цены на MacBook Pro 16 2021 M1 Pro 32GB 512GB (Z14V0008D)

Полный цикл:
1. Поиск по артикулу через DuckDuckGo
2. Проверка каждой ссылки
3. Извлечение цены
"""

import re
import json
import time
from duckduckgo_search import DDGS
from playwright.sync_api import sync_playwright

# Целевой товар
PRODUCT = {
    "name": "MacBook Pro 16 2021 M1 Pro 32GB 512GB",
    "article": "Z14V0008D",
    "ram": "32GB",
    "ssd": "512GB",
}


def search_product(article: str) -> list:
    """Поиск по артикулу"""
    query = f"{article} купить цена"
    print(f"\n[ПОИСК] Запрос: '{query}'")

    with DDGS() as ddgs:
        results = list(ddgs.text(query, region="ru-ru", max_results=20))

    print(f"[ПОИСК] Найдено: {len(results)} результатов")
    return results


def extract_price_from_html(html: str, min_price: int = 100000, max_price: int = 400000) -> list:
    """Извлечь цены из HTML"""
    prices = []

    # Schema.org price
    match = re.search(r'itemprop="price"\s+content="(\d+)"', html)
    if match:
        prices.append(int(match.group(1)))

    # JSON цены
    for match in re.findall(r'"price"[:\s]*(\d+)', html):
        p = int(match)
        if min_price < p < max_price:
            prices.append(p)

    # Текстовые цены
    for match in re.findall(r'(\d{3}[\s\u00a0]?\d{3})\s*(?:₽|руб)', html):
        clean = match.replace(" ", "").replace("\u00a0", "")
        if clean.isdigit():
            p = int(clean)
            if min_price < p < max_price:
                prices.append(p)

    return sorted(set(prices))


def extract_availability(html: str) -> str:
    """Извлечь информацию о наличии"""
    if 'InStock' in html or 'instock' in html.lower():
        return "В наличии"
    elif 'SoldOut' in html or 'OutOfStock' in html:
        return "Нет в наличии"
    elif 'PreOrder' in html:
        return "Предзаказ"
    return "Неизвестно"


def check_url(url: str, browser) -> dict:
    """Проверить URL и извлечь данные"""
    page = browser.new_page()

    try:
        resp = page.goto(url, timeout=15000)

        if resp.status != 200:
            return {"status": f"HTTP {resp.status}", "price": None}

        time.sleep(2)
        html = page.content()

        # Проверка защиты
        if 'captcha' in html.lower():
            return {"status": "CAPTCHA", "price": None}
        if 'blocked' in html.lower() or 'access denied' in html.lower():
            return {"status": "Blocked", "price": None}

        # Извлечение данных
        prices = extract_price_from_html(html)
        availability = extract_availability(html)

        return {
            "status": "OK",
            "price": prices[0] if prices else None,
            "all_prices": prices,
            "availability": availability,
        }

    except Exception as e:
        return {"status": f"Error: {type(e).__name__}", "price": None}

    finally:
        page.close()


def main():
    print("=" * 70)
    print(f"ПОИСК ЦЕНЫ: {PRODUCT['name']}")
    print(f"Артикул: {PRODUCT['article']}")
    print("=" * 70)

    # Шаг 1: Поиск
    results = search_product(PRODUCT['article'])

    # Фильтрация - только прямые ссылки на товар
    urls_to_check = []
    for r in results:
        url = r.get('href', '')
        # Пропускаем маркетплейсы с CAPTCHA
        if any(x in url for x in ['yandex', 'ozon.ru', 'wildberries', 'avito']):
            continue
        if PRODUCT['article'].lower() in url.lower():
            urls_to_check.append(url)

    print(f"\n[ФИЛЬТР] URL с артикулом: {len(urls_to_check)}")

    # Шаг 2: Проверка каждого URL
    print("\n" + "=" * 70)
    print("ПРОВЕРКА МАГАЗИНОВ")
    print("=" * 70)

    found_prices = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])

        for url in urls_to_check[:10]:
            # Извлекаем домен
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')

            print(f"\n[{domain}]")
            print(f"  URL: {url[:50]}...")

            result = check_url(url, browser)

            print(f"  Статус: {result['status']}")

            if result['price']:
                print(f"  Цена: {result['price']:,} ₽".replace(',', ' '))
                print(f"  Наличие: {result.get('availability', 'N/A')}")

                found_prices.append({
                    "shop": domain,
                    "price": result['price'],
                    "availability": result.get('availability'),
                    "url": url,
                })

        browser.close()

    # Шаг 3: Результаты
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 70)

    if found_prices:
        # Сортировка по цене
        found_prices.sort(key=lambda x: x['price'])

        print(f"\nНайдено предложений: {len(found_prices)}")
        print("-" * 70)

        for i, offer in enumerate(found_prices, 1):
            in_stock = "[+]" if offer['availability'] == "В наличии" else "[-]"
            print(f"{i}. {offer['shop']}: {offer['price']:,} ₽ {in_stock}".replace(',', ' '))

        print("\n" + "-" * 70)
        min_price = found_prices[0]['price']
        max_price = found_prices[-1]['price']
        print(f"Минимальная цена: {min_price:,} ₽".replace(',', ' '))
        print(f"Максимальная цена: {max_price:,} ₽".replace(',', ' '))

    else:
        print("\nЦены не найдены. Возможные причины:")
        print("- Все магазины используют CAPTCHA")
        print("- Товар снят с продажи")
        print("- Нужен VPN/прокси")


if __name__ == "__main__":
    main()
