#!/usr/bin/env python3
"""
Поиск цены на MacBook Pro 16 2021 M1 Pro 32GB 512GB (Z14V0008D)

С верификацией товара:
- Проверка что это страница товара (не поиск/каталог)
- Проверка артикула
- Проверка ключевых характеристик (RAM, SSD, CPU)
"""

import re
import json
import time
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Optional, List

from duckduckgo_search import DDGS
from playwright.sync_api import sync_playwright, Page


@dataclass
class Product:
    """Целевой товар для поиска"""
    name: str
    article: str
    ram_gb: int
    ssd_gb: int
    cpu: str

    def get_search_query(self) -> str:
        return f"{self.article} купить цена"

    def get_verification_patterns(self) -> dict:
        """Паттерны для верификации товара (case-insensitive)"""
        return {
            "article": [self.article.lower()],
            "ram": [
                f"{self.ram_gb}gb", f"{self.ram_gb} gb",
                f"{self.ram_gb}гб", f"{self.ram_gb} гб",
                f"{self.ram_gb * 1024}",  # 32768 для 32GB
            ],
            "ssd": [
                f"{self.ssd_gb}gb", f"{self.ssd_gb} gb",
                f"{self.ssd_gb}гб", f"{self.ssd_gb} гб",
            ],
            "cpu": [self.cpu.lower(), self.cpu.lower().replace(" ", "")],
        }


@dataclass
class VerificationResult:
    """Результат верификации товара"""
    is_product_page: bool
    article_found: bool
    ram_found: bool
    ssd_found: bool
    cpu_found: bool
    page_title: str

    @property
    def is_verified(self) -> bool:
        """Товар верифицирован если все проверки пройдены"""
        return (
            self.is_product_page and
            self.article_found and
            self.ram_found and
            self.ssd_found and
            self.cpu_found
        )

    @property
    def score(self) -> int:
        """Оценка совпадения (0-5)"""
        return sum([
            self.is_product_page,
            self.article_found,
            self.ram_found,
            self.ssd_found,
            self.cpu_found,
        ])

    def __str__(self) -> str:
        checks = [
            ("Страница товара", self.is_product_page),
            ("Артикул", self.article_found),
            ("RAM", self.ram_found),
            ("SSD", self.ssd_found),
            ("CPU", self.cpu_found),
        ]
        lines = []
        for name, ok in checks:
            status = "[+]" if ok else "[X]"
            lines.append(f"  {status} {name}")
        return "\n".join(lines)


@dataclass
class PriceResult:
    """Результат поиска цены"""
    shop: str
    url: str
    price: Optional[int]
    availability: str
    verification: VerificationResult
    status: str  # OK, CAPTCHA, Blocked, Error, Not Verified


# Целевой товар
TARGET = Product(
    name="MacBook Pro 16 2021 M1 Pro 32GB 512GB",
    article="Z14V0008D",
    ram_gb=32,
    ssd_gb=512,
    cpu="M1 Pro",
)

# Известные рабочие URL (проверяются в первую очередь)
KNOWN_URLS = [
    "https://i-ray.ru/macbook/macbook-pro-16-m1-2021/10498",
]


def search_product(product: Product) -> List[dict]:
    """Поиск по артикулу через DuckDuckGo"""
    query = product.get_search_query()
    print(f"\n[ПОИСК] Запрос: '{query}'")

    with DDGS() as ddgs:
        results = list(ddgs.text(query, region="ru-ru", max_results=20))

    print(f"[ПОИСК] Найдено: {len(results)} результатов")
    return results


def is_product_page(html: str, title: str) -> bool:
    """Определить, является ли страница страницей товара"""

    # Признаки страницы поиска/каталога
    search_indicators = [
        "поиск по товарам",
        "результаты поиска",
        "search results",
        "найдено товаров",
        "показать ещё",
    ]

    title_lower = title.lower()
    html_lower = html.lower()

    for indicator in search_indicators:
        if indicator in title_lower or indicator in html_lower[:5000]:
            return False

    # Признаки страницы товара
    product_indicators = [
        'itemprop="product"',
        'itemtype="http://schema.org/Product"',
        '"@type":"Product"',
        '"@type": "Product"',
        'class="product-page"',
        'class="product-card"',
        'id="product-',
    ]

    for indicator in product_indicators:
        if indicator in html:
            return True

    # Проверяем наличие единственной цены (не списка)
    # На странице товара обычно 1-3 цены, на каталоге - много
    prices = re.findall(r'(\d{3}[\s\u00a0]?\d{3})\s*(?:₽|руб)', html)
    if 1 <= len(prices) <= 5:
        return True

    return False


def verify_product(html: str, title: str, product: Product) -> VerificationResult:
    """Верификация товара на странице (case-insensitive)"""

    patterns = product.get_verification_patterns()
    content = (html + " " + title).lower()  # Case-insensitive

    # Проверка типа страницы
    is_product = is_product_page(html, title)

    # Проверка артикула
    article_found = any(p in content for p in patterns["article"])

    # Проверка RAM
    ram_found = any(p in content for p in patterns["ram"])

    # Проверка SSD
    ssd_found = any(p in content for p in patterns["ssd"])

    # Проверка CPU
    cpu_found = any(p in content for p in patterns["cpu"])

    return VerificationResult(
        is_product_page=is_product,
        article_found=article_found,
        ram_found=ram_found,
        ssd_found=ssd_found,
        cpu_found=cpu_found,
        page_title=title[:60],
    )


def extract_price(html: str, min_price: int = 100000, max_price: int = 400000) -> Optional[int]:
    """Извлечь цену из HTML"""

    # Приоритет 1: Schema.org price
    match = re.search(r'itemprop="price"\s+content="(\d+)"', html)
    if match:
        price = int(match.group(1))
        if min_price < price < max_price:
            return price

    # Приоритет 2: JSON-LD
    for match in re.findall(r'"price"[:\s]*(\d+)', html):
        price = int(match)
        if min_price < price < max_price:
            return price

    # Приоритет 3: Текстовые цены (берём первую подходящую)
    for match in re.findall(r'(\d{3}[\s\u00a0]?\d{3})\s*(?:₽|руб)', html):
        clean = match.replace(" ", "").replace("\u00a0", "")
        if clean.isdigit():
            price = int(clean)
            if min_price < price < max_price:
                return price

    return None


def extract_availability(html: str) -> str:
    """Извлечь информацию о наличии"""
    html_lower = html.lower()

    if 'instock' in html_lower or 'in_stock' in html_lower:
        return "В наличии"
    elif 'soldout' in html_lower or 'outofstock' in html_lower or 'out_of_stock' in html_lower:
        return "Нет в наличии"
    elif 'preorder' in html_lower:
        return "Предзаказ"
    elif 'availability' in html_lower:
        # Попробуем найти текст наличия
        match = re.search(r'наличии|в наличии|есть в наличии', html_lower)
        if match:
            return "В наличии"

    return "Неизвестно"


def check_url(url: str, product: Product, browser) -> PriceResult:
    """Проверить URL и извлечь данные с верификацией"""

    domain = urlparse(url).netloc.replace('www.', '')
    page = browser.new_page()

    try:
        resp = page.goto(url, timeout=15000)

        if resp.status == 404:
            return PriceResult(
                shop=domain, url=url, price=None,
                availability="",
                verification=VerificationResult(False, False, False, False, False, "404 Not Found"),
                status="404 Not Found"
            )

        if resp.status != 200:
            return PriceResult(
                shop=domain, url=url, price=None,
                availability="",
                verification=VerificationResult(False, False, False, False, False, f"HTTP {resp.status}"),
                status=f"HTTP {resp.status}"
            )

        time.sleep(2)
        html = page.content()
        title = page.title()

        # Проверка защиты
        if 'captcha' in html.lower():
            return PriceResult(
                shop=domain, url=url, price=None,
                availability="",
                verification=VerificationResult(False, False, False, False, False, title),
                status="CAPTCHA"
            )

        if 'blocked' in html.lower() or 'access denied' in html.lower():
            return PriceResult(
                shop=domain, url=url, price=None,
                availability="",
                verification=VerificationResult(False, False, False, False, False, title),
                status="Blocked"
            )

        # Верификация товара
        verification = verify_product(html, title, product)

        if not verification.is_verified:
            return PriceResult(
                shop=domain, url=url, price=None,
                availability="",
                verification=verification,
                status=f"Not Verified (score: {verification.score}/5)"
            )

        # Извлечение данных
        price = extract_price(html)
        availability = extract_availability(html)

        return PriceResult(
            shop=domain, url=url,
            price=price,
            availability=availability,
            verification=verification,
            status="OK" if price else "No Price"
        )

    except Exception as e:
        return PriceResult(
            shop=domain, url=url, price=None,
            availability="",
            verification=VerificationResult(False, False, False, False, False, str(e)[:50]),
            status=f"Error: {type(e).__name__}"
        )

    finally:
        page.close()


def main():
    print("=" * 70)
    print(f"ПОИСК ЦЕНЫ: {TARGET.name}")
    print(f"Артикул: {TARGET.article}")
    print(f"Конфигурация: {TARGET.cpu} / {TARGET.ram_gb}GB / {TARGET.ssd_gb}GB SSD")
    print("=" * 70)

    # Шаг 1: Поиск
    results = search_product(TARGET)

    # Фильтрация - пропускаем маркетплейсы с CAPTCHA
    blocked_domains = ['yandex', 'ozon.ru', 'wildberries', 'avito', 'aliexpress']

    # Начинаем с известных рабочих URL
    urls_to_check = list(KNOWN_URLS)
    print(f"\n[ИЗВЕСТНЫЕ] Добавлено {len(KNOWN_URLS)} проверенных источников")

    # Добавляем URL из поиска
    for r in results:
        url = r.get('href', '')
        if any(x in url for x in blocked_domains):
            continue
        if TARGET.article.lower() in url.lower():
            if url not in urls_to_check:
                urls_to_check.append(url)

    print(f"[ФИЛЬТР] URL с артикулом (без маркетплейсов): {len(urls_to_check)}")

    # Шаг 2: Проверка каждого URL с верификацией
    print("\n" + "=" * 70)
    print("ПРОВЕРКА МАГАЗИНОВ (с верификацией товара)")
    print("=" * 70)

    all_results: List[PriceResult] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])

        for url in urls_to_check[:10]:
            domain = urlparse(url).netloc.replace('www.', '')

            print(f"\n[{domain}]")
            print(f"  URL: {url[:55]}...")

            result = check_url(url, TARGET, browser)
            all_results.append(result)

            print(f"  Статус: {result.status}")

            if result.status == "OK":
                print(f"  Цена: {result.price:,} ₽".replace(',', ' '))
                print(f"  Наличие: {result.availability}")
                print("  Верификация:")
                print(result.verification)
            elif "Not Verified" in result.status:
                print("  Верификация:")
                print(result.verification)

        browser.close()

    # Шаг 3: Результаты
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ")
    print("=" * 70)

    # Только верифицированные результаты с ценой
    verified = [r for r in all_results if r.status == "OK" and r.price]

    # Частично верифицированные
    partial = [r for r in all_results if "Not Verified" in r.status and r.verification.score >= 3]

    # Заблокированные
    blocked = [r for r in all_results if r.status in ("CAPTCHA", "Blocked")]

    if verified:
        verified.sort(key=lambda x: x.price)

        print(f"\n✓ Верифицированные предложения: {len(verified)}")
        print("-" * 70)

        for i, r in enumerate(verified, 1):
            stock = "[+]" if r.availability == "В наличии" else "[-]"
            print(f"{i}. {r.shop}: {r.price:,} ₽ {stock} {r.availability}".replace(',', ' '))

        print("\n" + "-" * 70)
        print(f"Минимальная цена: {verified[0].price:,} ₽ ({verified[0].shop})".replace(',', ' '))

    else:
        print("\n[!] Верифицированных предложений не найдено")

    if partial:
        print(f"\n? Частично совпадающие (проверьте вручную): {len(partial)}")
        for r in partial:
            print(f"  - {r.shop}: score {r.verification.score}/5")

    if blocked:
        print(f"\n✗ Заблокировано CAPTCHA: {len(blocked)}")
        for r in blocked:
            print(f"  - {r.shop}")

    # Сводка
    print("\n" + "=" * 70)
    print("СВОДКА")
    print("=" * 70)
    print(f"Проверено URL: {len(all_results)}")
    print(f"Верифицировано: {len(verified)}")
    print(f"CAPTCHA/Blocked: {len(blocked)}")
    print(f"Не прошли верификацию: {len(all_results) - len(verified) - len(blocked)}")


if __name__ == "__main__":
    main()
