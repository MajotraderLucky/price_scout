#!/usr/bin/env python3
"""
DNS-Shop с сохранением сессии после Qrator
Идея: пройти challenge один раз, сохранить cookies, использовать повторно
"""

import time
import sys
import re
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


SESSION_FILE = Path("/tmp/dns_session.json")


def wait_for_qrator(page, timeout: int = 30) -> bool:
    """Ждём прохождения Qrator challenge"""
    print("[*] Ожидание Qrator challenge...")

    start = time.time()
    while time.time() - start < timeout:
        url = page.url
        title = page.title()

        # Qrator пройден если:
        # - URL не содержит qrator
        # - Title содержит DNS или нормальное название
        if "qrator" not in url.lower() and "403" not in title and "401" not in title:
            if "dns" in title.lower() or "каталог" in title.lower():
                print(f"[+] Qrator пройден! Title: {title}")
                return True

        time.sleep(1)

    print(f"[!] Timeout. Title: {page.title()}")
    return False


def save_session(context):
    """Сохранить cookies и storage"""
    state = context.storage_state()
    SESSION_FILE.write_text(json.dumps(state, indent=2))
    print(f"[+] Сессия сохранена: {SESSION_FILE}")


def load_session() -> dict | None:
    """Загрузить сохранённую сессию"""
    if SESSION_FILE.exists():
        try:
            state = json.loads(SESSION_FILE.read_text())
            print(f"[+] Сессия загружена: {len(state.get('cookies', []))} cookies")
            return state
        except:
            pass
    return None


def search_dns(query: str, use_session: bool = True, headful: bool = False):
    """Поиск на DNS-Shop"""

    print("=" * 60)
    print("DNS-SHOP (session-based)")
    print("=" * 60)

    with sync_playwright() as p:
        # Загружаем сессию если есть
        storage_state = load_session() if use_session else None

        browser = p.chromium.launch(
            headless=not headful,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        # Anti-detection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
            window.chrome = { runtime: {} };
        """)

        try:
            # Если нет сессии - сначала главная для получения cookies
            if not storage_state:
                print("[*] Нет сессии, загружаем главную...")
                page.goto("https://www.dns-shop.ru/", wait_until="domcontentloaded", timeout=30000)

                if wait_for_qrator(page, timeout=20):
                    save_session(context)
                else:
                    print("[X] Не удалось пройти Qrator")
                    # Сохраним HTML для анализа
                    Path("/tmp/dns_qrator.html").write_text(page.content())
                    print("[*] HTML сохранён в /tmp/dns_qrator.html")
                    return []

            # Поиск
            print(f"\n[*] Поиск: {query}")
            search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # Ждём загрузки контента
            time.sleep(3)

            html = page.content()
            title = page.title()
            print(f"[*] Title: {title}")
            print(f"[*] Page size: {len(html)}")

            # Проверяем на блокировку
            if "403" in title or "401" in title:
                print("[X] Blocked!")
                # Удаляем невалидную сессию
                if SESSION_FILE.exists():
                    SESSION_FILE.unlink()
                    print("[*] Невалидная сессия удалена")
                return []

            # Ищем цены
            prices = re.findall(r'data-product-price="(\d+)"', html)

            if prices:
                print(f"\n[+] Найдено цен: {len(prices)}")
                prices_int = sorted([int(p) for p in prices])

                for i, price in enumerate(prices_int[:10], 1):
                    print(f"  {i}. {price:,} RUB".replace(",", " "))

                print(f"\n  Мин: {min(prices_int):,} RUB".replace(",", " "))
                print(f"  Макс: {max(prices_int):,} RUB".replace(",", " "))

                # Сохраняем успешную сессию
                save_session(context)
                return prices_int
            else:
                print("[!] Цены не найдены")
                Path("/tmp/dns_search.html").write_text(html)
                print("[*] HTML сохранён в /tmp/dns_search.html")
                return []

        except Exception as e:
            print(f"[!] Ошибка: {e}")
            return []
        finally:
            browser.close()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"

    # Сначала пробуем с сессией
    prices = search_dns(query, use_session=True)

    # Если не получилось - пробуем без сессии (свежий запрос)
    if not prices:
        print("\n[*] Повторная попытка без кэшированной сессии...")
        prices = search_dns(query, use_session=False)
