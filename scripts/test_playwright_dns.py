#!/usr/bin/env python3
"""
Тест Playwright: парсинг DNS-Shop

Использует headless браузер для обхода JS-защиты
"""

from playwright.sync_api import sync_playwright
import re
import time
import random


def random_delay(min_sec: float = 1, max_sec: float = 3):
    """Случайная задержка для имитации человека"""
    time.sleep(random.uniform(min_sec, max_sec))


def extract_prices(text: str) -> list:
    """Извлечь цены из текста"""
    patterns = [
        r'(\d{1,3}(?:\s?\d{3})*)\s*(?:₽|руб)',
        r'(\d{1,3}(?:[\s\u00a0]?\d{3})+)',
    ]

    prices = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            clean = match.replace(" ", "").replace("\u00a0", "")
            if clean.isdigit():
                price = int(clean)
                if 1000 < price < 500000:
                    prices.append(price)

    return sorted(set(prices))


def scrape_dns_product(url: str):
    """Спарсить страницу товара DNS"""

    print(f"\n{'='*60}")
    print("PLAYWRIGHT: Парсинг DNS-Shop")
    print(f"{'='*60}")
    print(f"\n[URL] {url}")

    with sync_playwright() as p:
        # Запуск браузера
        print("\n[1] Запуск браузера...")
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        # Создание контекста с реалистичными настройками
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        # Перехват запросов для отладки
        blocked_resources = ["image", "font", "media"]
        page.route("**/*", lambda route: route.abort()
                   if route.request.resource_type in blocked_resources
                   else route.continue_())

        try:
            # Загрузка страницы
            print("[2] Загрузка страницы...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)

            print(f"    Status: {response.status}")

            if response.status != 200:
                print(f"[!] Неуспешный статус: {response.status}")
                # Попробуем подождать и проверить контент

            # Ждём загрузку основного контента
            random_delay(2, 4)

            # Проверка на CAPTCHA или блокировку
            print("[3] Проверка на защиту...")
            page_content = page.content().lower()

            if "captcha" in page_content or "recaptcha" in page_content:
                print("    [!] Обнаружена CAPTCHA")
                # Скриншот для отладки
                page.screenshot(path="debug_captcha.png")
                print("    Скриншот сохранён: debug_captcha.png")
            elif "blocked" in page_content or "access denied" in page_content:
                print("    [!] Доступ заблокирован")
            else:
                print("    [+] Защита не обнаружена")

            # Скролл страницы для загрузки lazy content
            print("[4] Скролл страницы...")
            page.evaluate("window.scrollTo(0, 500)")
            random_delay(1, 2)

            # Извлечение данных
            print("[5] Извлечение данных...")

            # Title
            title = page.title()
            print(f"    Title: {title[:60]}...")

            # Попытка найти название товара
            product_name = None
            selectors = [
                "h1.product-card-top__title",
                "h1[data-product-name]",
                ".product-card-description__title",
                "h1",
            ]
            for selector in selectors:
                elem = page.query_selector(selector)
                if elem:
                    product_name = elem.inner_text().strip()
                    break

            if product_name:
                print(f"    Товар: {product_name[:50]}...")

            # Попытка найти цену
            price = None
            price_selectors = [
                ".product-buy__price",
                ".product-card-price__current",
                "[data-product-price]",
                ".price__current",
                ".product-price",
            ]
            for selector in price_selectors:
                elem = page.query_selector(selector)
                if elem:
                    price_text = elem.inner_text()
                    prices = extract_prices(price_text)
                    if prices:
                        price = prices[0]
                        break

            if price:
                print(f"    Цена: {price:,} ₽".replace(",", " "))
            else:
                # Попробуем извлечь цены из всей страницы
                full_text = page.inner_text("body")
                all_prices = extract_prices(full_text)
                if all_prices:
                    print(f"    Найденные цены на странице: {all_prices[:5]}")

            # Проверка наличия
            availability = None
            avail_selectors = [
                ".product-buy__btn",
                ".order-avail-wrap",
                "[data-product-available]",
            ]
            for selector in avail_selectors:
                elem = page.query_selector(selector)
                if elem:
                    availability = elem.inner_text().strip()[:30]
                    break

            if availability:
                print(f"    Наличие: {availability}")

            # Сохранение скриншота
            screenshot_path = "debug_dns_page.png"
            page.screenshot(path=screenshot_path, full_page=False)
            print(f"\n[6] Скриншот сохранён: {screenshot_path}")

            # Сохранение HTML для анализа
            html_path = "debug_dns_page.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"    HTML сохранён: {html_path}")

        except Exception as e:
            print(f"\n[ОШИБКА] {type(e).__name__}: {e}")
            page.screenshot(path="debug_error.png")

        finally:
            context.close()
            browser.close()
            print("\n[7] Браузер закрыт")

    print(f"\n{'='*60}")
    print("ТЕСТ ЗАВЕРШЁН")
    print(f"{'='*60}")


def search_and_scrape(query: str):
    """Поиск на DNS и парсинг первого результата"""

    print(f"\n{'='*60}")
    print(f"ПОИСК НА DNS: {query}")
    print(f"{'='*60}")

    search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
        )

        page = context.new_page()

        # Блокируем тяжёлые ресурсы
        page.route("**/*", lambda route: route.abort()
                   if route.request.resource_type in ["image", "font", "media"]
                   else route.continue_())

        try:
            print(f"\n[1] Загрузка поиска: {search_url[:60]}...")
            response = page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            print(f"    Status: {response.status}")

            random_delay(3, 5)

            # Ищем карточки товаров
            print("\n[2] Поиск карточек товаров...")

            cards = page.query_selector_all(".catalog-product")
            print(f"    Найдено карточек: {len(cards)}")

            if cards:
                for i, card in enumerate(cards[:5], 1):
                    # Название
                    name_elem = card.query_selector(".catalog-product__name")
                    name = name_elem.inner_text().strip()[:50] if name_elem else "N/A"

                    # Цена
                    price_elem = card.query_selector(".product-buy__price")
                    price_text = price_elem.inner_text() if price_elem else ""
                    prices = extract_prices(price_text)
                    price = prices[0] if prices else None

                    # Ссылка
                    link_elem = card.query_selector("a")
                    link = link_elem.get_attribute("href") if link_elem else None

                    print(f"\n    [{i}] {name}...")
                    if price:
                        print(f"        Цена: {price:,} ₽".replace(",", " "))
                    if link:
                        print(f"        URL: {link[:50]}...")
            else:
                # Проверим на CAPTCHA
                if "captcha" in page.content().lower():
                    print("    [!] Обнаружена CAPTCHA")
                    page.screenshot(path="debug_dns_captcha.png")
                    print("    Скриншот: debug_dns_captcha.png")
                else:
                    print("    [!] Карточки не найдены")
                    page.screenshot(path="debug_dns_search.png")
                    print("    Скриншот: debug_dns_search.png")

        except Exception as e:
            print(f"\n[ОШИБКА] {e}")
            page.screenshot(path="debug_error.png")

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    # Тест 1: Поиск на DNS
    search_and_scrape("Samsung Galaxy S24")
