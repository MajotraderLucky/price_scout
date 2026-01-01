#!/usr/bin/env python3
"""
DNS-Shop через qutebrowser IPC

qutebrowser - реальный браузер с командным управлением.
Отправляем команды через CLI в запущенный экземпляр.

Использование:
1. Запусти qutebrowser вручную (или скрипт запустит)
2. Скрипт отправит команды через IPC
3. Страница сохранится, скрипт распарсит цены
"""

import subprocess
import time
import sys
import os
import re
from pathlib import Path

OUTPUT_DIR = Path("/tmp/dns_qute")
OUTPUT_DIR.mkdir(exist_ok=True)

HTML_FILE = OUTPUT_DIR / "dns_search.html"


def is_qutebrowser_running() -> bool:
    """Проверка запущен ли qutebrowser"""
    result = subprocess.run(
        ["pgrep", "-x", "qutebrowser"],
        capture_output=True
    )
    return result.returncode == 0


def send_qute_command(command: str) -> bool:
    """Отправка команды в qutebrowser"""
    try:
        # qutebrowser принимает команды через CLI
        result = subprocess.run(
            ["qutebrowser", f":{command}"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[!] Ошибка команды: {e}")
        return False


def start_qutebrowser(url: str = None):
    """Запуск qutebrowser"""
    cmd = ["qutebrowser"]
    if url:
        cmd.append(url)

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("[+] qutebrowser запущен")
    time.sleep(3)


def search_dns(query: str):
    """Поиск на DNS-Shop через qutebrowser"""

    print("=" * 60)
    print("DNS-SHOP via qutebrowser IPC")
    print("=" * 60)

    search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"

    # 1. Проверяем/запускаем qutebrowser
    if not is_qutebrowser_running():
        print("[*] qutebrowser не запущен, запускаю...")
        start_qutebrowser(search_url)
        print("[*] Жду загрузки страницы (10 сек)...")
        time.sleep(10)
    else:
        print("[+] qutebrowser уже запущен")
        print(f"[*] Открываю: {search_url}")
        send_qute_command(f"open {search_url}")
        time.sleep(8)

    # 2. Удаляем старый файл
    if HTML_FILE.exists():
        HTML_FILE.unlink()

    # 3. Сохраняем страницу
    print(f"[*] Сохраняю страницу в {HTML_FILE}")
    send_qute_command(f"save-page {HTML_FILE} plain")
    time.sleep(2)

    # 4. Парсим результат
    if HTML_FILE.exists():
        html = HTML_FILE.read_text(errors='ignore')
        print(f"[+] HTML получен: {len(html)} bytes")

        # Проверка на блокировку
        if "403" in html[:500] or "Forbidden" in html[:500]:
            print("[X] Страница заблокирована (403)")
            return []

        if "qrator" in html[:1000].lower():
            print("[!] Qrator challenge - страница не загрузилась")
            print("[*] Подожди пока qutebrowser пройдёт проверку и запусти снова")
            return []

        # Ищем цены
        prices = re.findall(r'data-product-price="(\d+)"', html)

        if prices:
            prices_int = sorted(set(int(p) for p in prices))
            print(f"\n[+] Найдено {len(prices_int)} уникальных цен:")

            for i, p in enumerate(prices_int[:15], 1):
                print(f"  {i}. {p:,} RUB".replace(",", " "))

            print(f"\n  Минимум: {min(prices_int):,} RUB".replace(",", " "))
            print(f"  Максимум: {max(prices_int):,} RUB".replace(",", " "))

            return prices_int
        else:
            print("[!] Цены не найдены")

            # Сохраним для анализа
            debug_file = OUTPUT_DIR / "debug.html"
            debug_file.write_text(html[:5000])
            print(f"[*] Первые 5000 символов сохранены в {debug_file}")

            return []
    else:
        print("[!] HTML файл не создан")
        print("[*] Попробуй вручную в qutebrowser:")
        print(f"    :save-page {HTML_FILE} plain")
        return []


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"

    print(f"Поиск: {query}")
    print()
    print("Если qutebrowser уже открыт с DNS-Shop,")
    print("скрипт сохранит текущую страницу и извлечёт цены.")
    print()

    prices = search_dns(query)

    if not prices:
        print("\n" + "=" * 60)
        print("Ручной режим:")
        print("1. Открой qutebrowser")
        print("2. Перейди на https://www.dns-shop.ru/search/?q=MacBook+Pro+16")
        print("3. Дождись загрузки (пройди Qrator если нужно)")
        print(f"4. Нажми : и введи: save-page {HTML_FILE} plain")
        print("5. Запусти этот скрипт снова")
