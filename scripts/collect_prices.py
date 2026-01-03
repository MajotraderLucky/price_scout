#!/usr/bin/env python3
"""
Price Scout - Unified Price Collector

Сбор цен со всех доступных магазинов для указанного товара.

Использование:
    python collect_prices.py Z14V0008D
    python collect_prices.py --search "MacBook Pro 16"
"""

import re
import sys
import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, quote_plus

from playwright.sync_api import sync_playwright, Page
from playwright_stealth import Stealth


# === Конфигурация ===

STORES = {
    "i-ray": {
        "search_url": "https://i-ray.ru/search?q={query}",
        "method": "direct",
    },
    "regard": {
        "search_url": "https://www.regard.ru/catalog?search={query}",
        "method": "stealth",
    },
    "kns": {
        "search_url": "https://www.kns.ru/product/noutbuk-apple-macbook-pro-16-2021-{query}/",
        "method": "direct",
        "url_type": "product",
        "lowercase": True,
    },
    "nix": {
        "search_url": "https://www.nix.ru/autocatalog/apple_notebook/{query}-Noutbuk-Apple-MacBook-Pro-162-Apple-M1-Pro-10-core-32GB-512GB-SSD-Mac-OS-{query}-seryj-kosmos_574636.html",
        "method": "direct",
        "url_type": "product",
    },
    # Citilink needs full product name, not just article
    "citilink": {
        "search_url": "https://www.citilink.ru/search/?text=MacBook+Pro+16+{query}",
        "method": "stealth",
        "parser": "nextjs",
        "delay": 5,
    },
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]

# Диапазон цен для MacBook (фильтрация мусора)
MIN_PRICE = 80000
MAX_PRICE = 500000


# === Dataclasses ===

@dataclass
class PriceResult:
    """Результат парсинга цены"""
    store: str
    price: Optional[int]
    available: Optional[bool]
    product_name: str
    url: str
    status: str  # OK, CAPTCHA, Blocked, Error, No Price
    timestamp: str


# === Утилиты ===

def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    time.sleep(random.uniform(min_sec, max_sec))


def human_scroll(page: Page):
    """Имитация скролла"""
    for _ in range(random.randint(2, 3)):
        page.mouse.wheel(0, random.randint(100, 300))
        time.sleep(random.uniform(0.2, 0.5))


def human_mouse_move(page: Page):
    """Случайные движения мыши"""
    viewport = page.viewport_size
    if not viewport:
        return
    for _ in range(random.randint(2, 4)):
        x = random.randint(100, viewport['width'] - 100)
        y = random.randint(100, viewport['height'] - 100)
        page.mouse.move(x, y, steps=random.randint(5, 10))
        time.sleep(random.uniform(0.1, 0.2))


# === Парсинг цен ===

def extract_price(html: str) -> Optional[int]:
    """Извлечь цену из HTML (несколько методов)"""

    # Приоритет 1: Schema.org itemprop="price"
    match = re.search(r'itemprop="price"\s+content="(\d+)"', html)
    if match:
        price = int(match.group(1))
        if MIN_PRICE < price < MAX_PRICE:
            return price

    # Приоритет 2: data-meta-price (Citilink)
    match = re.search(r'data-meta-price="(\d+)"', html)
    if match:
        price = int(match.group(1))
        if MIN_PRICE < price < MAX_PRICE:
            return price

    # Приоритет 3: JSON-LD "price"
    for match in re.findall(r'"price"[:\s]*(\d+)', html):
        price = int(match)
        if MIN_PRICE < price < MAX_PRICE:
            return price

    # Приоритет 4: Текстовые цены (XXX XXX ₽)
    for match in re.findall(r'(\d{2,3}[\s\u00a0]?\d{3})[\s\u00a0]*(?:₽|руб|RUB)', html):
        clean = match.replace(" ", "").replace("\u00a0", "")
        if clean.isdigit():
            price = int(clean)
            if MIN_PRICE < price < MAX_PRICE:
                return price

    return None


def extract_availability(html: str) -> Optional[bool]:
    """Извлечь информацию о наличии"""
    html_lower = html.lower()

    if 'instock' in html_lower or 'in_stock' in html_lower or '"availability":"instock"' in html_lower:
        return True
    elif 'outofstock' in html_lower or 'out_of_stock' in html_lower or 'soldout' in html_lower:
        return False
    elif 'isavailable":true' in html_lower or '"available":true' in html_lower:
        return True
    elif 'isavailable":false' in html_lower or '"available":false' in html_lower:
        return False

    # Текстовый поиск
    if 'в наличии' in html_lower or 'есть в наличии' in html_lower:
        return True
    elif 'нет в наличии' in html_lower or 'под заказ' in html_lower:
        return False

    return None


def extract_product_name(html: str, query: str) -> str:
    """Извлечь название товара"""

    # Schema.org
    match = re.search(r'itemprop="name"[^>]*>([^<]+)<', html)
    if match:
        return match.group(1).strip()[:100]

    # og:title
    match = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if match:
        return match.group(1).strip()[:100]

    # title tag
    match = re.search(r'<title>([^<]+)</title>', html)
    if match:
        title = match.group(1).strip()
        if query.lower() in title.lower():
            return title[:100]

    return query


def detect_captcha(html: str, url: str) -> bool:
    """Проверка на CAPTCHA"""
    html_lower = html.lower()
    url_lower = url.lower()

    indicators = [
        "captcha" in url_lower,
        "showcaptcha" in url_lower,
        "recaptcha" in html_lower,
        "hcaptcha" in html_lower,
        "cf-browser-verification" in html_lower,
        "smartcaptcha" in html_lower,
    ]

    return any(indicators)


# === Специализированные парсеры ===

def parse_citilink_nextjs(html: str, query: str) -> List[Dict]:
    """Парсинг Citilink через Next.js JSON"""
    products = []

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
                    for item in value["products"][:5]:
                        products.append({
                            "name": item.get("name", "")[:100],
                            "price": item.get("price", {}).get("price", 0),
                            "available": item.get("isAvailable", False),
                            "url": f"https://www.citilink.ru/product/{item.get('slug', '')}/"
                        })
                    break
        except json.JSONDecodeError:
            pass

    return products


# === Основной парсер ===

def scrape_store(store_name: str, query: str, config: dict) -> PriceResult:
    """Парсинг одного магазина"""

    # Handle URL formatting
    url_type = config.get("url_type", "search")
    use_lowercase = config.get("lowercase", False)
    query_formatted = query.lower() if use_lowercase else query

    if url_type == "product":
        # Direct product URL
        search_url = config["search_url"].format(query=query_formatted)
    else:
        search_url = config["search_url"].format(query=quote_plus(query))

    method = config.get("method", "direct")
    parser = config.get("parser", "generic")
    extra_delay = config.get("delay", 0)

    print(f"\n[{store_name}]")
    print(f"  URL: {search_url[:60]}...")

    result = PriceResult(
        store=store_name,
        price=None,
        available=None,
        product_name="",
        url=search_url,
        status="Error",
        timestamp=datetime.now().isoformat()
    )

    with sync_playwright() as p:
        # Настройка браузера
        browser_args = ["--no-sandbox", "--disable-setuid-sandbox"]

        if method == "stealth":
            browser_args.extend([
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ])

        browser = p.chromium.launch(headless=True, args=browser_args)

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice(USER_AGENTS),
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        # Применяем stealth если нужно
        if method == "stealth":
            stealth = Stealth(
                navigator_languages_override=("ru-RU", "ru"),
                navigator_platform_override="Win32",
            )
            stealth.apply_stealth_sync(page)

        try:
            # Extra delay for stores with rate limiting
            if extra_delay > 0:
                print(f"  [*] Waiting {extra_delay}s (rate limit protection)...")
                time.sleep(extra_delay)

            response = page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            print(f"  HTTP: {response.status}")

            if response.status != 200:
                result.status = f"HTTP {response.status}"
                return result

            # Ждём загрузки
            random_delay(2, 4)

            # Имитация человека для stealth
            if method == "stealth":
                human_mouse_move(page)
                human_scroll(page)
                random_delay(1, 2)

            html = page.content()
            current_url = page.url

            # Проверка CAPTCHA
            if detect_captcha(html, current_url):
                print("  [X] CAPTCHA detected!")
                result.status = "CAPTCHA"
                return result

            # Парсинг
            if parser == "nextjs":
                # Citilink: специальный парсер
                products = parse_citilink_nextjs(html, query)
                if products:
                    # Берём минимальную цену
                    products.sort(key=lambda x: x["price"])
                    best = products[0]
                    result.price = best["price"]
                    result.available = best["available"]
                    result.product_name = best["name"]
                    result.url = best["url"]
                    result.status = "OK"
                    print(f"  [+] Найдено {len(products)} товаров")
                else:
                    # Fallback: data-meta-price
                    prices = re.findall(r'data-meta-price="(\d+)"', html)
                    if prices:
                        result.price = int(prices[0])
                        result.available = True
                        result.status = "OK"
                        print(f"  [+] Цена (fallback): {result.price:,} RUB".replace(",", " "))
            else:
                # Общий парсер
                result.price = extract_price(html)
                result.available = extract_availability(html)
                result.product_name = extract_product_name(html, query)

            if result.price:
                result.status = "OK"
                print(f"  [+] Цена: {result.price:,} RUB".replace(",", " "))
                if result.available is not None:
                    status = "В наличии" if result.available else "Нет в наличии"
                    print(f"  [+] Наличие: {status}")
            else:
                result.status = "No Price"
                print("  [-] Цена не найдена")

        except Exception as e:
            print(f"  [!] Ошибка: {type(e).__name__}: {e}")
            result.status = f"Error: {type(e).__name__}"

        finally:
            context.close()
            browser.close()

    return result


def collect_all_prices(query: str) -> List[PriceResult]:
    """Собрать цены со всех магазинов"""

    results = []

    for store_name, config in STORES.items():
        result = scrape_store(store_name, query, config)
        results.append(result)

        # Пауза между магазинами
        random_delay(2, 4)

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python collect_prices.py <article>")
        print("       python collect_prices.py --search <query>")
        print()
        print("Examples:")
        print("  python collect_prices.py Z14V0008D")
        print('  python collect_prices.py --search "MacBook Pro 16"')
        sys.exit(1)

    if sys.argv[1] == "--search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
    else:
        query = sys.argv[1]

    print("=" * 70)
    print("PRICE SCOUT - Unified Price Collector")
    print("=" * 70)
    print(f"Запрос: {query}")
    print(f"Магазинов: {len(STORES)}")
    print("=" * 70)

    # Сбор цен
    results = collect_all_prices(query)

    # Результаты
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 70)

    ok_results = [r for r in results if r.status == "OK" and r.price]

    if ok_results:
        ok_results.sort(key=lambda x: x.price)

        print(f"\n[+] Найдено цен: {len(ok_results)}/{len(results)}")
        print("-" * 70)

        for i, r in enumerate(ok_results, 1):
            avail = "[+]" if r.available else "[-]" if r.available is False else "[?]"
            print(f"{i}. {r.store}: {r.price:,} RUB {avail}".replace(",", " "))
            if r.product_name:
                print(f"   {r.product_name[:60]}")

        print("-" * 70)
        print(f"Минимальная цена: {ok_results[0].price:,} RUB ({ok_results[0].store})".replace(",", " "))
        print(f"Максимальная цена: {ok_results[-1].price:,} RUB ({ok_results[-1].store})".replace(",", " "))
    else:
        print("\n[X] Цены не найдены")

    # Проблемные магазины
    failed = [r for r in results if r.status != "OK"]
    if failed:
        print(f"\n[!] Проблемы: {len(failed)}")
        for r in failed:
            print(f"    {r.store}: {r.status}")

    # Сохранение JSON
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"prices_{timestamp}.json"

    output_data = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "results": [asdict(r) for r in results],
        "summary": {
            "total_stores": len(results),
            "prices_found": len(ok_results),
            "min_price": ok_results[0].price if ok_results else None,
            "max_price": ok_results[-1].price if ok_results else None,
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Сохранено: {output_file}")


if __name__ == "__main__":
    main()
