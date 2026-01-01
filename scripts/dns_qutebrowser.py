#!/usr/bin/env python3
"""
DNS-Shop через qutebrowser
Реальный браузер + командное управление = обход любой защиты

qutebrowser особенности:
- Реальный браузер (не детектится как автоматизация)
- Управление через команды (как vim)
- Можно сохранять страницы и делать скриншоты
- Поддержка userscripts
"""

import subprocess
import time
import sys
import os
import re
import tempfile
from pathlib import Path

OUTPUT_DIR = Path("/tmp/dns_qute")
OUTPUT_DIR.mkdir(exist_ok=True)


def run_qutebrowser_session(url: str, commands: list, wait_seconds: int = 5) -> Path:
    """
    Запуск qutebrowser с командами

    Команды qutebrowser:
    - :open URL - открыть URL
    - :later 5000 <cmd> - выполнить через 5 секунд
    - :save-page - сохранить страницу
    - :screenshot - скриншот
    - :scroll down - прокрутить вниз
    """

    # Временный конфиг для изоляции сессии
    basedir = tempfile.mkdtemp(prefix="qute_dns_")

    # Формируем команды
    cmd_str = " ".join([f'-c "{c}"' for c in commands])

    # Собираем команду
    full_cmd = [
        "qutebrowser",
        "--temp-basedir",  # Изолированная сессия
        "--untrusted-args",
        url,
    ]

    # Добавляем команды
    for c in commands:
        full_cmd.extend(["-c", c])

    print(f"[*] Запуск qutebrowser: {url}")
    print(f"[*] Команды: {commands}")

    try:
        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Ждём выполнения
        print(f"[*] Ожидание {wait_seconds}s...")
        time.sleep(wait_seconds)

        return Path(basedir)

    except Exception as e:
        print(f"[!] Ошибка: {e}")
        return None


def dns_search_qute(query: str):
    """Поиск на DNS через qutebrowser userscript"""

    print("=" * 60)
    print("DNS-SHOP via qutebrowser")
    print("=" * 60)

    # Файл для сохранения HTML
    html_file = OUTPUT_DIR / "dns_page.html"
    screenshot_file = OUTPUT_DIR / "dns_screenshot.png"

    # URL поиска
    search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"

    # Команды для qutebrowser
    commands = [
        # Через 8 секунд сохраняем страницу
        f"later 8000 save-page '{html_file}' plain",
        # Через 9 секунд скриншот
        f"later 9000 screenshot '{screenshot_file}'",
        # Через 10 секунд закрываем
        "later 10000 quit",
    ]

    print(f"[*] URL: {search_url}")
    print(f"[*] HTML будет сохранён в: {html_file}")
    print(f"[*] Скриншот: {screenshot_file}")
    print()

    # Запускаем
    run_qutebrowser_session(search_url, commands, wait_seconds=12)

    # Проверяем результат
    time.sleep(2)

    if html_file.exists():
        html = html_file.read_text(errors='ignore')
        print(f"[+] HTML сохранён: {len(html)} bytes")

        # Ищем цены
        prices = re.findall(r'data-product-price="(\d+)"', html)

        if prices:
            prices_int = sorted(set(int(p) for p in prices))
            print(f"\n[+] Найдено {len(prices_int)} цен:")

            for i, p in enumerate(prices_int[:15], 1):
                print(f"  {i}. {p:,} RUB".replace(",", " "))

            print(f"\n  Минимум: {min(prices_int):,} RUB".replace(",", " "))
            print(f"  Максимум: {max(prices_int):,} RUB".replace(",", " "))
            return prices_int
        else:
            print("[!] Цены не найдены в HTML")

            # Проверим на блокировку
            if "403" in html or "Forbidden" in html:
                print("[X] Страница заблокирована (403)")
            elif "captcha" in html.lower():
                print("[!] Обнаружена CAPTCHA")

            return []
    else:
        print(f"[!] HTML не сохранён")
        return []


def interactive_mode():
    """Интерактивный режим - qutebrowser остаётся открытым"""

    print("=" * 60)
    print("DNS-SHOP qutebrowser - интерактивный режим")
    print("=" * 60)
    print()
    print("qutebrowser откроется. Используйте:")
    print("  o - открыть URL")
    print("  / - поиск на странице")
    print("  :save-page /tmp/page.html - сохранить HTML")
    print("  :screenshot /tmp/screen.png - скриншот")
    print("  :quit - закрыть")
    print()

    url = "https://www.dns-shop.ru/"

    subprocess.run([
        "qutebrowser",
        "--temp-basedir",
        url
    ])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "-i":
            interactive_mode()
        else:
            query = " ".join(sys.argv[1:])
            dns_search_qute(query)
    else:
        print("Использование:")
        print(f"  {sys.argv[0]} 'MacBook Pro 16'  - автоматический поиск")
        print(f"  {sys.argv[0]} -i                - интерактивный режим")
        print()
        dns_search_qute("MacBook Pro 16")
