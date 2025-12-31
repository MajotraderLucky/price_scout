#!/usr/bin/env python3
"""
Проверка IP-адреса и его репутации

Запустите этот скрипт на разных машинах чтобы понять,
какой IP подходит для парсинга.
"""

import requests
import json


def check_ip():
    """Проверить текущий IP и его характеристики"""

    print("=" * 60)
    print("ПРОВЕРКА IP-АДРЕСА")
    print("=" * 60)

    try:
        # Получаем информацию об IP
        resp = requests.get("https://ipinfo.io/json", timeout=10)
        data = resp.json()

        ip = data.get("ip", "Unknown")
        hostname = data.get("hostname", "Unknown")
        org = data.get("org", "Unknown")
        city = data.get("city", "Unknown")
        country = data.get("country", "Unknown")

        print(f"\nIP: {ip}")
        print(f"Hostname: {hostname}")
        print(f"Organization: {org}")
        print(f"Location: {city}, {country}")

        # Анализ типа IP
        print("\n" + "-" * 60)
        print("АНАЛИЗ")
        print("-" * 60)

        # Признаки датацентра
        datacenter_keywords = [
            "hosting", "server", "cloud", "vps", "dedicated",
            "datacenter", "data center", "hetzner", "ovh",
            "digitalocean", "aws", "amazon", "google", "azure",
            "linode", "vultr", "majordomo", "reg.ru"
        ]

        hostname_lower = hostname.lower() if hostname else ""
        org_lower = org.lower() if org else ""

        is_datacenter = any(
            kw in hostname_lower or kw in org_lower
            for kw in datacenter_keywords
        )

        if is_datacenter:
            print("[X] Тип: ДАТАЦЕНТР")
            print("    Этот IP будет заблокирован большинством магазинов")
            print("    Рекомендация: используйте домашний/мобильный IP")
        else:
            print("[+] Тип: Вероятно РЕЗИДЕНТНЫЙ")
            print("    Этот IP подходит для парсинга")

        # Проверка ASN
        asn = org.split()[0] if org else ""
        if asn.startswith("AS"):
            print(f"\nASN: {asn}")
            print(f"    Проверьте репутацию: https://bgp.he.net/{asn}")

        return {
            "ip": ip,
            "is_datacenter": is_datacenter,
            "org": org,
            "country": country,
        }

    except Exception as e:
        print(f"[!] Ошибка: {e}")
        return None


def main():
    result = check_ip()

    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ")
    print("=" * 60)

    if result and result["is_datacenter"]:
        print("""
Для обхода защиты магазинов (Citilink, DNS) нужен резидентный IP:

1. ДОМАШНИЙ ПК
   - Скопируйте скрипты на домашний компьютер
   - pip install playwright duckduckgo-search beautifulsoup4
   - playwright install chromium
   - python find_macbook_price.py

2. МОБИЛЬНЫЙ ИНТЕРНЕТ
   - Раздайте интернет с телефона
   - Запустите скрипты через мобильную сеть

3. VPN с резидентными IP (платно)
   - Mullvad, Surfshark (некоторые серверы)
""")
    else:
        print("""
Ваш IP подходит для парсинга!
Запустите: python find_macbook_price.py
""")


if __name__ == "__main__":
    main()
