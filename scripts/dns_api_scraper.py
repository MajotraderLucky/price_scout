#!/usr/bin/env python3
"""
DNS-Shop API Scraper
Извлекает данные о ценах без браузера (используя requests)
Работает для получения агрегированных данных из JSON-LD
"""

import sys
import json
import re
import time
import random
from pathlib import Path
from datetime import datetime

import urllib.request
import urllib.error
import gzip
from io import BytesIO


CATALOGS = {
    "macbook-pro": "https://www.dns-shop.ru/catalog/recipe/b70b01357dbede01/apple-macbook-pro/",
    "macbook": "https://www.dns-shop.ru/catalog/recipe/8ddf1df79c19c23d/macbook/",
    "iphone": "https://www.dns-shop.ru/catalog/recipe/4c7e3a7f7ef9a70e/apple-iphone/",
    "notebooks": "https://www.dns-shop.ru/catalog/17a892f816404e77/noutbuki/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def fetch_catalog(url: str) -> dict:
    """Загружает страницу каталога и извлекает данные"""
    print(f"[*] Загрузка: {url}")

    # Добавляем случайную задержку
    time.sleep(random.uniform(1, 3))

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.status
            print(f"    Status: {status}")

            # Читаем и декодируем ответ
            data = response.read()

            # Проверяем на gzip
            if response.headers.get('Content-Encoding') == 'gzip':
                data = gzip.decompress(data)

            html = data.decode('utf-8', errors='ignore')

            result = parse_html(html)
            result["url"] = url
            result["timestamp"] = datetime.now().isoformat()
            return result

    except urllib.error.HTTPError as e:
        print(f"    Status: {e.code}")
        if e.code == 401:
            print("[!] Qrator challenge - требуется браузер")
            return {"error": "qrator_challenge", "status": 401}
        if e.code == 403:
            print("[!] IP заблокирован")
            return {"error": "ip_blocked", "status": 403}
        return {"error": f"http_{e.code}", "status": e.code}

    except urllib.error.URLError as e:
        print(f"[!] URL error: {e}")
        return {"error": str(e)}

    except Exception as e:
        print(f"[!] Error: {e}")
        return {"error": str(e)}


def parse_html(html: str) -> dict:
    """Парсит HTML страницы"""
    result = {
        "catalog": {},
        "products": []
    }

    # Извлекаем JSON.stringify данные (JSON-LD вставленный через JS)
    match = re.search(r'JSON\.stringify\((\{[^}]+\}[^)]+)\)', html)
    if match:
        try:
            raw = match.group(1).replace('\\/', '/')
            data = json.loads(raw)
            result["catalog"] = {
                "name": data.get("name"),
                "low_price": data.get("offers", {}).get("lowPrice"),
                "high_price": data.get("offers", {}).get("highPrice"),
                "count": data.get("offers", {}).get("offerCount"),
                "rating": data.get("aggregateRating", {}).get("ratingValue"),
                "reviews": data.get("aggregateRating", {}).get("reviewCount"),
            }
        except json.JSONDecodeError:
            pass

    # Извлекаем товары
    product_pattern = re.compile(
        r'data-product="([^"]+)"[^>]*data-code="(\d+)".*?'
        r'catalog-product__name[^>]*href="([^"]+)"[^>]*><span>([^<]+)',
        re.DOTALL
    )

    for match in product_pattern.finditer(html):
        uuid, code, url, name = match.groups()
        short_name = name.split('[')[0].strip()

        specs = re.search(r'\[([^\]]+)\]', name)
        specs_str = specs.group(1) if specs else ''

        ram = re.search(r'RAM\s*(\d+)\s*ГБ', specs_str)
        ssd = re.search(r'SSD\s*(\d+)\s*ГБ', specs_str)

        result["products"].append({
            "code": code,
            "name": short_name,
            "ram": ram.group(1) if ram else None,
            "ssd": ssd.group(1) if ssd else None,
            "url": f"https://www.dns-shop.ru{url}"
        })

    return result


def main():
    catalog = sys.argv[1] if len(sys.argv) > 1 else "macbook-pro"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/dns_scraper"

    # Создаём директорию
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Получаем URL
    if catalog in CATALOGS:
        url = CATALOGS[catalog]
    elif catalog.startswith("http"):
        url = catalog
    else:
        print(f"[!] Unknown catalog: {catalog}")
        print(f"Available: {', '.join(CATALOGS.keys())}")
        sys.exit(1)

    print("=" * 50)
    print("  DNS-Shop API Scraper")
    print("=" * 50)

    # Загружаем данные
    data = fetch_catalog(url)

    # Сохраняем результат
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = Path(output_dir) / f"{catalog}_{timestamp}.json"

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Saved: {json_file}")

    # Выводим сводку
    if "catalog" in data and data["catalog"].get("name"):
        cat = data["catalog"]
        print(f"\n=== {cat['name']} ===")
        print(f"  Цены: {cat.get('low_price', 0):,} - {cat.get('high_price', 0):,} RUB")
        print(f"  Всего моделей: {cat.get('count', 'N/A')}")
        print(f"  На странице: {len(data.get('products', []))}")
        print(f"  Рейтинг: {cat.get('rating', 'N/A')}")
    elif "error" in data:
        print(f"\n[!] Error: {data['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
