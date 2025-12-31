#!/usr/bin/env python3
"""
Парсинг через локальный интерфейс (минуя VPN)

Для работы требуется временно отключить VPN или добавить маршруты.
"""

import re
import subprocess
import sys
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def check_ip_via_interface(interface: str = "wlo1") -> dict:
    """Проверить IP через конкретный интерфейс"""
    try:
        result = subprocess.run(
            ["curl", "-s", "--interface", interface, "https://ipinfo.io/json"],
            capture_output=True, text=True, timeout=10
        )
        import json
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


def fetch_via_interface(url: str, interface: str = "wlo1") -> Optional[str]:
    """Загрузить страницу через локальный интерфейс (curl)"""
    try:
        result = subprocess.run(
            [
                "curl", "-s",
                "--interface", interface,
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "-H", "Accept-Language: ru-RU,ru;q=0.9",
                url
            ],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception as e:
        print(f"[!] Ошибка: {e}")
        return None


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


def check_captcha(html: str) -> bool:
    """Проверить наличие CAPTCHA"""
    html_lower = html.lower()
    return any(x in html_lower for x in ["captcha", "каптча", "robot", "challenge"])


def parse_citilink_search(query: str, interface: str = "wlo1") -> list:
    """Поиск товара на Citilink"""

    url = f"https://www.citilink.ru/search/?text={query}"
    print(f"\n[Citilink] Поиск: {query}")
    print(f"  URL: {url}")

    html = fetch_via_interface(url, interface)
    if not html:
        return []

    if check_captcha(html):
        print("  [X] CAPTCHA!")
        return []

    # Парсим JSON из __NEXT_DATA__
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html)
    if not match:
        print("  [-] Данные не найдены")
        return []

    import json
    try:
        data = json.loads(match.group(1))
        products = data.get("props", {}).get("pageProps", {}).get("effectorValues", {})

        # Ищем массив products в данных
        results = []
        for key, value in products.items():
            if isinstance(value, dict) and "products" in value:
                for product in value.get("products", [])[:5]:
                    name = product.get("name", "")
                    price_data = product.get("price", {})
                    price = price_data.get("price", 0)

                    if price > 0:
                        results.append({
                            "name": name[:60],
                            "price": price,
                            "available": product.get("isAvailable", False),
                        })

        if results:
            print(f"  [+] Найдено: {len(results)} товаров")
            return results

    except json.JSONDecodeError:
        pass

    print("  [-] Товары не найдены")
    return []


def parse_dns_search(query: str, interface: str = "wlo1") -> list:
    """Поиск товара на DNS-Shop"""

    url = f"https://www.dns-shop.ru/search/?q={query}"
    print(f"\n[DNS-Shop] Поиск: {query}")
    print(f"  URL: {url}")

    html = fetch_via_interface(url, interface)
    if not html:
        return []

    if check_captcha(html):
        print("  [X] CAPTCHA!")
        return []

    # Простой парсинг
    soup = BeautifulSoup(html, 'html.parser')

    # Ищем цены
    prices = []
    for match in re.findall(r'(\d{3}[\s\u00a0]?\d{3})[\s\u00a0]*(?:₽|руб)', html):
        clean = match.replace(" ", "").replace("\u00a0", "")
        if clean.isdigit():
            price = int(clean)
            if 50000 < price < 400000:
                prices.append(price)

    if prices:
        print(f"  [+] Найдено цен: {len(prices)}")
        return [{"price": p} for p in prices[:5]]

    print("  [-] Цены не найдены")
    return []


def main():
    print("=" * 60)
    print("ПАРСИНГ ЧЕРЕЗ ЛОКАЛЬНЫЙ IP (минуя VPN)")
    print("=" * 60)

    # Проверяем IP
    print("\n[1] Проверка IP-адресов")
    print("-" * 40)

    # VPN IP
    try:
        vpn_ip = requests.get("https://ipinfo.io/json", timeout=5).json()
        print(f"VPN (default):  {vpn_ip.get('ip')} ({vpn_ip.get('org', 'Unknown')})")
    except:
        print("VPN (default):  Недоступен")

    # Local IP
    local_ip = check_ip_via_interface("wlo1")
    if "error" not in local_ip:
        print(f"Local (wlo1):   {local_ip.get('ip')} ({local_ip.get('org', 'Unknown')})")
    else:
        print(f"Local (wlo1):   Ошибка - {local_ip.get('error')}")
        sys.exit(1)

    # Поиск
    query = "MacBook Pro 16 M1 Pro"

    print("\n[2] Поиск товаров")
    print("-" * 40)

    # Citilink
    citilink_results = parse_citilink_search(query)

    # DNS
    dns_results = parse_dns_search(query)

    # Результаты
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 60)

    if citilink_results:
        print("\nCitilink:")
        for r in citilink_results[:3]:
            status = "[+]" if r.get("available") else "[-]"
            print(f"  {r['price']:,} ₽ {status} {r.get('name', '')[:40]}...".replace(",", " "))

    if dns_results:
        print("\nDNS-Shop:")
        for r in dns_results[:3]:
            print(f"  {r['price']:,} ₽".replace(",", " "))


if __name__ == "__main__":
    main()
