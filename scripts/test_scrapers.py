#!/usr/bin/env python3
"""
Price Scout - Scraper Test System

Тестирует все методы извлечения данных:
1. Playwright Direct - простые магазины
2. Playwright Stealth - магазины с защитой
3. Firefox + xdotool - сложная защита (DNS-Shop)

Использование:
    python test_scrapers.py           # Все тесты
    python test_scrapers.py --quick   # Быстрые тесты (без Firefox)
    python test_scrapers.py --store kns  # Один магазин
"""

import re
import sys
import json
import time
import random
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, Page
from playwright_stealth import Stealth


# === Конфигурация тестов ===

TEST_ARTICLE = "Z14V0008D"
TEST_PRODUCT = "MacBook Pro 16 M1 Pro 32GB 512GB"

# Ожидаемый диапазон цен для валидации
MIN_EXPECTED_PRICE = 80000
MAX_EXPECTED_PRICE = 300000

# Таймауты
PAGE_TIMEOUT = 30000
FIREFOX_TIMEOUT = 90  # Увеличен для Firefox + xvfb-run


# === Dataclasses ===

@dataclass
class TestResult:
    """Результат теста"""
    store: str
    method: str
    status: str  # PASS, FAIL, SKIP, ERROR
    price: Optional[int] = None
    available: Optional[bool] = None
    response_time: float = 0.0
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


@dataclass
class StoreConfig:
    """Конфигурация магазина"""
    name: str
    method: str  # playwright_direct, playwright_stealth, firefox
    search_url: str
    parser: str = "generic"  # generic, nextjs, dns_json
    url_type: str = "search"  # search, product
    lowercase: bool = False
    delay: int = 0
    validate_price: bool = True


# === Конфигурация магазинов ===

STORES: List[StoreConfig] = [
    StoreConfig(
        name="i-ray",
        method="playwright_direct",
        search_url="https://i-ray.ru/search?q={query}",
    ),
    StoreConfig(
        name="regard",
        method="playwright_stealth",
        search_url="https://www.regard.ru/catalog?search={query}",
    ),
    StoreConfig(
        name="kns",
        method="playwright_direct",
        search_url="https://www.kns.ru/product/noutbuk-apple-macbook-pro-16-2021-{query}/",
        url_type="product",
        lowercase=True,
    ),
    StoreConfig(
        name="nix",
        method="playwright_direct",
        search_url="https://www.nix.ru/autocatalog/apple_notebook/{query}-Noutbuk-Apple-MacBook-Pro-162-Apple-M1-Pro-10-core-32GB-512GB-SSD-Mac-OS-{query}-seryj-kosmos_574636.html",
        url_type="product",
    ),
    StoreConfig(
        name="citilink",
        method="citilink_special",  # Специальный метод с увеличенной задержкой
        search_url="https://www.citilink.ru/search/?text=MacBook+Pro+16",
        parser="citilink",
        delay=8,  # Увеличенная задержка для обхода rate limit
    ),
    StoreConfig(
        name="dns",
        method="firefox",
        search_url="https://www.dns-shop.ru/catalog/recipe/b70b01357dbede01/apple-macbook-pro/",
        parser="dns_json",
    ),
    StoreConfig(
        name="yandex_market",
        method="yandex_market_special",
        search_url="https://market.yandex.ru/search?text=MacBook+Pro+16",
        parser="yandex_market",
        delay=5,
    ),
    StoreConfig(
        name="ozon",
        method="ozon_firefox",
        search_url="https://www.ozon.ru/search/?text=MacBook+Pro+16&from_global=true",
        parser="ozon_json",
    ),
    StoreConfig(
        name="avito",
        method="avito_firefox",
        search_url="https://www.avito.ru/rossiya/noutbuki?q=MacBook+Pro+16",
        parser="avito_json",
    ),
]


# === User Agents ===

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
]


# === Утилиты ===

def format_price(price: Optional[int]) -> str:
    if price is None:
        return "N/A"
    return f"{price:,}".replace(",", " ") + " RUB"


def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    time.sleep(random.uniform(min_sec, max_sec))


def human_scroll(page: Page):
    for _ in range(random.randint(2, 3)):
        page.mouse.wheel(0, random.randint(100, 300))
        time.sleep(random.uniform(0.2, 0.5))


# === Парсеры ===

def extract_price(html: str) -> Optional[int]:
    """Извлечь цену из HTML"""

    # Schema.org
    match = re.search(r'itemprop="price"\s+content="(\d+)"', html)
    if match:
        price = int(match.group(1))
        if MIN_EXPECTED_PRICE < price < MAX_EXPECTED_PRICE:
            return price

    # data-meta-price (Citilink)
    match = re.search(r'data-meta-price="(\d+)"', html)
    if match:
        price = int(match.group(1))
        if MIN_EXPECTED_PRICE < price < MAX_EXPECTED_PRICE:
            return price

    # JSON-LD
    for match in re.findall(r'"price"[:\s]*(\d+)', html):
        price = int(match)
        if MIN_EXPECTED_PRICE < price < MAX_EXPECTED_PRICE:
            return price

    # Text patterns
    for match in re.findall(r'(\d{2,3}[\s\u00a0]?\d{3})[\s\u00a0]*(?:₽|руб|RUB)', html):
        clean = match.replace(" ", "").replace("\u00a0", "")
        if clean.isdigit():
            price = int(clean)
            if MIN_EXPECTED_PRICE < price < MAX_EXPECTED_PRICE:
                return price

    return None


def extract_availability(html: str) -> Optional[bool]:
    """Извлечь наличие"""
    html_lower = html.lower()

    if any(x in html_lower for x in ['instock', 'in_stock', '"availability":"instock"', 'isavailable":true']):
        return True
    if any(x in html_lower for x in ['outofstock', 'out_of_stock', 'soldout', 'isavailable":false']):
        return False
    if 'в наличии' in html_lower:
        return True
    if 'нет в наличии' in html_lower:
        return False

    return None


def parse_avito(html: str) -> Optional[Dict]:
    """Парсинг Avito (Schema.org)"""
    prices = []

    # Schema.org itemProp/itemprop="price" content="..." (case-insensitive)
    for match in re.findall(r'itemprop="price"\s+content="(\d+)"', html, re.IGNORECASE):
        price = int(match)
        # Avito: б/у товары, широкий диапазон 30K-400K
        if 30000 < price < 400000:
            prices.append(price)

    if prices:
        # Фильтруем только MacBook Pro 16 цены (от 80K)
        macbook_prices = [p for p in prices if p >= 80000]
        if macbook_prices:
            return {
                "price": min(macbook_prices),
                "available": True,
                "count": len(macbook_prices),
            }
        # Fallback: любая цена
        return {
            "price": min(prices),
            "available": True,
            "count": len(prices),
        }

    return None


def parse_citilink_nextjs(html: str) -> Optional[Dict]:
    """Парсинг Citilink Next.js"""
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        html
    )

    if match:
        try:
            data = json.loads(match.group(1))
            props = data.get("props", {}).get("pageProps", {}).get("effectorValues", {})

            for key, value in props.items():
                if isinstance(value, dict) and "products" in value:
                    for item in value["products"][:1]:
                        return {
                            "price": item.get("price", {}).get("price", 0),
                            "available": item.get("isAvailable", False),
                            "name": item.get("name", ""),
                        }
        except json.JSONDecodeError:
            pass

    # Fallback
    prices = re.findall(r'data-meta-price="(\d+)"', html)
    if prices:
        return {"price": int(prices[0]), "available": True, "name": ""}

    return None


def parse_dns_json(json_path: str) -> Optional[Dict]:
    """Парсинг DNS-Shop JSON"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        catalog = data.get("catalog", {})
        if catalog.get("low_price"):
            return {
                "price": catalog["low_price"],
                "available": True,
                "name": catalog.get("name", ""),
                "count": catalog.get("count", 0),
            }
    except Exception:
        pass

    return None


def parse_avito_json(json_path: str) -> Optional[Dict]:
    """Парсинг Avito JSON"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = data.get("products", [])
        if products:
            prices = [p["price"] for p in products if p.get("price")]
            if prices:
                return {
                    "price": min(prices),
                    "available": True,
                    "count": len(products),
                }
    except Exception:
        pass

    return None


def parse_ozon_json(json_path: str) -> Optional[Dict]:
    """Парсинг Ozon JSON"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = data.get("products", [])
        if products:
            prices = [p["price"] for p in products if p.get("price")]
            if prices:
                return {
                    "price": min(prices),
                    "available": True,
                    "count": len(products),
                }
    except Exception:
        pass

    return None


# === Тестовые методы ===

def test_playwright_direct(store: StoreConfig, query: str) -> TestResult:
    """Тест через Playwright (прямой)"""
    start_time = time.time()
    result = TestResult(store=store.name, method="playwright_direct", status="ERROR")

    # Формируем URL
    q = query.lower() if store.lowercase else query
    if store.url_type == "product":
        url = store.search_url.format(query=q)
    else:
        url = store.search_url.format(query=quote_plus(query))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                locale="ru-RU",
                timezone_id="Europe/Moscow",
            )

            page = context.new_page()

            response = page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            result.details["http_status"] = response.status

            if response.status != 200:
                result.status = "FAIL"
                result.error = f"HTTP {response.status}"
                return result

            random_delay(2, 3)
            html = page.content()

            # Проверка CAPTCHA
            if "captcha" in html.lower():
                result.status = "FAIL"
                result.error = "CAPTCHA detected"
                return result

            # Извлечение данных
            result.price = extract_price(html)
            result.available = extract_availability(html)

            if result.price:
                result.status = "PASS"
            else:
                result.status = "FAIL"
                result.error = "No price found"

            context.close()
            browser.close()

    except Exception as e:
        result.status = "ERROR"
        result.error = f"{type(e).__name__}: {str(e)[:50]}"

    result.response_time = time.time() - start_time
    return result


def test_playwright_stealth(store: StoreConfig, query: str) -> TestResult:
    """Тест через Playwright Stealth"""
    start_time = time.time()
    result = TestResult(store=store.name, method="playwright_stealth", status="ERROR")

    # Формируем URL
    q = query.lower() if store.lowercase else query
    if store.url_type == "product":
        url = store.search_url.format(query=q)
    else:
        url = store.search_url.format(query=quote_plus(query))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ]
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                locale="ru-RU",
                timezone_id="Europe/Moscow",
            )

            page = context.new_page()

            # Stealth patches
            stealth = Stealth(
                navigator_languages_override=("ru-RU", "ru"),
                navigator_platform_override="Win32",
            )
            stealth.apply_stealth_sync(page)

            # Delay если нужно
            if store.delay > 0:
                time.sleep(store.delay)

            response = page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            result.details["http_status"] = response.status

            if response.status == 429:
                result.status = "FAIL"
                result.error = "Rate limited (429)"
                return result

            if response.status != 200:
                result.status = "FAIL"
                result.error = f"HTTP {response.status}"
                return result

            random_delay(2, 4)
            human_scroll(page)
            random_delay(1, 2)

            html = page.content()

            # Проверка CAPTCHA (исключаем Avito - там слово captcha в коде)
            if store.name != "avito":
                if "captcha" in html.lower() or "showcaptcha" in page.url.lower():
                    result.status = "FAIL"
                    result.error = "CAPTCHA detected"
                    return result

            # Парсинг в зависимости от типа
            if store.parser == "nextjs":
                parsed = parse_citilink_nextjs(html)
                if parsed:
                    result.price = parsed["price"]
                    result.available = parsed["available"]
            elif store.parser == "avito":
                parsed = parse_avito(html)
                if parsed:
                    result.price = parsed["price"]
                    result.available = parsed["available"]
                    result.details["count"] = parsed.get("count", 0)
            else:
                result.price = extract_price(html)
                result.available = extract_availability(html)

            if result.price:
                result.status = "PASS"
            else:
                result.status = "FAIL"
                result.error = "No price found"

            context.close()
            browser.close()

    except Exception as e:
        result.status = "ERROR"
        result.error = f"{type(e).__name__}: {str(e)[:50]}"

    result.response_time = time.time() - start_time
    return result


def test_citilink_special(store: StoreConfig, query: str) -> TestResult:
    """Специальный тест для Citilink с увеличенной задержкой и retry при 429"""
    start_time = time.time()
    result = TestResult(store=store.name, method="citilink_special", status="ERROR")

    url = store.search_url  # URL уже полный, без подстановки
    max_retries = 3
    retry_delay = 30  # секунд между попытками при 429

    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )

                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=random.choice(USER_AGENTS),
                    locale="ru-RU",
                    timezone_id="Europe/Moscow",
                )

                page = context.new_page()

                # Stealth patches
                stealth = Stealth(
                    navigator_languages_override=("ru-RU", "ru"),
                    navigator_platform_override="Win32",
                )
                stealth.apply_stealth_sync(page)

                # Начальная задержка перед запросом (увеличивается с каждой попыткой)
                initial_delay = 3 + (attempt * 5)
                random_delay(initial_delay, initial_delay + 3)

                response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                result.details["http_status"] = response.status
                result.details["attempt"] = attempt + 1

                if response.status == 429:
                    context.close()
                    browser.close()
                    if attempt < max_retries - 1:
                        print(f"    [!] 429 Rate Limited, waiting {retry_delay}s before retry...")
                        time.sleep(retry_delay)
                        retry_delay += 15  # Увеличиваем задержку с каждой попыткой
                        continue
                    else:
                        result.status = "FAIL"
                        result.error = f"Rate limited (429) after {max_retries} attempts"
                        return result

                if response.status != 200:
                    result.status = "FAIL"
                    result.error = f"HTTP {response.status}"
                    context.close()
                    browser.close()
                    return result

                # Увеличенная задержка для загрузки контента
                random_delay(5, 8)

                # Прокрутка для загрузки lazy content
                human_scroll(page)
                random_delay(2, 3)

                # Ожидание карточек товаров
                try:
                    page.wait_for_selector('[data-meta-price]', timeout=15000)
                except Exception:
                    pass  # Продолжаем даже если не нашли

                html = page.content()

                # Проверка CAPTCHA (только реальные блокировки, не упоминания в скриптах)
                if "showcaptcha" in page.url.lower() or "challenge-platform" in html.lower():
                    result.status = "FAIL"
                    result.error = "CAPTCHA detected"
                    context.close()
                    browser.close()
                    return result

                # Извлечение цен через JavaScript
                try:
                    prices = page.evaluate("""
                        () => {
                            const items = [];
                            document.querySelectorAll('[data-meta-price]').forEach(el => {
                                const price = parseInt(el.getAttribute('data-meta-price'));
                                if (price > 80000 && price < 400000) {
                                    items.push(price);
                                }
                            });
                            return items;
                        }
                    """)

                    if prices:
                        result.price = min(prices)
                        result.available = True
                        result.details["prices_found"] = len(prices)
                        result.details["price_range"] = f"{min(prices):,} - {max(prices):,}"
                except Exception:
                    pass

                # Fallback: regex
                if not result.price:
                    for match in re.findall(r'data-meta-price="(\d+)"', html):
                        p = int(match)
                        if 80000 < p < 400000:
                            result.price = p
                            result.available = True
                            break

                if result.price:
                    result.status = "PASS"
                else:
                    result.status = "FAIL"
                    result.error = "No price found"

                context.close()
                browser.close()
                break  # Успешная попытка - выходим из цикла

        except Exception as e:
            result.status = "ERROR"
            result.error = f"{type(e).__name__}: {str(e)[:50]}"
            if attempt < max_retries - 1:
                time.sleep(10)
                continue
            break

    result.response_time = time.time() - start_time
    return result


def test_ozon_firefox(store: StoreConfig, query: str) -> TestResult:
    """Тест через Firefox + xdotool (Ozon)"""
    start_time = time.time()
    result = TestResult(store=store.name, method="ozon_firefox", status="ERROR")

    script_path = Path(__file__).parent / "ozon_scraper.sh"
    output_dir = Path("/tmp/ozon_scraper_test")

    if not script_path.exists():
        result.status = "SKIP"
        result.error = "ozon_scraper.sh not found"
        return result

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        import os
        env = os.environ.copy()
        env.pop("DISPLAY", None)
        env.pop("XVFB_RUNNING", None)

        proc = subprocess.run(
            ["bash", str(script_path), "macbook-pro-16", str(output_dir)],
            capture_output=True,
            text=True,
            timeout=FIREFOX_TIMEOUT,
            env=env
        )

        result.details["returncode"] = proc.returncode

        if proc.returncode != 0:
            if "Saved:" in proc.stdout or "JSON:" in proc.stdout:
                pass
            else:
                result.status = "FAIL"
                result.error = f"Script failed: {proc.stderr[:100] if proc.stderr else proc.stdout[:100]}"
                return result

        json_files = list(output_dir.glob("*.json"))
        if not json_files:
            result.status = "FAIL"
            result.error = "No JSON output"
            return result

        latest = max(json_files, key=lambda x: x.stat().st_mtime)
        parsed = parse_ozon_json(str(latest))

        if parsed and parsed.get("price"):
            result.price = parsed["price"]
            result.available = parsed.get("available")
            result.details["products_count"] = parsed.get("count", 0)
            result.status = "PASS"
        else:
            result.status = "FAIL"
            result.error = "Failed to parse JSON"

    except subprocess.TimeoutExpired:
        result.status = "FAIL"
        result.error = f"Timeout ({FIREFOX_TIMEOUT}s)"
    except Exception as e:
        result.status = "ERROR"
        result.error = f"{type(e).__name__}: {str(e)[:50]}"

    result.response_time = time.time() - start_time
    return result


def test_avito_firefox(store: StoreConfig, query: str) -> TestResult:
    """Тест через Firefox + xdotool (Avito)"""
    start_time = time.time()
    result = TestResult(store=store.name, method="avito_firefox", status="ERROR")

    script_path = Path(__file__).parent / "avito_scraper.sh"
    output_dir = Path("/tmp/avito_scraper_test")

    if not script_path.exists():
        result.status = "SKIP"
        result.error = "avito_scraper.sh not found"
        return result

    try:
        # Создаём директорию
        output_dir.mkdir(parents=True, exist_ok=True)

        # Получаем текущее окружение и модифицируем
        import os
        env = os.environ.copy()
        # Удаляем DISPLAY чтобы скрипт сам запустил xvfb-run
        env.pop("DISPLAY", None)
        env.pop("XVFB_RUNNING", None)

        # Запускаем скрипт
        proc = subprocess.run(
            ["bash", str(script_path), "macbook-pro-16", str(output_dir)],
            capture_output=True,
            text=True,
            timeout=FIREFOX_TIMEOUT,
            env=env
        )

        result.details["returncode"] = proc.returncode

        if proc.returncode != 0:
            # Проверяем есть ли частичный вывод
            if "Сохранено:" in proc.stdout or "JSON:" in proc.stdout:
                pass  # Продолжаем парсить
            else:
                result.status = "FAIL"
                result.error = f"Script failed: {proc.stderr[:100] if proc.stderr else proc.stdout[:100]}"
                return result

        # Ищем JSON файл
        json_files = list(output_dir.glob("*.json"))
        if not json_files:
            result.status = "FAIL"
            result.error = "No JSON output"
            return result

        # Парсим последний файл
        latest = max(json_files, key=lambda x: x.stat().st_mtime)
        parsed = parse_avito_json(str(latest))

        if parsed and parsed.get("price"):
            result.price = parsed["price"]
            result.available = parsed.get("available")
            result.details["products_count"] = parsed.get("count", 0)
            result.status = "PASS"
        else:
            result.status = "FAIL"
            result.error = "Failed to parse JSON"

    except subprocess.TimeoutExpired:
        result.status = "FAIL"
        result.error = f"Timeout ({FIREFOX_TIMEOUT}s)"
    except Exception as e:
        result.status = "ERROR"
        result.error = f"{type(e).__name__}: {str(e)[:50]}"

    result.response_time = time.time() - start_time
    return result


def test_yandex_market_special(store: StoreConfig, query: str) -> TestResult:
    """Специальный тест для Yandex Market"""
    start_time = time.time()
    result = TestResult(store=store.name, method="yandex_market_special", status="ERROR")

    url = store.search_url

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ]
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                locale="ru-RU",
                timezone_id="Europe/Moscow",
            )

            page = context.new_page()

            # Stealth patches
            stealth = Stealth(
                navigator_languages_override=("ru-RU", "ru"),
                navigator_platform_override="Win32",
            )
            stealth.apply_stealth_sync(page)

            # Начальная задержка
            random_delay(3, 5)

            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            result.details["http_status"] = response.status

            if response.status != 200:
                result.status = "FAIL"
                result.error = f"HTTP {response.status}"
                return result

            # Ожидание загрузки контента
            random_delay(5, 8)

            # Скролл для lazy loading
            human_scroll(page)
            random_delay(2, 3)

            # Проверка CAPTCHA
            if "showcaptcha" in page.url.lower() or "captcha" in page.url.lower():
                result.status = "FAIL"
                result.error = "CAPTCHA detected"
                return result

            # Извлечение цен через JavaScript
            try:
                prices = page.evaluate("""
                    () => {
                        const items = [];
                        // Попробуем разные селекторы
                        const selectors = [
                            '[data-baobab-name="price"]',
                            '[data-auto="price-value"]',
                            '[data-zone-name="price"]'
                        ];

                        for (const selector of selectors) {
                            document.querySelectorAll(selector).forEach(el => {
                                const text = el.textContent || '';
                                // Удаляем все виды пробелов и получаем число
                                const clean = text.replace(/[^0-9]/g, '');
                                if (clean) {
                                    const price = parseInt(clean);
                                    if (price > 80000 && price < 500000) {
                                        items.push(price);
                                    }
                                }
                            });
                        }
                        return items;
                    }
                """)

                if prices:
                    result.price = min(prices)
                    result.available = True
                    result.details["prices_found"] = len(prices)
                    result.details["price_range"] = f"{min(prices):,} - {max(prices):,}"
            except Exception:
                pass

            # Fallback: regex
            if not result.price:
                html = page.content()
                # Ищем цены в JSON - формат "price":{"value":"287891"}
                for match in re.findall(r'"price":\s*\{\s*"value"\s*:\s*"?(\d+)"?', html):
                    p = int(match)
                    if 80000 < p < 500000:
                        result.price = p
                        result.available = True
                        break

                # Fallback 2: data-auto="snippet-price-current"
                if not result.price:
                    # Ищем текстовые цены вида "287 891" в span
                    for match in re.findall(r'snippet-price-current[^>]*>.*?(\d[\d\s\u00a0\u2006]+\d)', html):
                        clean = re.sub(r'[\s\u00a0\u2006]', '', match)
                        if clean.isdigit():
                            p = int(clean)
                            if 80000 < p < 500000:
                                result.price = p
                                result.available = True
                                break

            if result.price:
                result.status = "PASS"
            else:
                result.status = "FAIL"
                result.error = "No price found"

            context.close()
            browser.close()

    except Exception as e:
        result.status = "ERROR"
        result.error = f"{type(e).__name__}: {str(e)[:50]}"

    result.response_time = time.time() - start_time
    return result


def test_firefox(store: StoreConfig, query: str) -> TestResult:
    """Тест через Firefox + xdotool (DNS-Shop)"""
    start_time = time.time()
    result = TestResult(store=store.name, method="firefox", status="ERROR")

    script_path = Path(__file__).parent / "dns_scraper.sh"
    output_dir = Path("/tmp/dns_scraper_test")

    if not script_path.exists():
        result.status = "SKIP"
        result.error = "dns_scraper.sh not found"
        return result

    try:
        # Создаём директорию
        output_dir.mkdir(parents=True, exist_ok=True)

        # Получаем текущее окружение и модифицируем
        import os
        env = os.environ.copy()
        # Удаляем DISPLAY чтобы скрипт сам запустил xvfb-run
        env.pop("DISPLAY", None)
        env.pop("XVFB_RUNNING", None)

        # Запускаем скрипт - он сам запустит xvfb-run
        proc = subprocess.run(
            ["bash", str(script_path), "macbook-pro", str(output_dir)],
            capture_output=True,
            text=True,
            timeout=FIREFOX_TIMEOUT,
            env=env
        )

        result.details["returncode"] = proc.returncode

        if proc.returncode != 0:
            # Проверяем есть ли частичный вывод
            if "Сохранено:" in proc.stdout or "JSON:" in proc.stdout:
                pass  # Продолжаем парсить
            else:
                result.status = "FAIL"
                result.error = f"Script failed: {proc.stderr[:100] if proc.stderr else proc.stdout[:100]}"
                return result

        # Ищем JSON файл
        json_files = list(output_dir.glob("*.json"))
        if not json_files:
            result.status = "FAIL"
            result.error = "No JSON output"
            return result

        # Парсим последний файл
        latest = max(json_files, key=lambda x: x.stat().st_mtime)
        parsed = parse_dns_json(str(latest))

        if parsed and parsed.get("price"):
            result.price = parsed["price"]
            result.available = parsed.get("available")
            result.details["products_count"] = parsed.get("count", 0)
            result.status = "PASS"
        else:
            result.status = "FAIL"
            result.error = "Failed to parse JSON"

    except subprocess.TimeoutExpired:
        result.status = "FAIL"
        result.error = f"Timeout ({FIREFOX_TIMEOUT}s)"
    except Exception as e:
        result.status = "ERROR"
        result.error = f"{type(e).__name__}: {str(e)[:50]}"

    result.response_time = time.time() - start_time
    return result


# === Основные функции ===

def run_test(store: StoreConfig, query: str) -> TestResult:
    """Запуск теста для магазина"""
    if store.method == "playwright_direct":
        return test_playwright_direct(store, query)
    elif store.method == "playwright_stealth":
        return test_playwright_stealth(store, query)
    elif store.method == "citilink_special":
        return test_citilink_special(store, query)
    elif store.method == "yandex_market_special":
        return test_yandex_market_special(store, query)
    elif store.method == "ozon_firefox":
        return test_ozon_firefox(store, query)
    elif store.method == "avito_firefox":
        return test_avito_firefox(store, query)
    elif store.method == "firefox":
        return test_firefox(store, query)
    else:
        return TestResult(
            store=store.name,
            method=store.method,
            status="ERROR",
            error=f"Unknown method: {store.method}"
        )


def run_all_tests(query: str, skip_firefox: bool = False, store_filter: str = None) -> List[TestResult]:
    """Запуск всех тестов"""
    results = []

    stores = STORES
    if store_filter:
        stores = [s for s in STORES if s.name == store_filter]

    for store in stores:
        # Skip Firefox-based methods in quick mode
        if skip_firefox and ("firefox" in store.method or store.method == "firefox"):
            results.append(TestResult(
                store=store.name,
                method=store.method,
                status="SKIP",
                error="Skipped (--quick mode)"
            ))
            continue

        print(f"\n[TEST] {store.name} ({store.method})")
        result = run_test(store, query)
        results.append(result)

        # Статус
        if result.passed:
            print(f"  [PASS] {format_price(result.price)}")
        else:
            print(f"  [{result.status}] {result.error}")

        print(f"  Time: {result.response_time:.1f}s")

        # Пауза между тестами
        if store.method != "firefox":
            random_delay(2, 4)

    return results


def print_summary(results: List[TestResult]):
    """Печать сводки"""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = [r for r in results if r.status == "PASS"]
    failed = [r for r in results if r.status == "FAIL"]
    errors = [r for r in results if r.status == "ERROR"]
    skipped = [r for r in results if r.status == "SKIP"]

    print(f"\nTotal: {len(results)}")
    print(f"  PASS:  {len(passed)}")
    print(f"  FAIL:  {len(failed)}")
    print(f"  ERROR: {len(errors)}")
    print(f"  SKIP:  {len(skipped)}")

    if passed:
        print("\n" + "-" * 70)
        print("WORKING STORES:")
        print("-" * 70)
        for r in sorted(passed, key=lambda x: x.price or 999999):
            avail = "[+]" if r.available else "[-]" if r.available is False else "[?]"
            print(f"  {r.store}: {format_price(r.price)} {avail} ({r.response_time:.1f}s)")

    if failed or errors:
        print("\n" + "-" * 70)
        print("PROBLEMS:")
        print("-" * 70)
        for r in failed + errors:
            print(f"  {r.store}: [{r.status}] {r.error}")

    # Общий результат
    print("\n" + "=" * 70)
    if len(passed) == len(results) - len(skipped):
        print("RESULT: ALL TESTS PASSED")
    else:
        print(f"RESULT: {len(passed)}/{len(results) - len(skipped)} PASSED")
    print("=" * 70)


def save_results(results: List[TestResult], output_path: Path):
    """Сохранение результатов"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "query": TEST_ARTICLE,
        "results": [asdict(r) for r in results],
        "summary": {
            "total": len(results),
            "passed": len([r for r in results if r.status == "PASS"]),
            "failed": len([r for r in results if r.status == "FAIL"]),
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved: {output_path}")


def main():
    print("=" * 70)
    print("PRICE SCOUT - Scraper Test System")
    print("=" * 70)
    print(f"Test article: {TEST_ARTICLE}")
    print(f"Test product: {TEST_PRODUCT}")

    # Аргументы
    skip_firefox = "--quick" in sys.argv
    store_filter = None

    for arg in sys.argv[1:]:
        if arg.startswith("--store="):
            store_filter = arg.split("=")[1]
        elif arg == "--store" and sys.argv.index(arg) + 1 < len(sys.argv):
            store_filter = sys.argv[sys.argv.index(arg) + 1]

    if skip_firefox:
        print("Mode: QUICK (skipping Firefox tests)")
    if store_filter:
        print(f"Filter: {store_filter}")

    print(f"Stores to test: {len([s for s in STORES if not store_filter or s.name == store_filter])}")

    # Запуск тестов
    results = run_all_tests(TEST_ARTICLE, skip_firefox=skip_firefox, store_filter=store_filter)

    # Сводка
    print_summary(results)

    # Сохранение
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_results(results, output_dir / f"test_results_{timestamp}.json")

    # Exit code
    passed_count = len([r for r in results if r.status == "PASS"])
    expected_count = len([r for r in results if r.status != "SKIP"])
    sys.exit(0 if passed_count == expected_count else 1)


if __name__ == "__main__":
    main()
