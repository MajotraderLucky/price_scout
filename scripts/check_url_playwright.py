#!/usr/bin/env python3
"""
Проверка URL через Playwright (с рендерингом JS)
"""

import sys
import re
import json
import time
import random
from playwright.sync_api import sync_playwright

# URL для теста
YANDEX_MARKET_URL = "https://market.yandex.ru/product--noutbuk-apple-macbook-pro-16-2021-m1-pro-10c-cpu-16c-gpu-32gb-512gb-ssd-space-gray-z14v0008d-rus/1495790507"


def extract_prices(text: str) -> list:
    """Извлечь цены (100K-500K для MacBook)"""
    prices = []
    patterns = [
        r'(\d{3}[\s\u00a0]?\d{3})\s*(?:₽|руб)',
        r'"price"[:\s]*(\d+)',
        r'"value"[:\s]*"?(\d+)"?',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text):
            clean = str(match).replace(" ", "").replace("\u00a0", "")
            if clean.isdigit():
                price = int(clean)
                if 100000 < price < 500000:
                    prices.append(price)

    return sorted(set(prices))


def check_with_playwright(url: str):
    """Проверить URL через Playwright"""

    print(f"\n{'='*70}")
    print("PLAYWRIGHT: Проверка URL")
    print(f"{'='*70}")
    print(f"URL: {url[:60]}...")

    with sync_playwright() as p:
        print("\n[1] Запуск браузера...")
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        try:
            print("[2] Загрузка страницы...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"    Status: {response.status}")
            print(f"    URL: {page.url[:60]}...")

            # Ждём загрузку
            time.sleep(random.uniform(3, 5))

            # Скролл
            page.evaluate("window.scrollTo(0, 300)")
            time.sleep(1)

            # Проверка title
            title = page.title()
            print(f"\n[3] Title: {title[:50]}...")

            # Проверка на CAPTCHA
            print("\n[4] Проверка на защиту...")
            content = page.content().lower()

            if "captcha" in content or "showcaptcha" in page.url:
                print("    [!] CAPTCHA обнаружена")

                # Скриншот
                page.screenshot(path="debug_yandex_captcha.png")
                print("    Скриншот: debug_yandex_captcha.png")

                return {"status": "captcha", "prices": []}

            elif "robot" in content or "blocked" in content:
                print("    [!] Заблокировано")
                return {"status": "blocked", "prices": []}

            else:
                print("    [+] Защита не обнаружена")

            # Поиск цены на странице
            print("\n[5] Поиск цены...")

            # Попытка найти элемент цены
            price_selectors = [
                '[data-auto="price-value"]',
                '[data-zone-name="price"]',
                '.price-value',
                '[itemprop="price"]',
                '.n-price-old__block',
            ]

            price_found = None
            for selector in price_selectors:
                elem = page.query_selector(selector)
                if elem:
                    price_text = elem.inner_text()
                    print(f"    Selector: {selector}")
                    print(f"    Text: {price_text}")
                    prices = extract_prices(price_text)
                    if prices:
                        price_found = prices[0]
                        break

            if price_found:
                print(f"    [+] Цена найдена: {price_found:,} ₽".replace(",", " "))
            else:
                # Попробуем извлечь из всего HTML
                html = page.content()
                all_prices = extract_prices(html)
                if all_prices:
                    print(f"    Цены в HTML: {all_prices[:5]}")
                else:
                    print("    Цены не найдены")

            # Сохранение
            page.screenshot(path="debug_yandex_page.png")
            with open("debug_yandex_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())

            print("\n[6] Файлы сохранены:")
            print("    - debug_yandex_page.png")
            print("    - debug_yandex_page.html")

            return {
                "status": "ok" if price_found else "no_price",
                "prices": [price_found] if price_found else all_prices if 'all_prices' in dir() else [],
            }

        except Exception as e:
            print(f"\n[!] Ошибка: {e}")
            page.screenshot(path="debug_error.png")
            return {"status": "error", "prices": []}

        finally:
            context.close()
            browser.close()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else YANDEX_MARKET_URL

    result = check_with_playwright(url)

    print(f"\n{'='*70}")
    print("РЕЗУЛЬТАТ")
    print(f"{'='*70}")
    print(f"Статус: {result['status']}")
    if result['prices']:
        print(f"Цены: {result['prices']}")


if __name__ == "__main__":
    main()
