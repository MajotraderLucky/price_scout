#!/usr/bin/env python3
"""
DNS-Shop parser - headful режим через Xvfb
Обход Qrator protection

Запуск:
    xvfb-run -a python test_dns_headful.py "MacBook Pro 16"
"""

import time
import sys
import re

from playwright.sync_api import sync_playwright


def test_dns_headful(query: str = "MacBook Pro 16"):
    """Тест DNS-Shop в headful режиме"""

    print("=" * 60)
    print("DNS-SHOP TEST (headful via Xvfb)")
    print("=" * 60)

    with sync_playwright() as p:
        # Headful режим (не headless!)
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        page = context.new_page()

        # Убираем webdriver detection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__proto__.webdriver;
        """)

        try:
            print("[*] Загрузка главной страницы...")
            page.goto("https://www.dns-shop.ru/", wait_until="networkidle", timeout=60000)

            # Ждём прохождения Qrator challenge
            time.sleep(5)

            current_url = page.url
            title = page.title()

            print(f"[*] URL: {current_url}")
            print(f"[*] Title: {title}")

            # Проверяем прошёл ли challenge
            if "qrator" in page.content().lower() or "401" in title:
                print("[!] Qrator challenge не пройден, ждём...")
                page.wait_for_load_state("networkidle", timeout=30000)
                time.sleep(5)

                title = page.title()
                print(f"[*] Title after wait: {title}")

            if "dns" not in title.lower() and "403" not in title and "401" not in title:
                print("[!] Странный title, проверяем контент...")

            html = page.content()
            print(f"[*] Page length: {len(html)}")

            # Проверка на блокировку
            if "access denied" in html.lower() or "заблокирован" in html.lower():
                print("[X] Access Denied!")
                with open("/tmp/dns_blocked.html", "w") as f:
                    f.write(html)
                print("[*] HTML сохранён в /tmp/dns_blocked.html")
                return False

            # Если главная загрузилась - идём на поиск
            if "dns-shop" in current_url.lower() or "dns" in title.lower():
                print(f"\n[+] Главная загрузилась!")
                print(f"[*] Поиск: {query}")

                search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"
                page.goto(search_url, wait_until="networkidle", timeout=60000)
                time.sleep(3)

                html = page.content()
                print(f"[*] Search URL: {page.url}")
                print(f"[*] Search Title: {page.title()}")
                print(f"[*] Page length: {len(html)}")

                # Ищем цены
                prices = re.findall(r'data-product-price="(\d+)"', html)
                if prices:
                    print(f"\n[+] Найдено цен: {len(prices)}")
                    for i, price in enumerate(prices[:10], 1):
                        print(f"  {i}. {int(price):,} RUB".replace(",", " "))

                    prices_int = [int(p) for p in prices]
                    print(f"\n  Мин: {min(prices_int):,} RUB".replace(",", " "))
                    print(f"  Макс: {max(prices_int):,} RUB".replace(",", " "))
                    return True
                else:
                    print("[!] Цены не найдены в HTML")
                    with open("/tmp/dns_search.html", "w") as f:
                        f.write(html)
                    print("[*] HTML сохранён в /tmp/dns_search.html")

            return False

        except Exception as e:
            print(f"[!] Ошибка: {e}")
            return False

        finally:
            browser.close()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"
    test_dns_headful(query)
