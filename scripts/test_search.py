#!/usr/bin/env python3
"""
Тестовый скрипт: поиск цен через DuckDuckGo

Шаг 1: Поиск через поисковик
Шаг 2: Фильтрация ссылок на магазины
Шаг 3: Попытка получить страницу
Шаг 4: Базовый парсинг
"""

import sys

# Проверка зависимостей
try:
    from duckduckgo_search import DDGS
except ImportError:
    print("Установите: pip install duckduckgo-search")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Установите: pip install beautifulsoup4 lxml")
    sys.exit(1)

import requests
import re
from urllib.parse import urlparse

# Известные магазины
KNOWN_SHOPS = {
    "dns-shop.ru": "DNS",
    "mvideo.ru": "М.Видео",
    "citilink.ru": "Ситилинк",
    "eldorado.ru": "Эльдорадо",
    "ozon.ru": "Ozon",
    "wildberries.ru": "Wildberries",
    "market.yandex.ru": "Яндекс.Маркет",
    "regard.ru": "Регард",
    "technopark.ru": "Технопарк",
    "svyaznoy.ru": "Связной",
    "holodilnik.ru": "Холодильник.ру",
    "onlinetrade.ru": "Онлайн Трейд",
}


def search_product(query: str, max_results: int = 20) -> list:
    """Поиск товара через DuckDuckGo"""
    print(f"\n[ПОИСК] Запрос: '{query}'")

    with DDGS() as ddgs:
        results = list(ddgs.text(
            query,
            region="ru-ru",
            max_results=max_results
        ))

    print(f"[ПОИСК] Найдено результатов: {len(results)}")
    return results


def filter_shops(results: list) -> list:
    """Фильтрация только ссылок на магазины"""
    shops = []

    for r in results:
        url = r.get("href", "")
        domain = urlparse(url).netloc.replace("www.", "")

        for shop_domain, shop_name in KNOWN_SHOPS.items():
            if shop_domain in domain:
                shops.append({
                    "shop": shop_name,
                    "domain": shop_domain,
                    "url": url,
                    "title": r.get("title", ""),
                    "snippet": r.get("body", "")
                })
                break

    return shops


def extract_price_from_text(text: str) -> list:
    """Извлечь цены из текста с помощью regex"""
    # Паттерны для российских цен
    patterns = [
        r'(\d{1,3}(?:\s?\d{3})*)\s*(?:₽|руб\.?|RUB)',
        r'(?:цена|price|стоимость)[:\s]*(\d{1,3}(?:\s?\d{3})*)',
        r'(\d{1,3}(?:\s?\d{3})*)\s*(?:р\.|рублей)',
    ]

    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            price = match.replace(" ", "").replace("\u00a0", "")
            if price.isdigit() and 1000 < int(price) < 10000000:
                prices.append(int(price))

    return list(set(prices))


def fetch_page(url: str) -> tuple:
    """Получить страницу и вернуть (status_code, html или error)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        return (resp.status_code, resp.text)
    except requests.exceptions.Timeout:
        return (0, "Timeout")
    except requests.exceptions.ConnectionError as e:
        return (0, f"Connection error: {e}")
    except Exception as e:
        return (0, f"Error: {e}")


def analyze_page(html: str) -> dict:
    """Анализ HTML страницы"""
    soup = BeautifulSoup(html, "lxml")

    result = {
        "title": None,
        "prices": [],
        "has_captcha": False,
        "has_product": False,
    }

    # Title
    title_tag = soup.find("title")
    if title_tag:
        result["title"] = title_tag.text.strip()[:100]

    # Проверка на CAPTCHA
    captcha_indicators = ["captcha", "recaptcha", "robot", "проверка"]
    page_text = soup.get_text().lower()
    for indicator in captcha_indicators:
        if indicator in page_text:
            result["has_captcha"] = True
            break

    # Проверка на страницу товара (Schema.org)
    if soup.find(itemprop="product") or soup.find(itemtype=re.compile("Product")):
        result["has_product"] = True

    # Извлечение цен из HTML
    result["prices"] = extract_price_from_text(soup.get_text())

    return result


def main():
    # Товар для поиска
    product = "Samsung Galaxy S24 256GB"
    query = f"купить {product} цена"

    print("=" * 60)
    print("ТЕСТ: Поиск цен через поисковик")
    print("=" * 60)

    # Шаг 1: Поиск
    results = search_product(query)

    if not results:
        print("[ОШИБКА] Поиск не вернул результатов")
        return

    # Шаг 2: Фильтрация магазинов
    shops = filter_shops(results)
    print(f"\n[ФИЛЬТР] Найдено магазинов: {len(shops)}")

    for i, shop in enumerate(shops, 1):
        print(f"  {i}. {shop['shop']}: {shop['title'][:50]}...")

    # Шаг 3: Анализ всех результатов (включая немагазины)
    print("\n" + "=" * 60)
    print("АНАЛИЗ РЕЗУЛЬТАТОВ ПОИСКА")
    print("=" * 60)

    for i, r in enumerate(results[:10], 1):
        title = r.get("title", "")[:50]
        url = r.get("href", "")
        snippet = r.get("body", "")

        # Извлечь цены из сниппета
        prices = extract_price_from_text(snippet)

        domain = urlparse(url).netloc.replace("www.", "")

        print(f"\n[{i}] {title}...")
        print(f"    Домен: {domain}")
        if prices:
            print(f"    Цены в сниппете: {prices}")
        else:
            print(f"    Цены: не найдены в сниппете")

    # Шаг 4: Попытка загрузить первый магазин
    if shops:
        print("\n" + "=" * 60)
        print("ТЕСТ ЗАГРУЗКИ СТРАНИЦЫ")
        print("=" * 60)

        shop = shops[0]
        print(f"\n[ЗАПРОС] {shop['shop']}: {shop['url'][:60]}...")

        status, content = fetch_page(shop['url'])

        if status == 200:
            print(f"[OK] Status: {status}, Size: {len(content)} bytes")

            analysis = analyze_page(content)
            print(f"    Title: {analysis['title']}")
            print(f"    Captcha: {'ДА' if analysis['has_captcha'] else 'Нет'}")
            print(f"    Product page: {'ДА' if analysis['has_product'] else 'Нет'}")
            if analysis['prices']:
                print(f"    Найденные цены: {sorted(analysis['prices'])[:5]}")
        else:
            print(f"[ОШИБКА] Status: {status}")
            print(f"    Причина: {content[:100] if isinstance(content, str) else content}")

    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)


if __name__ == "__main__":
    main()
