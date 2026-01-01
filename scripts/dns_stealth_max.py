#!/usr/bin/env python3
"""
DNS-Shop с максимальным stealth
"""

import time
import sys
import re
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    print("[!] playwright-stealth не установлен")


def search_dns(query: str):
    print("=" * 60)
    print("DNS-SHOP (max stealth)")
    print("=" * 60)

    with sync_playwright() as p:
        # Используем Firefox вместо Chromium - меньше детектится
        browser = p.firefox.launch(
            headless=True,
            args=[]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            color_scheme="light",
            # Эмуляция реального устройства
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )

        page = context.new_page()

        # Применяем stealth если доступен
        if HAS_STEALTH:
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

        # Дополнительные патчи
        page.add_init_script("""
            // Удаляем webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Подделываем plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                    ];
                    plugins.length = 3;
                    return plugins;
                }
            });

            // Подделываем languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });

            // Chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // WebGL vendor
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.apply(this, arguments);
            };
        """)

        try:
            print("[*] Загрузка главной (Firefox)...")

            # Сначала простой запрос
            response = page.goto(
                "https://www.dns-shop.ru/",
                wait_until="commit",
                timeout=30000
            )

            print(f"[*] Status: {response.status}")

            # Ждём полной загрузки
            time.sleep(5)
            page.wait_for_load_state("networkidle", timeout=30000)

            title = page.title()
            url = page.url

            print(f"[*] URL: {url}")
            print(f"[*] Title: {title}")

            if "403" in title or "401" in title:
                print("[X] Blocked!")
                html = page.content()

                # Проверим IP
                ip_match = re.search(r'IP: ([0-9.]+)', html)
                if ip_match:
                    print(f"[*] Blocked IP: {ip_match.group(1)}")

                with open("/tmp/dns_firefox.html", "w") as f:
                    f.write(html)
                return []

            # Если прошли - ищем
            print(f"\n[+] Главная загружена!")
            print(f"[*] Поиск: {query}")

            search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            html = page.content()
            print(f"[*] Search title: {page.title()}")

            prices = re.findall(r'data-product-price="(\d+)"', html)
            if prices:
                print(f"\n[+] Найдено цен: {len(prices)}")
                for i, p in enumerate(sorted([int(x) for x in prices])[:10], 1):
                    print(f"  {i}. {p:,} RUB".replace(",", " "))
                return prices
            else:
                print("[!] Цены не найдены")
                return []

        except Exception as e:
            print(f"[!] Ошибка: {e}")
            return []
        finally:
            browser.close()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"
    search_dns(query)
