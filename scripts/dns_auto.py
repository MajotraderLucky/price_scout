#!/usr/bin/env python3
"""
DNS-Shop полная автоматизация через qutebrowser

Автоматически:
1. Запускает qutebrowser с нужным URL
2. Ждёт загрузки страницы
3. Сохраняет HTML через userscript
4. Парсит цены
"""

import subprocess
import socket
import json
import time
import sys
import os
import re
from pathlib import Path

OUTPUT_DIR = Path("/tmp/dns_qute")
OUTPUT_DIR.mkdir(exist_ok=True)


def get_qute_socket() -> str | None:
    """Найти IPC сокет qutebrowser"""
    # Проверяем несколько возможных мест
    locations = [
        Path(f"/run/user/{os.getuid()}/qutebrowser"),
        Path.home() / ".local/share/qutebrowser/runtime",
        Path("/tmp"),
    ]

    for loc in locations:
        if loc.exists():
            sockets = list(loc.glob("**/ipc-*"))
            if sockets:
                return str(sockets[0])

    # Поиск во всех temp директориях
    import glob
    for pattern in ["/tmp/qutebrowser-*/runtime/ipc-*", "/tmp/**/qutebrowser**/ipc-*"]:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]

    return None


def send_to_qute(args: list) -> bool:
    """Отправить команду в qutebrowser через IPC"""
    sock_path = get_qute_socket()
    if not sock_path:
        return False

    msg = {
        "args": args,
        "target_arg": None,
        "version": "3.0.0",
        "protocol_version": 1,
        "cwd": str(Path.cwd())
    }

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock_path)
        s.send(json.dumps(msg).encode() + b'\n')
        s.close()
        return True
    except Exception as e:
        print(f"[!] IPC ошибка: {e}")
        return False


def is_qute_running() -> bool:
    """Проверка запущен ли qutebrowser"""
    result = subprocess.run(["pgrep", "-x", "qutebrowser"], capture_output=True)
    return result.returncode == 0


def start_qutebrowser(url: str):
    """Запуск qutebrowser (без temp-basedir чтобы userscripts работали)"""
    subprocess.Popen(
        ["qutebrowser", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def get_latest_html() -> Path | None:
    """Получить последний сохранённый HTML"""
    files = sorted(OUTPUT_DIR.glob("page_*.html"), key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0] if files else None


def parse_prices(html: str) -> list:
    """Извлечь цены из HTML"""
    prices = re.findall(r'data-product-price="(\d+)"', html)
    return sorted(set(int(p) for p in prices))


def dns_search(query: str):
    """Главная функция поиска"""

    print("=" * 60)
    print("DNS-SHOP AUTO (qutebrowser)")
    print("=" * 60)

    search_url = f"https://www.dns-shop.ru/search/?q={query.replace(' ', '+')}"
    print(f"[*] Запрос: {query}")
    print(f"[*] URL: {search_url}")

    # Очищаем старые файлы
    for f in OUTPUT_DIR.glob("page_*.html"):
        f.unlink()

    # Запускаем/открываем URL
    if is_qute_running():
        print("[+] qutebrowser запущен, открываю URL...")
        send_to_qute([search_url])
    else:
        print("[*] Запускаю qutebrowser...")
        start_qutebrowser(search_url)

    # Ждём загрузки
    print("[*] Ожидание загрузки страницы (15 сек)...")
    time.sleep(15)

    # Сохранение через JavaScript - получаем DOM как есть в браузере
    print("[*] Сохранение страницы через JS...")

    output_file = OUTPUT_DIR / f"page_{int(time.time())}.html"

    # JavaScript для сохранения HTML
    js_code = f'''
        (function() {{
            var html = document.documentElement.outerHTML;
            var blob = new Blob([html], {{type: 'text/html'}});
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'page.html';
            a.click();
        }})();
    '''

    # Отправляем команду jseval
    if send_to_qute([f":jseval {js_code}"]):
        print("[+] JS команда отправлена")
        print("[*] Файл должен скачаться в ~/Downloads/page.html")
    else:
        print("[!] Не удалось отправить JS команду")

    time.sleep(3)

    # Проверяем Downloads
    downloads = Path.home() / "Downloads"
    page_files = list(downloads.glob("page*.html"))
    if page_files:
        latest = max(page_files, key=lambda x: x.stat().st_mtime)
        # Копируем в наш каталог
        import shutil
        shutil.copy(latest, output_file)
        print(f"[+] Скопирован: {output_file}")

    # Проверяем результат
    html_file = get_latest_html()

    if html_file:
        html = html_file.read_text(errors='ignore')
        print(f"[+] HTML: {len(html)} bytes")

        # Проверки
        if len(html) < 1000:
            print("[!] Файл слишком маленький")
            return []

        if "qrator" in html[:2000].lower() and "<script" in html[:500]:
            print("[!] Qrator challenge - страница не загрузилась полностью")
            print("[*] Подожди и попробуй снова")
            return []

        if "403" in html[:500] or "Forbidden" in html[:500]:
            print("[X] Заблокировано (403)")
            return []

        # Парсим цены
        prices = parse_prices(html)

        if prices:
            print(f"\n[+] Найдено {len(prices)} цен:")
            for i, p in enumerate(prices[:15], 1):
                print(f"  {i}. {p:,} RUB".replace(",", " "))
            print(f"\n  Мин: {min(prices):,} RUB".replace(",", " "))
            print(f"  Макс: {max(prices):,} RUB".replace(",", " "))
            return prices
        else:
            print("[!] Цены не найдены в HTML")
            print("[*] Первые 500 символов:")
            print(html[:500])
            return []
    else:
        print("[!] HTML файл не найден")
        print("[*] Userscript не сработал")
        print("[*] Проверь: ~/.local/share/qutebrowser/userscripts/save_page")
        return []


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MacBook Pro 16"
    dns_search(query)
