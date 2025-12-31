#!/usr/bin/env python3
"""
Stealth-парсер для обхода CAPTCHA и bot-detection

Методы:
1. Playwright Stealth - маскировка отпечатков браузера
2. Human-like поведение - случайные задержки, движения мыши
3. Правильные заголовки и cookies
4. Ротация User-Agent
"""

import re
import time
import random
from typing import Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, BrowserContext
from playwright_stealth import Stealth


@dataclass
class ScrapeResult:
    """Результат парсинга"""
    domain: str
    url: str
    status: str  # OK, CAPTCHA, Blocked, Error
    price: Optional[int]
    title: str
    captcha_detected: bool


# User-Agent ротация (реальные браузеры)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """Случайная задержка для имитации человека"""
    time.sleep(random.uniform(min_sec, max_sec))


def human_scroll(page: Page):
    """Имитация человеческого скролла"""
    # Скроллим вниз случайными шагами
    for _ in range(random.randint(2, 4)):
        scroll_y = random.randint(100, 300)
        page.mouse.wheel(0, scroll_y)
        time.sleep(random.uniform(0.3, 0.8))

    # Иногда скроллим обратно
    if random.random() > 0.5:
        page.mouse.wheel(0, -random.randint(50, 150))
        time.sleep(random.uniform(0.2, 0.5))


def human_mouse_move(page: Page):
    """Случайные движения мыши"""
    viewport = page.viewport_size
    if not viewport:
        return

    # Несколько случайных движений
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, viewport['width'] - 100)
        y = random.randint(100, viewport['height'] - 100)

        # Двигаем мышь с небольшими шагами
        page.mouse.move(x, y, steps=random.randint(5, 15))
        time.sleep(random.uniform(0.1, 0.3))


def detect_captcha(page: Page) -> dict:
    """Определить тип CAPTCHA на странице"""
    html = page.content().lower()
    url = page.url.lower()

    result = {
        "detected": False,
        "type": "none",
        "site_key": None,
    }

    # Проверка URL редиректа на CAPTCHA
    if "captcha" in url or "showcaptcha" in url:
        result["detected"] = True
        result["type"] = "redirect"
        return result

    # reCAPTCHA
    if "recaptcha" in html or "grecaptcha" in html:
        result["detected"] = True
        result["type"] = "reCAPTCHA"

        # Ищем site_key
        match = re.search(r'data-sitekey=["\']([^"\']+)["\']', page.content())
        if match:
            result["site_key"] = match.group(1)
        return result

    # hCaptcha
    if "hcaptcha" in html:
        result["detected"] = True
        result["type"] = "hCaptcha"
        return result

    # CloudFlare
    if "cf-browser-verification" in html or "cloudflare" in html:
        result["detected"] = True
        result["type"] = "CloudFlare"
        return result

    # Яндекс SmartCaptcha
    if "smartcaptcha" in html:
        result["detected"] = True
        result["type"] = "SmartCaptcha"
        return result

    # Общая проверка слова captcha
    if "captcha" in html:
        result["detected"] = True
        result["type"] = "unknown"

    return result


def extract_price(html: str, min_price: int = 100000, max_price: int = 400000) -> Optional[int]:
    """Извлечь цену из HTML"""

    # Schema.org
    match = re.search(r'itemprop="price"\s+content="(\d+)"', html)
    if match:
        price = int(match.group(1))
        if min_price < price < max_price:
            return price

    # JSON
    for match in re.findall(r'"price"[:\s]*(\d+)', html):
        price = int(match)
        if min_price < price < max_price:
            return price

    # Текст
    for match in re.findall(r'(\d{3}[\s\u00a0]?\d{3})[\s\u00a0]*(?:₽|руб)', html):
        clean = match.replace(" ", "").replace("\u00a0", "")
        if clean.isdigit():
            price = int(clean)
            if min_price < price < max_price:
                return price

    return None


def create_stealth_context(playwright) -> tuple:
    """Создать стелс-браузер"""

    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
        ]
    )

    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=random.choice(USER_AGENTS),
        locale="ru-RU",
        timezone_id="Europe/Moscow",
        # Дополнительные параметры для реалистичности
        color_scheme="light",
        has_touch=False,
        is_mobile=False,
        java_script_enabled=True,
    )

    return browser, context


def scrape_with_stealth(url: str, verbose: bool = True) -> ScrapeResult:
    """Парсинг с использованием stealth-техник"""

    domain = urlparse(url).netloc.replace('www.', '')

    if verbose:
        print(f"\n[{domain}]")
        print(f"  URL: {url[:60]}...")

    with sync_playwright() as p:
        browser, context = create_stealth_context(p)
        page = context.new_page()

        # Применяем stealth патчи
        stealth = Stealth(
            navigator_languages_override=("ru-RU", "ru"),
            navigator_platform_override="Win32",
        )
        stealth.apply_stealth_sync(page)

        try:
            # Загрузка с имитацией человека
            if verbose:
                print("  [1] Загрузка...")

            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if verbose:
                print(f"  [2] HTTP: {response.status}")

            # Ждём как человек
            random_delay(2, 4)

            # Имитируем поведение
            human_mouse_move(page)
            human_scroll(page)
            random_delay(1, 2)

            # Проверяем CAPTCHA
            captcha = detect_captcha(page)

            if captcha["detected"]:
                if verbose:
                    print(f"  [X] CAPTCHA: {captcha['type']}")
                    if captcha["site_key"]:
                        print(f"      Site key: {captcha['site_key'][:30]}...")

                # Попытка подождать (иногда CloudFlare пропускает)
                if captcha["type"] == "CloudFlare":
                    if verbose:
                        print("  [*] Ждём CloudFlare challenge...")
                    time.sleep(5)

                    # Проверяем ещё раз
                    captcha = detect_captcha(page)
                    if not captcha["detected"]:
                        if verbose:
                            print("  [+] CloudFlare пройден!")

                if captcha["detected"]:
                    page.screenshot(path=f"debug_captcha_{domain.replace('.', '_')}.png")
                    return ScrapeResult(
                        domain=domain,
                        url=url,
                        status="CAPTCHA",
                        price=None,
                        title=page.title(),
                        captcha_detected=True,
                    )

            # Извлечение данных
            html = page.content()
            title = page.title()
            price = extract_price(html)

            if verbose:
                print(f"  [3] Title: {title[:40]}...")
                if price:
                    print(f"  [+] Цена: {price:,} ₽".replace(",", " "))
                else:
                    print("  [-] Цена не найдена")

            return ScrapeResult(
                domain=domain,
                url=url,
                status="OK" if price else "No Price",
                price=price,
                title=title,
                captcha_detected=False,
            )

        except Exception as e:
            if verbose:
                print(f"  [!] Ошибка: {type(e).__name__}")

            return ScrapeResult(
                domain=domain,
                url=url,
                status=f"Error: {type(e).__name__}",
                price=None,
                title="",
                captcha_detected=False,
            )

        finally:
            context.close()
            browser.close()


def main():
    """Тест stealth-парсера на заблокированных магазинах"""

    print("=" * 70)
    print("STEALTH SCRAPER - Обход CAPTCHA без платных сервисов")
    print("=" * 70)
    print("\nМетоды:")
    print("  - Playwright Stealth (маскировка fingerprints)")
    print("  - Human-like поведение (движения мыши, скролл)")
    print("  - Ротация User-Agent")
    print("  - Случайные задержки")

    # Тестовые URL (ранее заблокированные)
    test_urls = [
        "https://gbstore.ru/products/apple-macbook-pro-16-late-2021-z14v0008d",
        "https://kotofoto.ru/moskva/shop/noutbuki_apple_macbook/",
        "https://www.regard.ru/catalog/tovar421341.htm",
    ]

    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ")
    print("=" * 70)

    results = []
    for url in test_urls:
        result = scrape_with_stealth(url)
        results.append(result)

        # Пауза между запросами
        random_delay(3, 6)

    # Итоги
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 70)

    ok = [r for r in results if r.status == "OK"]
    captcha = [r for r in results if r.status == "CAPTCHA"]
    other = [r for r in results if r.status not in ["OK", "CAPTCHA"]]

    print(f"\n[+] Успешно: {len(ok)}")
    for r in ok:
        print(f"    {r.domain}: {r.price:,} ₽".replace(",", " ") if r.price else f"    {r.domain}: no price")

    print(f"\n[X] CAPTCHA: {len(captcha)}")
    for r in captcha:
        print(f"    {r.domain}")

    print(f"\n[?] Другое: {len(other)}")
    for r in other:
        print(f"    {r.domain}: {r.status}")


if __name__ == "__main__":
    main()
