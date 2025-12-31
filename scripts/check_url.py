#!/usr/bin/env python3
"""
Проверка конкретного URL - получение цены товара

Шаг 3: Анализ каждой ссылки из поиска
"""

import sys
import re
import json
import requests
from urllib.parse import urlparse

# Тестовые URL из поиска
TEST_URLS = [
    {
        "shop": "Яндекс.Маркет",
        "url": "https://market.yandex.ru/product--noutbuk-apple-macbook-pro-16-2021-m1-pro-10c-cpu-16c-gpu-32gb-512gb-ssd-space-gray-z14v0008d-rus/1495790507",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}


def extract_prices(text: str) -> list:
    """Извлечь цены из текста"""
    prices = []

    # Паттерны для цен (100K - 500K для MacBook)
    patterns = [
        r'(\d{3}[\s\u00a0]?\d{3})\s*(?:₽|руб)',
        r'"price":\s*(\d+)',
        r'"lowPrice":\s*(\d+)',
        r'"value":\s*"?(\d+)"?',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            clean = str(match).replace(" ", "").replace("\u00a0", "")
            if clean.isdigit():
                price = int(clean)
                if 100000 < price < 500000:
                    prices.append(price)

    return sorted(set(prices))


def extract_json_ld(html: str) -> list:
    """Извлечь данные из JSON-LD (Schema.org)"""
    data = []

    pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

    for match in matches:
        try:
            json_data = json.loads(match)
            data.append(json_data)
        except:
            pass

    return data


def check_url(url: str, shop_name: str = "Unknown"):
    """Проверить URL и извлечь данные"""

    print(f"\n{'='*70}")
    print(f"ПРОВЕРКА: {shop_name}")
    print(f"{'='*70}")
    print(f"URL: {url[:70]}...")

    domain = urlparse(url).netloc

    # Попытка HTTP запроса
    print("\n[1] HTTP запрос...")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        print(f"    Status: {resp.status_code}")
        print(f"    Size: {len(resp.content):,} bytes")
        print(f"    Final URL: {resp.url[:60]}...")

        if resp.status_code != 200:
            print(f"    [!] Неуспешный статус")
            return None

        html = resp.text

        # Проверка на блокировку
        print("\n[2] Проверка на защиту...")
        lower_html = html.lower()

        if "captcha" in lower_html:
            print("    [!] CAPTCHA обнаружена")
            return {"status": "captcha", "prices": []}
        elif "access denied" in lower_html or "blocked" in lower_html:
            print("    [!] Доступ заблокирован")
            return {"status": "blocked", "prices": []}
        else:
            print("    [+] Защита не обнаружена")

        # Извлечение title
        print("\n[3] Извлечение данных...")
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            print(f"    Title: {title_match.group(1)[:60]}...")

        # JSON-LD данные
        print("\n[4] Поиск JSON-LD (Schema.org)...")
        json_ld = extract_json_ld(html)
        print(f"    Найдено JSON-LD блоков: {len(json_ld)}")

        product_data = None
        for data in json_ld:
            if isinstance(data, dict):
                # Проверяем @type
                dtype = data.get("@type", "")
                if dtype == "Product" or "Product" in str(dtype):
                    product_data = data
                    print(f"    [+] Найден Product!")

                    # Название
                    name = data.get("name", "N/A")
                    print(f"    Название: {name[:50]}...")

                    # Цена
                    offers = data.get("offers", {})
                    if isinstance(offers, dict):
                        price = offers.get("price") or offers.get("lowPrice")
                        currency = offers.get("priceCurrency", "RUB")
                        if price:
                            print(f"    Цена: {price} {currency}")

        # Извлечение цен из HTML
        print("\n[5] Поиск цен в HTML...")
        prices = extract_prices(html)
        if prices:
            print(f"    Найденные цены: {prices[:5]}")
        else:
            print("    Цены не найдены в HTML")

        # Сохранение HTML для анализа
        filename = f"debug_{domain.replace('.', '_')}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n[6] HTML сохранён: {filename}")

        return {
            "status": "ok",
            "prices": prices,
            "json_ld": product_data,
        }

    except requests.exceptions.Timeout:
        print("    [!] Timeout")
        return {"status": "timeout", "prices": []}
    except requests.exceptions.ConnectionError as e:
        print(f"    [!] Connection error: {e}")
        return {"status": "connection_error", "prices": []}
    except Exception as e:
        print(f"    [!] Error: {e}")
        return {"status": "error", "prices": []}


def main():
    print("=" * 70)
    print("ШАГ 3: ПРОВЕРКА ССЫЛОК ИЗ ПОИСКА")
    print("=" * 70)

    # URL из аргумента или тестовый
    if len(sys.argv) > 1:
        url = sys.argv[1]
        shop = "Custom"
    else:
        # Используем первый тестовый URL
        url = TEST_URLS[0]["url"]
        shop = TEST_URLS[0]["shop"]

    result = check_url(url, shop)

    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ")
    print("=" * 70)

    if result:
        print(f"Статус: {result['status']}")
        if result['prices']:
            print(f"Цены: {result['prices']}")
    else:
        print("Не удалось получить данные")


if __name__ == "__main__":
    main()
