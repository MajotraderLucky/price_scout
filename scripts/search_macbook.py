#!/usr/bin/env python3
"""
Поиск конкретного товара: MacBook Pro 16 2021 M1 Pro 32GB 512GB

Шаг 1: Пользователь вводит запрос
Шаг 2: Получаем список ссылок
Шаг 3: Анализируем каждую ссылку
"""

from duckduckgo_search import DDGS
from urllib.parse import urlparse
import re

# Целевой товар
PRODUCT = {
    "name": "MacBook Pro 16 2021 M1 Pro",
    "ram": "32GB",
    "ssd": "512GB",
    "color": "Space Gray",
    "article": "Z14V0008D",
}

# Известные магазины
KNOWN_SHOPS = {
    "market.yandex.ru": "Яндекс.Маркет",
    "ozon.ru": "Ozon",
    "wildberries.ru": "Wildberries",
    "dns-shop.ru": "DNS",
    "mvideo.ru": "М.Видео",
    "citilink.ru": "Ситилинк",
    "eldorado.ru": "Эльдорадо",
    "re-store.ru": "re:Store",
    "apple.com": "Apple",
    "aliexpress.ru": "AliExpress",
    "avito.ru": "Авито",
    "technopark.ru": "Технопарк",
}


def build_search_query(product: dict) -> str:
    """Построить поисковый запрос"""
    # Разные варианты запроса
    queries = [
        f"купить {product['name']} {product['ram']} {product['ssd']} цена",
        f"{product['name']} {product['article']} купить",
        f"MacBook Pro 16 M1 Pro 32 512 купить цена",
    ]
    return queries[0]


def extract_price_from_text(text: str) -> list:
    """Извлечь цены из текста"""
    # Паттерны для цен
    patterns = [
        r'(\d{3}[\s\u00a0]?\d{3})\s*(?:₽|руб|р\.)',
        r'(\d{2,3}[\s\u00a0]?\d{3})\s*(?:₽|руб|р\.)',
        r'от\s*(\d{2,3}[\s\u00a0]?\d{3})',
    ]

    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            clean = match.replace(" ", "").replace("\u00a0", "")
            if clean.isdigit():
                price = int(clean)
                # Фильтр разумных цен для MacBook (100K - 500K)
                if 100000 < price < 500000:
                    prices.append(price)

    return sorted(set(prices))


def search_product():
    """Поиск товара через DuckDuckGo"""

    query = build_search_query(PRODUCT)

    print("=" * 70)
    print("ШАГ 1: ПОИСК ТОВАРА")
    print("=" * 70)
    print(f"\nТовар: {PRODUCT['name']}")
    print(f"Конфигурация: {PRODUCT['ram']} / {PRODUCT['ssd']}")
    print(f"Артикул: {PRODUCT['article']}")
    print(f"\nПоисковый запрос: '{query}'")

    print("\n[Поиск...]")

    with DDGS() as ddgs:
        results = list(ddgs.text(query, region="ru-ru", max_results=30))

    print(f"Найдено результатов: {len(results)}")

    # Сортировка по магазинам
    print("\n" + "=" * 70)
    print("ШАГ 2: АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 70)

    shops_found = []
    other_results = []

    for r in results:
        url = r.get("href", "")
        title = r.get("title", "")
        snippet = r.get("body", "")
        domain = urlparse(url).netloc.replace("www.", "")

        # Проверяем, это магазин?
        shop_name = None
        for shop_domain, name in KNOWN_SHOPS.items():
            if shop_domain in domain:
                shop_name = name
                break

        # Извлекаем цены из сниппета
        prices = extract_price_from_text(snippet)

        entry = {
            "shop": shop_name,
            "domain": domain,
            "url": url,
            "title": title[:60],
            "snippet": snippet[:100],
            "prices_in_snippet": prices,
        }

        if shop_name:
            shops_found.append(entry)
        else:
            other_results.append(entry)

    # Вывод магазинов
    print(f"\n### Найдено магазинов: {len(shops_found)}")
    print("-" * 70)

    for i, shop in enumerate(shops_found, 1):
        print(f"\n[{i}] {shop['shop']}")
        print(f"    URL: {shop['url'][:70]}...")
        print(f"    Title: {shop['title']}...")
        if shop['prices_in_snippet']:
            print(f"    Цены в сниппете: {shop['prices_in_snippet']}")

    # Другие результаты
    if other_results:
        print(f"\n### Другие результаты: {len(other_results)}")
        print("-" * 70)
        for i, r in enumerate(other_results[:5], 1):
            print(f"\n[{i}] {r['domain']}")
            print(f"    {r['title']}...")

    # Сводка
    print("\n" + "=" * 70)
    print("СВОДКА")
    print("=" * 70)

    # Уникальные магазины
    unique_shops = list(set(s['shop'] for s in shops_found))
    print(f"\nМагазины: {', '.join(unique_shops)}")

    # Все цены из сниппетов
    all_prices = []
    for s in shops_found:
        all_prices.extend(s['prices_in_snippet'])

    if all_prices:
        all_prices = sorted(set(all_prices))
        print(f"Цены (из сниппетов): {all_prices}")
        print(f"Диапазон: {min(all_prices):,} - {max(all_prices):,} ₽".replace(",", " "))

    # Список URL для следующего шага
    print("\n" + "=" * 70)
    print("ШАГ 3: ССЫЛКИ ДЛЯ ДЕТАЛЬНОГО АНАЛИЗА")
    print("=" * 70)

    urls_to_check = []
    for s in shops_found:
        urls_to_check.append({
            "shop": s['shop'],
            "url": s['url']
        })
        print(f"\n{s['shop']}:")
        print(f"  {s['url']}")

    return urls_to_check


if __name__ == "__main__":
    urls = search_product()

    print("\n" + "=" * 70)
    print(f"Найдено {len(urls)} ссылок на магазины для проверки")
    print("=" * 70)
