#!/usr/bin/env python3
"""
Avito Scraper с решением CAPTCHA

Avito блокирует по IP и показывает CAPTCHA.
Этот скрипт:
1. Загружает страницу через Firefox
2. Определяет тип CAPTCHA
3. Решает через 2Captcha API
4. Сохраняет cookies для последующих запросов
5. Парсит цены

Использование:
    export CAPTCHA_API_KEY='your_2captcha_key'
    python avito_captcha_scraper.py
"""

import os
import re
import sys
import json
import time
import random
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
    from playwright_stealth import Stealth
except ImportError:
    print("Установите: pip install playwright playwright-stealth")
    sys.exit(1)

try:
    from twocaptcha import TwoCaptcha
except ImportError:
    print("Установите: pip install 2captcha-python")
    sys.exit(1)


# === Конфигурация ===

AVITO_SEARCH_URL = "https://www.avito.ru/rossiya/noutbuki?q=MacBook+Pro+16"
COOKIES_FILE = "/tmp/avito_cookies.json"
OUTPUT_DIR = "/tmp/avito_scraper"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
]


# === CAPTCHA Solver ===

class AvitoCaptchaSolver:
    """Решение CAPTCHA для Avito"""

    def __init__(self, api_key: str):
        self.solver = TwoCaptcha(api_key)
        self.solver.pollingInterval = 5

    def get_balance(self) -> float:
        """Проверить баланс"""
        try:
            return float(self.solver.balance())
        except Exception as e:
            print(f"[2CAPTCHA] Ошибка баланса: {e}")
            return 0.0

    def solve_yandex_smartcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """
        Решить Yandex SmartCaptcha
        Avito использует Yandex SmartCaptcha
        """
        print(f"[2CAPTCHA] Решаем Yandex SmartCaptcha...")
        print(f"    Site key: {site_key[:30]}...")

        try:
            # Yandex SmartCaptcha решается как обычная turnstile/cloudflare
            result = self.solver.turnstile(
                sitekey=site_key,
                url=page_url,
            )
            token = result.get("code")
            print(f"[2CAPTCHA] Успех! Token: {token[:50]}...")
            return token

        except Exception as e:
            print(f"[2CAPTCHA] Ошибка: {e}")

            # Fallback: попробуем как reCAPTCHA
            try:
                print("[2CAPTCHA] Пробуем как reCAPTCHA...")
                result = self.solver.recaptcha(
                    sitekey=site_key,
                    url=page_url
                )
                return result.get("code")
            except Exception as e2:
                print(f"[2CAPTCHA] Fallback ошибка: {e2}")
                return None

    def solve_funcaptcha(self, public_key: str, page_url: str) -> Optional[str]:
        """Решить FunCaptcha (Arkose Labs)"""
        print(f"[2CAPTCHA] Решаем FunCaptcha...")

        try:
            result = self.solver.funcaptcha(
                sitekey=public_key,
                url=page_url
            )
            return result.get("code")
        except Exception as e:
            print(f"[2CAPTCHA] Ошибка: {e}")
            return None


# === Утилиты ===

def random_delay(min_sec: float = 2.0, max_sec: float = 5.0):
    time.sleep(random.uniform(min_sec, max_sec))


def human_scroll(page: Page):
    """Имитация человеческого скролла"""
    for _ in range(random.randint(2, 4)):
        page.mouse.wheel(0, random.randint(200, 400))
        time.sleep(random.uniform(0.3, 0.6))


def save_cookies(context: BrowserContext, filepath: str):
    """Сохранить cookies"""
    cookies = context.cookies()
    with open(filepath, 'w') as f:
        json.dump(cookies, f)
    print(f"[COOKIES] Сохранено: {filepath} ({len(cookies)} cookies)")


def load_cookies(context: BrowserContext, filepath: str) -> bool:
    """Загрузить cookies"""
    if not os.path.exists(filepath):
        return False

    try:
        with open(filepath, 'r') as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print(f"[COOKIES] Загружено: {len(cookies)} cookies")
        return True
    except Exception as e:
        print(f"[COOKIES] Ошибка загрузки: {e}")
        return False


# === CAPTCHA Detection ===

def detect_avito_captcha(page: Page) -> Dict:
    """
    Определить тип CAPTCHA на Avito

    Avito может использовать:
    - Yandex SmartCaptcha
    - FunCaptcha
    - Собственную CAPTCHA
    """
    result = {
        "type": "none",
        "site_key": None,
        "detected": False,
    }

    html = page.content()
    url = page.url

    # Проверка по URL
    if "blocked" in url.lower() or "captcha" in url.lower():
        result["detected"] = True

    # Проверка по тексту
    captcha_indicators = [
        "Доступ ограничен",
        "проблема с IP",
        "решения капчи",
        "captcha",
        "challenge",
    ]

    for indicator in captcha_indicators:
        if indicator.lower() in html.lower():
            result["detected"] = True
            break

    if not result["detected"]:
        return result

    print("[CAPTCHA] Обнаружена CAPTCHA, определяю тип...")

    # Yandex SmartCaptcha
    # <div class="SmartCaptcha" data-sitekey="...">
    match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
    if match:
        result["type"] = "yandex_smartcaptcha"
        result["site_key"] = match.group(1)
        print(f"    Тип: Yandex SmartCaptcha")
        return result

    # FunCaptcha / Arkose Labs
    # <div id="funcaptcha" data-pkey="...">
    match = re.search(r'data-pkey=["\']([^"\']+)["\']', html)
    if match:
        result["type"] = "funcaptcha"
        result["site_key"] = match.group(1)
        print(f"    Тип: FunCaptcha")
        return result

    # reCAPTCHA
    recaptcha = page.query_selector('[data-sitekey]')
    if recaptcha:
        result["type"] = "recaptcha"
        result["site_key"] = recaptcha.get_attribute("data-sitekey")
        print(f"    Тип: reCAPTCHA")
        return result

    # hCaptcha
    hcaptcha = page.query_selector('.h-captcha, [data-hcaptcha-sitekey]')
    if hcaptcha:
        result["type"] = "hcaptcha"
        result["site_key"] = hcaptcha.get_attribute("data-sitekey")
        print(f"    Тип: hCaptcha")
        return result

    # Неизвестная CAPTCHA - сохраняем скриншот для анализа
    result["type"] = "unknown"
    print("    Тип: Неизвестный (сохраняю скриншот)")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    page.screenshot(path=f"{OUTPUT_DIR}/captcha_unknown.png")

    # Сохраняем HTML для анализа
    with open(f"{OUTPUT_DIR}/captcha_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    return result


# === Main Scraper ===

def scrape_avito(api_key: Optional[str] = None) -> Dict:
    """
    Парсинг Avito с решением CAPTCHA

    Returns:
        {
            "status": "success" | "captcha_required" | "error",
            "prices": [...],
            "count": N,
            "error": "..."
        }
    """
    print("=" * 60)
    print("AVITO SCRAPER WITH CAPTCHA SOLVING")
    print("=" * 60)
    print(f"\nURL: {AVITO_SEARCH_URL}")

    result = {
        "status": "error",
        "prices": [],
        "count": 0,
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    # Инициализация solver если есть API ключ
    solver = None
    if api_key:
        solver = AvitoCaptchaSolver(api_key)
        balance = solver.get_balance()
        print(f"[2CAPTCHA] Баланс: ${balance:.2f}")

        if balance < 0.01:
            print("[!] Недостаточно средств на 2Captcha")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Запуск браузера
        browser = p.firefox.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice(USER_AGENTS),
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        # Пробуем загрузить cookies
        cookies_loaded = load_cookies(context, COOKIES_FILE)

        page = context.new_page()

        # Stealth patches
        stealth = Stealth(
            navigator_languages_override=("ru-RU", "ru"),
            navigator_platform_override="Win32",
        )
        stealth.apply_stealth_sync(page)

        try:
            # Начальная задержка
            random_delay(3, 5)

            print("\n[1] Загрузка страницы...")
            response = page.goto(
                AVITO_SEARCH_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )
            print(f"    HTTP: {response.status}")

            random_delay(5, 8)

            # Проверка CAPTCHA
            print("\n[2] Проверка CAPTCHA...")
            captcha_info = detect_avito_captcha(page)

            if captcha_info["detected"]:
                print(f"    CAPTCHA обнаружена: {captcha_info['type']}")

                # Сохраняем скриншот CAPTCHA
                page.screenshot(path=f"{OUTPUT_DIR}/captcha_detected.png")
                print(f"    Скриншот: {OUTPUT_DIR}/captcha_detected.png")

                if not solver:
                    result["status"] = "captcha_required"
                    result["error"] = f"CAPTCHA ({captcha_info['type']}) требует API ключ 2Captcha"
                    print(f"\n[!] {result['error']}")
                    print("    Установите: export CAPTCHA_API_KEY='your_key'")
                    return result

                if not captcha_info["site_key"]:
                    result["status"] = "captcha_required"
                    result["error"] = f"Не удалось найти site_key для {captcha_info['type']}"
                    return result

                # Решаем CAPTCHA
                print("\n[3] Решение CAPTCHA (20-60 сек)...")
                token = None

                if captcha_info["type"] == "yandex_smartcaptcha":
                    token = solver.solve_yandex_smartcaptcha(
                        captcha_info["site_key"],
                        page.url
                    )
                elif captcha_info["type"] == "funcaptcha":
                    token = solver.solve_funcaptcha(
                        captcha_info["site_key"],
                        page.url
                    )
                elif captcha_info["type"] == "recaptcha":
                    try:
                        res = solver.solver.recaptcha(
                            sitekey=captcha_info["site_key"],
                            url=page.url
                        )
                        token = res.get("code")
                    except Exception as e:
                        print(f"[2CAPTCHA] Ошибка: {e}")

                if token:
                    print("\n[4] Вставка токена и отправка...")

                    # Вставляем токен
                    try:
                        page.evaluate(f'''
                            // Ищем поле для токена
                            const inputs = document.querySelectorAll('input[name*="captcha"], textarea[name*="captcha"], [name="smart-token"]');
                            inputs.forEach(input => input.value = "{token}");

                            // Или в hidden field
                            const hidden = document.querySelector('input[type="hidden"][name*="token"]');
                            if (hidden) hidden.value = "{token}";
                        ''')
                    except Exception as e:
                        print(f"    Ошибка вставки: {e}")

                    # Кликаем кнопку "Продолжить"
                    continue_btn = page.query_selector('button:has-text("Продолжить"), input[type="submit"]')
                    if continue_btn:
                        continue_btn.click()
                        random_delay(5, 8)

                    # Проверяем результат
                    page.screenshot(path=f"{OUTPUT_DIR}/after_captcha.png")

                    # Повторная проверка CAPTCHA
                    captcha_check = detect_avito_captcha(page)
                    if captcha_check["detected"]:
                        result["status"] = "captcha_required"
                        result["error"] = "CAPTCHA не пройдена после решения"
                        return result

                    # Сохраняем cookies после успешного прохождения
                    save_cookies(context, COOKIES_FILE)
                else:
                    result["status"] = "captcha_required"
                    result["error"] = "Не удалось получить токен от 2Captcha"
                    return result

            # Парсинг данных
            print("\n[5] Парсинг данных...")

            html = page.content()

            # Сохраняем HTML
            with open(f"{OUTPUT_DIR}/avito_result.html", "w", encoding="utf-8") as f:
                f.write(html)

            # Извлекаем цены
            # Avito: data-marker="item-price" или itemprop="price"
            prices = []

            # Метод 1: data-marker
            price_elements = page.query_selector_all('[data-marker="item-price"]')
            for el in price_elements:
                text = el.text_content()
                if text:
                    clean = re.sub(r'[^\d]', '', text)
                    if clean and clean.isdigit():
                        price = int(clean)
                        if 50000 < price < 500000:
                            prices.append(price)

            # Метод 2: itemprop="price"
            if not prices:
                for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html):
                    price = int(match)
                    if 50000 < price < 500000:
                        prices.append(price)

            # Метод 3: JSON в data-* атрибутах
            if not prices:
                for match in re.findall(r'"price":\s*(\d+)', html):
                    price = int(match)
                    if 50000 < price < 500000:
                        prices.append(price)

            # Убираем дубликаты
            prices = sorted(set(prices))

            if prices:
                result["status"] = "success"
                result["prices"] = prices
                result["count"] = len(prices)
                print(f"    Найдено: {len(prices)} цен")
                print(f"    Диапазон: {min(prices):,} - {max(prices):,} RUB")

                # Сохраняем cookies при успехе
                save_cookies(context, COOKIES_FILE)
            else:
                result["status"] = "no_prices"
                result["error"] = "Цены не найдены в HTML"
                print("    [!] Цены не найдены")

                # Скриншот для отладки
                page.screenshot(path=f"{OUTPUT_DIR}/no_prices.png")

        except Exception as e:
            result["status"] = "error"
            result["error"] = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ОШИБКА] {result['error']}")
            page.screenshot(path=f"{OUTPUT_DIR}/error.png")

        finally:
            context.close()
            browser.close()

    # Сохраняем результат в JSON
    with open(f"{OUTPUT_DIR}/result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Результат: {result['status']}")
    if result["prices"]:
        print(f"Цены: {result['prices'][:5]}...")
    print(f"{'=' * 60}")

    return result


if __name__ == "__main__":
    api_key = os.environ.get("CAPTCHA_API_KEY")

    if not api_key:
        print("[!] API ключ 2Captcha не найден")
        print("    Установите: export CAPTCHA_API_KEY='your_key'")
        print("\n    Запускаю без решения CAPTCHA (только диагностика)...\n")

    result = scrape_avito(api_key)

    if result["status"] == "captcha_required":
        print("\n" + "=" * 60)
        print("CAPTCHA ТРЕБУЕТСЯ")
        print("=" * 60)
        print("""
Для решения CAPTCHA на Avito:

1. Зарегистрируйтесь на https://2captcha.com/
2. Пополните баланс (мин. $3)
3. Получите API ключ
4. Запустите:

   export CAPTCHA_API_KEY='your_key'
   python avito_captcha_scraper.py

Стоимость: ~$2.99 за 1000 CAPTCHA
""")
