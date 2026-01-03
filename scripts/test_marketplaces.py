#!/usr/bin/env python3
"""
Тест парсинга маркетплейсов: Ozon, Yandex Market, Avito
"""

import re
import time
import random
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
]

MARKETPLACES = {
    "ozon": {
        "url": "https://www.ozon.ru/search/?text=MacBook+Pro+16",
        "price_selectors": [
            '[data-widget="searchResultsV2"] span[class*="price"]',
            '[data-widget="searchResultsV2"] [class*="tsHeadline"]',
        ],
    },
    "yandex_market": {
        "url": "https://market.yandex.ru/search?text=MacBook+Pro+16",
        "price_selectors": [
            '[data-auto="price-value"]',
            '[data-baobab-name="price"]',
        ],
    },
    "avito": {
        "url": "https://www.avito.ru/rossiya/noutbuki?q=MacBook+Pro+16",
        "price_selectors": [
            '[data-marker="item-price"]',
            '[itemprop="price"]',
        ],
    },
}


def random_delay(min_sec=2.0, max_sec=5.0):
    time.sleep(random.uniform(min_sec, max_sec))


def human_scroll(page):
    for _ in range(random.randint(2, 4)):
        page.mouse.wheel(0, random.randint(200, 500))
        time.sleep(random.uniform(0.3, 0.7))


def test_marketplace(name: str, config: dict) -> dict:
    """Тест маркетплейса"""
    print(f"\n{'='*60}")
    print(f"Testing: {name.upper()}")
    print(f"URL: {config['url']}")
    print("="*60)

    result = {
        "name": name,
        "url": config["url"],
        "status": "error",
        "prices": [],
        "http_status": None,
        "error": None,
        "captcha": False,
        "blocked": False,
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

            # Начальная задержка
            random_delay(3, 5)

            print(f"[*] Loading page...")
            response = page.goto(config["url"], wait_until="domcontentloaded", timeout=60000)
            result["http_status"] = response.status
            print(f"    HTTP: {response.status}")

            if response.status == 403:
                result["status"] = "blocked"
                result["blocked"] = True
                result["error"] = "403 Forbidden - IP blocked"
                print(f"    [X] BLOCKED: 403 Forbidden")
                return result

            if response.status == 429:
                result["status"] = "rate_limited"
                result["error"] = "429 Too Many Requests"
                print(f"    [X] Rate limited")
                return result

            if response.status != 200:
                result["status"] = "http_error"
                result["error"] = f"HTTP {response.status}"
                return result

            # Ожидание загрузки
            random_delay(5, 8)

            # Скролл для lazy loading
            human_scroll(page)
            random_delay(2, 3)

            # Получаем HTML
            html = page.content()
            current_url = page.url

            # Сохраняем HTML для анализа
            with open(f"/tmp/{name}_test.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"    Saved: /tmp/{name}_test.html ({len(html)} bytes)")

            # Проверка CAPTCHA
            captcha_indicators = [
                "captcha", "challenge", "robot", "verify", "blocked",
                "access denied", "security check"
            ]

            html_lower = html.lower()
            for indicator in captcha_indicators:
                if indicator in html_lower:
                    # Проверяем что это не просто упоминание в скрипте
                    if f'"{indicator}"' in html_lower or f"'{indicator}'" in html_lower:
                        continue
                    if "showcaptcha" in current_url.lower() or "challenge" in current_url.lower():
                        result["captcha"] = True
                        result["status"] = "captcha"
                        result["error"] = f"CAPTCHA detected ({indicator})"
                        print(f"    [X] CAPTCHA: {indicator}")
                        break

            # Проверка редиректа на captcha
            if "captcha" in current_url.lower() or "challenge" in current_url.lower():
                result["captcha"] = True
                result["status"] = "captcha"
                result["error"] = "Redirected to CAPTCHA page"
                print(f"    [X] CAPTCHA redirect: {current_url}")

            # Попытка извлечь цены
            if not result["captcha"]:
                # Пробуем селекторы
                for selector in config.get("price_selectors", []):
                    try:
                        elements = page.query_selector_all(selector)
                        if elements:
                            print(f"    Found {len(elements)} elements for: {selector}")
                            for el in elements[:5]:
                                text = el.text_content()
                                if text:
                                    # Извлекаем цифры
                                    nums = re.findall(r'\d[\d\s]*\d', text.replace("\u00a0", " "))
                                    for num in nums:
                                        price = int(num.replace(" ", ""))
                                        if 50000 < price < 500000:
                                            result["prices"].append(price)
                    except Exception as e:
                        print(f"    Selector error: {e}")

                # Fallback: regex
                if not result["prices"]:
                    # itemprop="price"
                    for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html):
                        price = int(match)
                        if 50000 < price < 500000:
                            result["prices"].append(price)

                    # data-price
                    for match in re.findall(r'data-price="(\d+)"', html):
                        price = int(match)
                        if 50000 < price < 500000:
                            result["prices"].append(price)

                    # price в JSON
                    for match in re.findall(r'"price":\s*(\d+)', html):
                        price = int(match)
                        if 50000 < price < 500000:
                            result["prices"].append(price)

                # Уникальные цены
                result["prices"] = sorted(set(result["prices"]))

                if result["prices"]:
                    result["status"] = "success"
                    print(f"    [+] Found {len(result['prices'])} prices")
                    print(f"    Prices: {result['prices'][:5]}")
                else:
                    result["status"] = "no_prices"
                    result["error"] = "No prices found in HTML"
                    print(f"    [!] No prices found")

            context.close()
            browser.close()

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        print(f"    [X] Error: {result['error']}")

    return result


def main():
    print("="*60)
    print("MARKETPLACE SCRAPING TEST")
    print("="*60)

    results = []
    for name, config in MARKETPLACES.items():
        result = test_marketplace(name, config)
        results.append(result)
        random_delay(5, 10)  # Пауза между маркетплейсами

    # Сводка
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for r in results:
        status_icon = {
            "success": "[+]",
            "captcha": "[C]",
            "blocked": "[X]",
            "no_prices": "[?]",
            "error": "[!]",
        }.get(r["status"], "[?]")

        if r["status"] == "success":
            print(f"{status_icon} {r['name']}: {len(r['prices'])} prices, min={min(r['prices']):,} RUB")
        else:
            print(f"{status_icon} {r['name']}: {r['status']} - {r['error']}")

    print("="*60)


if __name__ == "__main__":
    main()
