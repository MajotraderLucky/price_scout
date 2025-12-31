#!/usr/bin/env python3
"""
Тест Playwright: парсинг Citilink
"""

from playwright.sync_api import sync_playwright
import re
import time
import random


def extract_prices(text: str) -> list:
    """Извлечь цены из текста"""
    prices = []
    matches = re.findall(r'(\d{1,3}(?:[\s\u00a0]?\d{3})+)', text)
    for match in matches:
        clean = match.replace(" ", "").replace("\u00a0", "")
        if clean.isdigit():
            price = int(clean)
            if 1000 < price < 500000:
                prices.append(price)
    return sorted(set(prices))


def search_citilink(query: str):
    """Поиск на Citilink"""

    print(f"\n{'='*60}")
    print(f"CITILINK: Поиск '{query}'")
    print(f"{'='*60}")

    search_url = f"https://www.citilink.ru/search/?text={query.replace(' ', '+')}"

    with sync_playwright() as p:
        print("\n[1] Запуск браузера...")
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        try:
            print(f"[2] Загрузка: {search_url[:60]}...")
            response = page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            print(f"    Status: {response.status}")

            # Ждём загрузку
            time.sleep(random.uniform(3, 5))

            # Скролл
            page.evaluate("window.scrollTo(0, 500)")
            time.sleep(1)

            # Проверка title
            title = page.title()
            print(f"[3] Title: {title[:50]}...")

            # Проверка на защиту
            content = page.content().lower()
            if "captcha" in content:
                print("[!] Обнаружена CAPTCHA")
                page.screenshot(path="debug_citilink_captcha.png")
            elif "blocked" in content or "access denied" in content:
                print("[!] Доступ заблокирован")

            # Поиск карточек товаров
            print("[4] Поиск товаров...")

            # Citilink селекторы
            card_selectors = [
                "[data-product-id]",
                ".product-card",
                ".ProductCardVertical",
                ".product_data__gtm-js",
            ]

            cards = []
            for selector in card_selectors:
                cards = page.query_selector_all(selector)
                if cards:
                    print(f"    Селектор: {selector}")
                    break

            print(f"    Найдено карточек: {len(cards)}")

            if cards:
                for i, card in enumerate(cards[:5], 1):
                    # Название
                    name = "N/A"
                    name_selectors = [
                        "[data-product-name]",
                        ".ProductCardVertical__name",
                        ".product__title",
                        "a.ProductCardVertical__title"
                    ]
                    for sel in name_selectors:
                        elem = card.query_selector(sel)
                        if elem:
                            name = elem.inner_text().strip()[:50]
                            break

                    # Цена
                    price = None
                    price_selectors = [
                        "[data-price]",
                        ".ProductCardVertical__price",
                        ".product__price",
                    ]
                    for sel in price_selectors:
                        elem = card.query_selector(sel)
                        if elem:
                            price_text = elem.inner_text()
                            prices = extract_prices(price_text)
                            if prices:
                                price = prices[0]
                                break

                    print(f"\n    [{i}] {name}...")
                    if price:
                        print(f"        Цена: {price:,} ₽".replace(",", " "))

            else:
                # Попробуем извлечь из JSON-LD
                print("[5] Поиск в JSON-LD...")
                scripts = page.query_selector_all('script[type="application/ld+json"]')
                print(f"    JSON-LD скриптов: {len(scripts)}")

                # Сохраняем отладочную информацию
                page.screenshot(path="debug_citilink.png")
                print("\n    Скриншот: debug_citilink.png")

                with open("debug_citilink.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print("    HTML: debug_citilink.html")

        except Exception as e:
            print(f"\n[ОШИБКА] {type(e).__name__}: {e}")
            page.screenshot(path="debug_error.png")

        finally:
            context.close()
            browser.close()

    print(f"\n{'='*60}")


if __name__ == "__main__":
    search_citilink("Samsung Galaxy S24")
