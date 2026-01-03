#!/usr/bin/env python3
"""
Citilink Scraper via Playwright
Использует stealth mode и ожидание загрузки элементов
"""

import sys
import json
import time
import random
import re
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


CATALOGS = {
    "macbook-pro": "https://www.citilink.ru/search/?text=MacBook+Pro+16",
    "macbook-air": "https://www.citilink.ru/search/?text=MacBook+Air",
    "macbook": "https://www.citilink.ru/search/?text=Apple+MacBook",
    "iphone": "https://www.citilink.ru/search/?text=iPhone",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
]


def extract_specs(name: str) -> dict:
    """Извлечение характеристик из названия товара"""
    if not name:
        return {"cpu": None, "ram": None, "ssd": None, "screen": None, "article": None}

    # Screen: "16.2", "16", "14.2"
    screen_match = re.search(r'(\d{2})(?:\.\d)?["\s]', name)
    screen = screen_match.group(1) if screen_match else None

    # CPU: "M1 Pro", "M4 Max", "M5"
    cpu_match = re.search(r'(?:Apple\s+)?(M\d+(?:\s+(?:Pro|Max|Ultra))?)', name, re.I)
    cpu = cpu_match.group(1).strip() if cpu_match else None

    # RAM: "32 ГБ", "32GB"
    ram_match = re.search(r'(?:RAM|ОЗУ|память)?\s*(\d+)\s*(?:ГБ|GB)', name, re.I)
    if not ram_match:
        all_gb = re.findall(r'(\d+)\s*(?:ГБ|GB)', name, re.I)
        ram = int(all_gb[0]) if all_gb else None
    else:
        ram = int(ram_match.group(1))

    # SSD: "512 ГБ", "1TB"
    ssd_match = re.search(r'(?:SSD|накопитель)\s*(\d+)\s*(?:ТБ|TB)', name, re.I)
    if ssd_match:
        ssd = int(ssd_match.group(1)) * 1000
    else:
        ssd_match = re.search(r'(?:SSD|накопитель)\s*(\d+)\s*(?:ГБ|GB)', name, re.I)
        if not ssd_match:
            all_tb = re.findall(r'(\d+)\s*(?:ТБ|TB)', name, re.I)
            if all_tb:
                ssd = int(all_tb[0]) * 1000
            else:
                all_gb = re.findall(r'(\d+)\s*(?:ГБ|GB)', name, re.I)
                ssd = int(all_gb[1]) if len(all_gb) >= 2 else None
        else:
            ssd = int(ssd_match.group(1))

    # Article: "Z14V0008D"
    article_match = re.search(r'\b([A-Z]\d{2}[A-Z0-9]{5,})\b', name)
    article = article_match.group(1) if article_match else None

    return {
        "cpu": cpu,
        "ram": ram,
        "ssd": ssd,
        "screen": screen,
        "article": article
    }


def random_delay(min_sec=1.0, max_sec=3.0):
    time.sleep(random.uniform(min_sec, max_sec))


def human_scroll(page):
    """Имитация человеческой прокрутки"""
    for _ in range(random.randint(2, 4)):
        page.mouse.wheel(0, random.randint(200, 400))
        time.sleep(random.uniform(0.3, 0.7))


def scrape_citilink(url: str, output_dir: str) -> dict:
    """Скрейпинг Citilink с ожиданием загрузки"""

    result = {
        "source": "citilink",
        "url": url,
        "products": [],
        "timestamp": datetime.now().isoformat(),
        "status": "error"
    }

    try:
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
                user_agent=random.choice(USER_AGENTS),
                locale="ru-RU",
                timezone_id="Europe/Moscow",
            )

            page = context.new_page()

            # Stealth patches
            stealth = Stealth(
                navigator_languages_override=("ru-RU", "ru"),
                navigator_platform_override="Win32",
            )
            stealth.apply_stealth_sync(page)

            print(f"[*] Загрузка: {url}")

            # Начальная задержка
            random_delay(3, 5)

            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"    HTTP: {response.status}")

            if response.status == 429:
                result["status"] = "rate_limited"
                result["error"] = "429 Too Many Requests"
                return result

            if response.status != 200:
                result["status"] = "http_error"
                result["error"] = f"HTTP {response.status}"
                return result

            # Ждём загрузки контента
            random_delay(5, 8)

            # Прокрутка для загрузки lazy content
            human_scroll(page)
            random_delay(2, 3)

            # Пробуем дождаться карточек товаров
            try:
                page.wait_for_selector('[data-meta-price]', timeout=15000)
                print("    [+] Найдены карточки товаров")
            except Exception:
                print("    [!] Карточки товаров не найдены, пробуем альтернативы...")

            # Получаем HTML
            html = page.content()

            # Сохраняем HTML
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = Path(output_dir) / f"citilink_{timestamp}.html"
            html_file.write_text(html, encoding="utf-8")
            print(f"    HTML: {html_file} ({len(html)} bytes)")

            # Парсим __NEXT_DATA__
            import re
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
                            for item in value["products"]:
                                name = item.get("shortName") or item.get("name", "")
                                product = {
                                    "id": item.get("id"),
                                    "name": name,
                                    "price": item.get("price", {}).get("price", 0),
                                    "old_price": item.get("price", {}).get("old"),
                                    "available": item.get("isAvailable", False),
                                    "rating": item.get("rating", {}).get("value"),
                                    "reviews": item.get("rating", {}).get("reviewsCount"),
                                    "url": f"https://www.citilink.ru/product/{item.get('slug', '')}/" if item.get("slug") else None,
                                    "specs": extract_specs(name)
                                }
                                result["products"].append(product)
                except json.JSONDecodeError as e:
                    print(f"    [!] JSON parse error: {e}")

            # Fallback: извлекаем через JavaScript evaluate
            if not result["products"]:
                try:
                    prices = page.evaluate("""
                        () => {
                            const items = [];
                            document.querySelectorAll('[data-meta-price]').forEach(el => {
                                const price = el.getAttribute('data-meta-price');
                                const name = el.getAttribute('data-meta-name') ||
                                             el.closest('[data-product-id]')?.querySelector('.product-title')?.textContent ||
                                             'Unknown';
                                if (price) {
                                    items.push({name: name.trim(), price: parseInt(price)});
                                }
                            });
                            return items;
                        }
                    """)

                    for item in prices:
                        if item.get("price", 0) > 50000:  # Фильтр MacBook цен
                            name = item["name"]
                            result["products"].append({
                                "name": name,
                                "price": item["price"],
                                "available": True,
                                "specs": extract_specs(name)
                            })
                except Exception as e:
                    print(f"    [!] JS evaluate error: {e}")

            # Финальный fallback: regex
            if not result["products"]:
                import re
                prices = re.findall(r'data-meta-price="(\d+)"', html)
                for price in prices:
                    p = int(price)
                    if 80000 < p < 400000:  # Диапазон MacBook
                        result["products"].append({
                            "price": p,
                            "available": True
                        })

            if result["products"]:
                result["status"] = "success"
                prices = [p["price"] for p in result["products"] if p.get("price")]
                if prices:
                    print(f"    Найдено: {len(result['products'])} товаров")
                    print(f"    Цены: {min(prices):,} - {max(prices):,} RUB")
            else:
                result["status"] = "no_products"
                print("    [!] Товары не найдены")

            context.close()
            browser.close()

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        print(f"    [!] Error: {result['error']}")

    return result


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "macbook-pro"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/citilink_scraper"

    # Получаем URL
    if query in CATALOGS:
        url = CATALOGS[query]
    elif query.startswith("http"):
        url = query
    else:
        print(f"[!] Unknown query: {query}")
        print(f"Available: {', '.join(CATALOGS.keys())}")
        sys.exit(1)

    print("=" * 50)
    print("  Citilink Playwright Scraper")
    print("=" * 50)

    result = scrape_citilink(url, output_dir)

    # Сохраняем JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = Path(output_dir) / f"citilink_{timestamp}.json"
    json_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[+] JSON: {json_file}")

    print("\n" + "=" * 50)
    if result["status"] == "success":
        print("  УСПЕХ!")
    else:
        print(f"  Статус: {result['status']}")
    print("=" * 50)

    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
