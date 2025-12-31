#!/usr/bin/env python3
"""
Тест интеграции 2Captcha для решения CAPTCHA

Типы поддерживаемых CAPTCHA:
- reCAPTCHA v2 (checkbox)
- reCAPTCHA v3 (invisible)
- hCaptcha
- Image CAPTCHA

Документация: https://2captcha.com/2captcha-api
Стоимость: ~$2.99 за 1000 CAPTCHA
"""

import os
import sys
import re
import json
import time
from typing import Optional

try:
    from twocaptcha import TwoCaptcha
except ImportError:
    print("Установите: pip install 2captcha-python")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    print("Установите: pip install playwright")
    sys.exit(1)


class CaptchaSolver:
    """Решение CAPTCHA через 2Captcha API"""

    def __init__(self, api_key: str):
        self.solver = TwoCaptcha(api_key)
        self.solver.pollingInterval = 5  # Интервал проверки (сек)

    def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        """
        Решить reCAPTCHA v2

        Args:
            site_key: data-sitekey из HTML
            page_url: URL страницы с CAPTCHA

        Returns:
            g-recaptcha-response token или None
        """
        print(f"[2CAPTCHA] Решаем reCAPTCHA v2...")
        print(f"    Site key: {site_key[:20]}...")
        print(f"    URL: {page_url[:50]}...")

        try:
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=page_url
            )
            token = result.get("code")
            print(f"[2CAPTCHA] Успех! Token: {token[:50]}...")
            return token

        except Exception as e:
            print(f"[2CAPTCHA] Ошибка: {e}")
            return None

    def solve_recaptcha_v3(self, site_key: str, page_url: str,
                           action: str = "verify", min_score: float = 0.7) -> Optional[str]:
        """
        Решить reCAPTCHA v3 (invisible)

        Args:
            site_key: data-sitekey
            page_url: URL страницы
            action: action parameter (default: verify)
            min_score: минимальный score (0.1-0.9)
        """
        print(f"[2CAPTCHA] Решаем reCAPTCHA v3...")

        try:
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=page_url,
                version="v3",
                action=action,
                score=min_score
            )
            return result.get("code")

        except Exception as e:
            print(f"[2CAPTCHA] Ошибка: {e}")
            return None

    def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Решить hCaptcha"""
        print(f"[2CAPTCHA] Решаем hCaptcha...")

        try:
            result = self.solver.hcaptcha(
                sitekey=site_key,
                url=page_url
            )
            return result.get("code")

        except Exception as e:
            print(f"[2CAPTCHA] Ошибка: {e}")
            return None

    def get_balance(self) -> float:
        """Получить баланс аккаунта"""
        try:
            balance = self.solver.balance()
            return float(balance)
        except Exception as e:
            print(f"[2CAPTCHA] Ошибка получения баланса: {e}")
            return 0.0


def detect_captcha(page: Page) -> dict:
    """
    Определить тип CAPTCHA на странице

    Returns:
        {
            "type": "recaptcha_v2" | "recaptcha_v3" | "hcaptcha" | "none",
            "site_key": "...",
            "action": "..." (для v3)
        }
    """
    result = {"type": "none", "site_key": None, "action": None}

    # Проверка reCAPTCHA v2
    recaptcha_v2 = page.query_selector('[data-sitekey]')
    if recaptcha_v2:
        site_key = recaptcha_v2.get_attribute("data-sitekey")
        result["type"] = "recaptcha_v2"
        result["site_key"] = site_key
        return result

    # Проверка reCAPTCHA v3 (в скриптах)
    scripts = page.query_selector_all("script")
    for script in scripts:
        src = script.get_attribute("src") or ""
        if "recaptcha" in src and "v3" in src:
            # Попытка найти site key в URL или в коде
            match = re.search(r'render=([A-Za-z0-9_-]+)', src)
            if match:
                result["type"] = "recaptcha_v3"
                result["site_key"] = match.group(1)
                return result

    # Проверка hCaptcha
    hcaptcha = page.query_selector('[data-hcaptcha-sitekey], .h-captcha')
    if hcaptcha:
        site_key = hcaptcha.get_attribute("data-sitekey") or \
                   hcaptcha.get_attribute("data-hcaptcha-sitekey")
        result["type"] = "hcaptcha"
        result["site_key"] = site_key
        return result

    # Проверка по тексту страницы
    content = page.content().lower()
    if "captcha" in content or "recaptcha" in content:
        result["type"] = "unknown_captcha"

    return result


def inject_captcha_token(page: Page, token: str, captcha_type: str) -> bool:
    """
    Вставить решённый токен в форму

    Args:
        page: Playwright page
        token: g-recaptcha-response или h-captcha-response
        captcha_type: тип CAPTCHA
    """
    try:
        if captcha_type in ["recaptcha_v2", "recaptcha_v3"]:
            # Вставляем в textarea g-recaptcha-response
            page.evaluate(f'''
                document.querySelector('[name="g-recaptcha-response"]').value = "{token}";
                // Также в iframe если есть
                const iframe = document.querySelector('iframe[title*="recaptcha"]');
                if (iframe) {{
                    iframe.contentDocument.querySelector('#g-recaptcha-response').value = "{token}";
                }}
            ''')
            return True

        elif captcha_type == "hcaptcha":
            page.evaluate(f'''
                document.querySelector('[name="h-captcha-response"]').value = "{token}";
            ''')
            return True

    except Exception as e:
        print(f"[INJECT] Ошибка: {e}")
        return False

    return False


def scrape_with_captcha(url: str, api_key: str):
    """
    Полный цикл: загрузка страницы -> решение CAPTCHA -> парсинг
    """
    print(f"\n{'='*60}")
    print("SCRAPING WITH CAPTCHA SOLVING")
    print(f"{'='*60}")
    print(f"\nURL: {url}")

    solver = CaptchaSolver(api_key)

    # Проверка баланса
    balance = solver.get_balance()
    print(f"[2CAPTCHA] Баланс: ${balance:.2f}")

    if balance < 0.01:
        print("[!] Недостаточно средств на балансе 2Captcha")
        return None

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

        try:
            # Загрузка страницы
            print("\n[1] Загрузка страницы...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"    Status: {response.status}")

            time.sleep(3)

            # Детекция CAPTCHA
            print("\n[2] Поиск CAPTCHA...")
            captcha_info = detect_captcha(page)
            print(f"    Тип: {captcha_info['type']}")

            if captcha_info["type"] == "none":
                print("    CAPTCHA не обнаружена!")

            elif captcha_info["type"] == "unknown_captcha":
                print("    Обнаружена неизвестная CAPTCHA")
                page.screenshot(path="debug_unknown_captcha.png")

            elif captcha_info["site_key"]:
                print(f"    Site key: {captcha_info['site_key'][:30]}...")

                # Решаем CAPTCHA
                print("\n[3] Решение CAPTCHA (это займёт ~20-60 сек)...")

                token = None
                if captcha_info["type"] == "recaptcha_v2":
                    token = solver.solve_recaptcha_v2(
                        captcha_info["site_key"],
                        url
                    )
                elif captcha_info["type"] == "recaptcha_v3":
                    token = solver.solve_recaptcha_v3(
                        captcha_info["site_key"],
                        url
                    )
                elif captcha_info["type"] == "hcaptcha":
                    token = solver.solve_hcaptcha(
                        captcha_info["site_key"],
                        url
                    )

                if token:
                    print("\n[4] Вставка токена...")
                    inject_captcha_token(page, token, captcha_info["type"])

                    # Отправка формы (если есть кнопка)
                    submit_btn = page.query_selector('button[type="submit"], input[type="submit"]')
                    if submit_btn:
                        submit_btn.click()
                        time.sleep(3)

                    print("\n[5] Проверка результата...")
                    page.screenshot(path="debug_after_captcha.png")
                    print("    Скриншот: debug_after_captcha.png")

            # Парсинг данных
            print("\n[6] Извлечение данных...")
            title = page.title()
            print(f"    Title: {title[:50]}...")

            # Сохранение HTML
            with open("debug_result.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("    HTML сохранён: debug_result.html")

        except Exception as e:
            print(f"\n[ОШИБКА] {type(e).__name__}: {e}")
            page.screenshot(path="debug_error.png")

        finally:
            context.close()
            browser.close()

    print(f"\n{'='*60}")


def demo_without_real_captcha():
    """Демо режим без реального API ключа"""
    print(f"\n{'='*60}")
    print("ДЕМО: Как работает решение CAPTCHA")
    print(f"{'='*60}")

    print("""
Процесс решения reCAPTCHA v2:

1. Playwright загружает страницу
2. Скрипт находит элемент с data-sitekey
3. Отправляем site_key + URL в 2Captcha API
4. 2Captcha показывает CAPTCHA работнику (человеку)
5. Работник решает CAPTCHA за ~20-60 секунд
6. API возвращает g-recaptcha-response токен
7. Скрипт вставляет токен в форму
8. Отправляем форму / продолжаем парсинг

Стоимость:
- reCAPTCHA v2: $2.99 / 1000
- reCAPTCHA v3: $2.99 / 1000
- hCaptcha: $2.99 / 1000

Для работы нужен API ключ 2Captcha:
1. Регистрация: https://2captcha.com/
2. Пополнение баланса (мин. $3)
3. Получение API ключа в личном кабинете
""")

    print("\nЗапуск:")
    print("  export CAPTCHA_API_KEY='your_2captcha_api_key'")
    print("  python scripts/test_captcha_solver.py")


if __name__ == "__main__":
    # Получаем API ключ из переменной окружения
    api_key = os.environ.get("CAPTCHA_API_KEY")

    if not api_key:
        print("[!] API ключ не найден")
        print("    Установите: export CAPTCHA_API_KEY='your_key'")
        print("\n    Запускаю демо режим...\n")
        demo_without_real_captcha()
    else:
        # Тест на Citilink
        test_url = "https://www.citilink.ru/search/?text=Samsung+Galaxy+S24"
        scrape_with_captcha(test_url, api_key)
