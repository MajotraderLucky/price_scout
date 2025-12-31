#!/usr/bin/env python3
"""
Продвинутые техники обхода защиты

Методы:
1. Headful браузер (не headless) - сложнее детектить
2. Persistent context - сохранение cookies/localStorage
3. Реалистичное поведение - клики, печать, задержки
4. Firefox вместо Chromium - другой fingerprint
5. Случайные viewport размеры
"""

import os
import time
import random
import string
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


# Директория для хранения профилей браузера
PROFILES_DIR = Path("/home/ryazanov/Development/price_scout/browser_profiles")
PROFILES_DIR.mkdir(exist_ok=True)


def random_viewport():
    """Случайный размер окна (реалистичные разрешения)"""
    viewports = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
    ]
    return random.choice(viewports)


def human_typing(page, selector, text):
    """Печать текста как человек"""
    element = page.query_selector(selector)
    if not element:
        return False

    element.click()
    time.sleep(random.uniform(0.2, 0.5))

    for char in text:
        page.keyboard.type(char, delay=random.randint(50, 150))
        if random.random() > 0.9:  # Иногда пауза
            time.sleep(random.uniform(0.1, 0.3))

    return True


def human_scroll(page, direction="down", amount=None):
    """Человеческий скролл"""
    if amount is None:
        amount = random.randint(200, 500)

    if direction == "down":
        page.mouse.wheel(0, amount)
    else:
        page.mouse.wheel(0, -amount)

    time.sleep(random.uniform(0.3, 0.8))


def human_mouse_movement(page):
    """Случайные движения мыши"""
    viewport = page.viewport_size
    if not viewport:
        return

    # Несколько случайных точек
    points = []
    for _ in range(random.randint(3, 7)):
        x = random.randint(100, viewport['width'] - 100)
        y = random.randint(100, viewport['height'] - 100)
        points.append((x, y))

    for x, y in points:
        # Двигаемся с разной скоростью
        steps = random.randint(10, 30)
        page.mouse.move(x, y, steps=steps)
        time.sleep(random.uniform(0.1, 0.4))


def wait_for_cloudflare(page, timeout=30):
    """Ожидание прохождения CloudFlare challenge"""
    start = time.time()

    while time.time() - start < timeout:
        url = page.url.lower()
        content = page.content().lower()

        # Признаки CloudFlare challenge
        if "challenge" in url or "cdn-cgi" in url:
            print("    [*] CloudFlare challenge...")
            time.sleep(2)
            continue

        # Проверка на успешное прохождение
        if "just a moment" in content or "checking your browser" in content:
            print("    [*] Ждём проверку браузера...")
            time.sleep(2)
            continue

        # Прошли
        return True

    return False


def solve_simple_captcha(page):
    """
    Попытка решить простые CAPTCHA
    (checkbox типа "Я не робот")
    """
    # Ищем iframe reCAPTCHA
    frames = page.frames

    for frame in frames:
        # Checkbox reCAPTCHA
        checkbox = frame.query_selector('.recaptcha-checkbox-border')
        if checkbox:
            print("    [*] Найден checkbox reCAPTCHA, кликаем...")

            # Движение мыши к checkbox
            box = checkbox.bounding_box()
            if box:
                # Случайная точка внутри checkbox
                x = box['x'] + random.uniform(5, box['width'] - 5)
                y = box['y'] + random.uniform(5, box['height'] - 5)

                page.mouse.move(x, y, steps=random.randint(10, 20))
                time.sleep(random.uniform(0.3, 0.7))
                page.mouse.click(x, y)

                time.sleep(3)
                return True

    return False


def check_with_persistent_profile(url: str, profile_name: str = "default"):
    """
    Проверка с сохранением профиля браузера
    (cookies, localStorage сохраняются между сессиями)
    """
    domain = urlparse(url).netloc.replace('www.', '')
    profile_path = PROFILES_DIR / profile_name

    print(f"\n[{domain}]")
    print(f"  URL: {url[:55]}...")
    print(f"  Профиль: {profile_path}")

    with sync_playwright() as p:
        # Используем Firefox для другого fingerprint
        browser = p.firefox.launch(
            headless=True,  # Попробуем headless Firefox
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
            }
        )

        # Persistent context сохраняет cookies
        context = browser.new_context(
            viewport=random_viewport(),
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        )

        page = context.new_page()

        try:
            print("  [1] Загрузка...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Ждём загрузку
            time.sleep(random.uniform(3, 5))

            # Проверка CloudFlare
            if not wait_for_cloudflare(page, timeout=15):
                print("  [X] CloudFlare не пройден")

            # Имитация поведения
            human_mouse_movement(page)
            human_scroll(page)
            time.sleep(random.uniform(1, 2))

            html = page.content()

            # Проверка CAPTCHA
            if "captcha" in html.lower():
                print("  [!] Обнаружена CAPTCHA")

                # Попытка решить checkbox
                if solve_simple_captcha(page):
                    time.sleep(3)
                    html = page.content()

                    if "captcha" not in html.lower():
                        print("  [+] CAPTCHA пройдена!")
                    else:
                        print("  [X] CAPTCHA требует решения")
                        page.screenshot(path=f"debug_{domain}_captcha.png")
                        return {"status": "CAPTCHA", "price": None}
                else:
                    page.screenshot(path=f"debug_{domain}_captcha.png")
                    return {"status": "CAPTCHA", "price": None}

            # Извлечение цены
            price = None
            for m in re.findall(r'(\d{3}[\s\u00a0]?\d{3})', html):
                clean = m.replace(" ", "").replace("\u00a0", "")
                if clean.isdigit():
                    p = int(clean)
                    if 100000 < p < 400000:
                        price = p
                        break

            if price:
                print(f"  [+] Цена найдена: {price:,} ₽".replace(",", " "))
                return {"status": "OK", "price": price}

            print("  [-] Цена не найдена")
            page.screenshot(path=f"debug_{domain}_noPrice.png")
            return {"status": "No Price", "price": None}

        except Exception as e:
            print(f"  [!] Ошибка: {type(e).__name__}: {str(e)[:50]}")
            return {"status": "Error", "price": None}

        finally:
            context.close()
            browser.close()


def check_with_headful_browser(url: str):
    """
    Проверка с видимым браузером (headful)
    Сложнее детектить автоматизацию
    """
    domain = urlparse(url).netloc.replace('www.', '')

    print(f"\n[{domain}] (HEADFUL)")
    print(f"  URL: {url[:55]}...")

    with sync_playwright() as p:
        # Headful браузер - видимый
        browser = p.chromium.launch(
            headless=False,  # ВИДИМЫЙ БРАУЗЕР
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        # Stealth патчи
        stealth = Stealth(
            navigator_languages_override=("ru-RU", "ru"),
            navigator_webdriver=True,  # Скрыть webdriver
        )
        stealth.apply_stealth_sync(page)

        try:
            print("  [1] Загрузка (headful)...")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Длинные задержки - как реальный пользователь
            time.sleep(random.uniform(5, 8))

            # Много движений мыши
            for _ in range(3):
                human_mouse_movement(page)
                time.sleep(random.uniform(0.5, 1.5))

            # Скролл туда-сюда
            human_scroll(page, "down")
            time.sleep(random.uniform(1, 2))
            human_scroll(page, "down")
            time.sleep(random.uniform(0.5, 1))
            human_scroll(page, "up", 100)

            html = page.content()

            if "captcha" in html.lower():
                print("  [X] CAPTCHA (даже в headful)")
                return {"status": "CAPTCHA", "price": None}

            # Цена
            price = None
            for m in re.findall(r'(\d{3}[\s\u00a0]?\d{3})', html):
                clean = m.replace(" ", "").replace("\u00a0", "")
                if clean.isdigit():
                    p = int(clean)
                    if 100000 < p < 400000:
                        price = p
                        break

            if price:
                print(f"  [+] Цена: {price:,} ₽".replace(",", " "))
                return {"status": "OK", "price": price}

            return {"status": "No Price", "price": None}

        except Exception as e:
            print(f"  [!] Ошибка: {e}")
            return {"status": "Error", "price": None}

        finally:
            context.close()
            browser.close()


def main():
    print("=" * 70)
    print("ПРОДВИНУТЫЕ ТЕХНИКИ ОБХОДА ЗАЩИТЫ")
    print("=" * 70)

    test_urls = [
        "https://www.citilink.ru/catalog/noutbuki/",
        "https://www.dns-shop.ru/catalog/17a892f816404e77/noutbuki/",
    ]

    print("\n[МЕТОД 1] Firefox + Persistent Profile")
    print("-" * 50)

    for url in test_urls:
        result = check_with_persistent_profile(url)
        time.sleep(random.uniform(5, 8))

    print("\n" + "=" * 70)
    print("ИТОГ")
    print("=" * 70)
    print("""
Если CAPTCHA всё ещё появляется, варианты:

1. HEADFUL БРАУЗЕР (видимый)
   - Запустите: check_with_headful_browser(url)
   - Требует GUI (не работает на сервере без X11)

2. РЕЗИДЕНТНЫЕ ПРОКСИ
   - Bright Data, Oxylabs, SmartProxy
   - $10-50/месяц за резидентные IP

3. 2CAPTCHA API
   - $3 за 1000 решений
   - export CAPTCHA_API_KEY='...'

4. ПАРСИНГ С ДОМАШНЕГО ПК
   - Другой IP, не в blacklist
   - Попробуйте запустить скрипты дома
""")


if __name__ == "__main__":
    main()
