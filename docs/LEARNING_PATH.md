# Learning Path: Web Scraping & Price Extraction

> Пошаговое руководство по парсингу цен через поисковики

---

## Архитектура подхода

```
Поисковый запрос: "купить Samsung Galaxy S24 цена"
              |
              v
      ┌───────────────┐
      │  Поисковик    │  (DuckDuckGo, Yandex, SerpAPI)
      └───────┬───────┘
              │
              v
      ┌───────────────┐
      │  Список URL   │  → dns-shop.ru, mvideo.ru, citilink.ru...
      └───────┬───────┘
              │
              v
      ┌───────────────┐
      │  Парсер       │  (requests + BS4 / Playwright)
      └───────┬───────┘
              │
              ├── Captcha? → Решение
              │
              v
      ┌───────────────┐
      │  Извлечение   │  → Название, цена, наличие
      └───────────────┘
```

---

## Модуль 1: Поисковые запросы

### 1.1 Варианты поисковиков

| Поисковик   | API         | Лимиты            | Сложность |
|-------------|-------------|-------------------|-----------|
| DuckDuckGo  | Неофиц.     | Без лимитов       | Низкая    |
| Yandex XML  | Официальный | 10K запросов/день | Средняя   |
| Google CSE  | Официальный | 100 запросов/день | Низкая    |
| SerpAPI     | Платный     | По тарифу         | Низкая    |

### 1.2 DuckDuckGo (рекомендуется для старта)

```python
# Простой вариант через duckduckgo-search
from duckduckgo_search import DDGS

def search_prices(product: str, region: str = "ru-ru") -> list:
    """Поиск цен на товар через DuckDuckGo"""
    query = f"купить {product} цена"

    with DDGS() as ddgs:
        results = list(ddgs.text(query, region=region, max_results=20))

    return [
        {"title": r["title"], "url": r["href"], "snippet": r["body"]}
        for r in results
    ]

# Использование
results = search_prices("Samsung Galaxy S24")
for r in results:
    print(f"{r['title']}\n  {r['url']}\n")
```

### 1.3 Фильтрация результатов

```python
# Известные магазины для фильтрации
KNOWN_SHOPS = {
    "dns-shop.ru": "DNS",
    "mvideo.ru": "М.Видео",
    "citilink.ru": "Ситилинк",
    "eldorado.ru": "Эльдорадо",
    "ozon.ru": "Ozon",
    "wildberries.ru": "Wildberries",
    "market.yandex.ru": "Яндекс.Маркет",
    "regard.ru": "Регард",
    "technopark.ru": "Технопарк",
}

def filter_shop_links(results: list) -> list:
    """Оставить только ссылки на известные магазины"""
    shops = []
    for r in results:
        url = r["url"]
        for domain, name in KNOWN_SHOPS.items():
            if domain in url:
                shops.append({
                    "shop": name,
                    "url": url,
                    "title": r["title"]
                })
                break
    return shops
```

---

## Модуль 2: HTTP запросы и парсинг

### 2.1 Базовый HTTP клиент

```python
import requests
from fake_useragent import UserAgent

class WebClient:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()

    def get(self, url: str, **kwargs) -> requests.Response:
        headers = {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }
        headers.update(kwargs.pop("headers", {}))

        return self.session.get(
            url,
            headers=headers,
            timeout=30,
            **kwargs
        )
```

### 2.2 Парсинг HTML (BeautifulSoup)

```python
from bs4 import BeautifulSoup
import re

def extract_price(html: str) -> dict:
    """Универсальный экстрактор цены"""
    soup = BeautifulSoup(html, "lxml")

    # Стратегия 1: Микроданные Schema.org
    price_elem = soup.find(itemprop="price")
    if price_elem:
        return {
            "method": "schema.org",
            "price": price_elem.get("content") or price_elem.text
        }

    # Стратегия 2: JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if "offers" in data:
                return {
                    "method": "json-ld",
                    "price": data["offers"].get("price")
                }
        except:
            pass

    # Стратегия 3: Regex для цен
    price_pattern = r'(\d{1,3}(?:\s?\d{3})*)\s*(?:₽|руб|RUB)'
    prices = re.findall(price_pattern, soup.get_text())
    if prices:
        return {
            "method": "regex",
            "price": prices[0].replace(" ", "")
        }

    return {"method": "not_found", "price": None}
```

### 2.3 Определение типа страницы

```python
def detect_page_type(soup: BeautifulSoup) -> str:
    """Определить тип страницы: товар, каталог, ошибка"""

    # Признаки страницы товара
    if soup.find(itemprop="product"):
        return "product"
    if soup.find(class_=re.compile(r"product[-_]?card|product[-_]?page")):
        return "product"

    # Признаки каталога
    if soup.find(class_=re.compile(r"catalog|product[-_]?list|search[-_]?results")):
        return "catalog"

    # Признаки ошибки/блокировки
    if soup.find(text=re.compile(r"captcha|robot|blocked", re.I)):
        return "blocked"
    if soup.find(class_=re.compile(r"captcha|recaptcha")):
        return "captcha"

    return "unknown"
```

---

## Модуль 3: Обход защит

### 3.1 Типы защит

| Защита              | Сложность | Решение                               |
|---------------------|-----------|---------------------------------------|
| User-Agent check    | Низкая    | Ротация UA                            |
| Rate limiting       | Низкая    | Задержки, распределение               |
| Cookies/Sessions    | Средняя   | Сохранение сессии                     |
| JavaScript render   | Средняя   | Playwright/Selenium                   |
| reCAPTCHA v2        | Высокая   | 2Captcha, Anti-Captcha                |
| reCAPTCHA v3        | Высокая   | Поведенческие паттерны                |
| Cloudflare          | Высокая   | undetected-chromedriver, FlareSolverr |

### 3.2 Playwright для JS-страниц

```python
from playwright.sync_api import sync_playwright
import random
import time

class BrowserScraper:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

    def get_page(self, url: str) -> str:
        context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
            locale="ru-RU",
        )
        page = context.new_page()

        # Эмуляция человека
        page.goto(url)
        time.sleep(random.uniform(1, 3))

        # Скролл для загрузки контента
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        time.sleep(random.uniform(0.5, 1.5))

        html = page.content()
        context.close()
        return html

    def close(self):
        self.browser.close()
        self.playwright.stop()
```

### 3.3 Решение CAPTCHA (2Captcha API)

```python
import time
import requests

class CaptchaSolver:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://2captcha.com"

    def solve_recaptcha(self, site_key: str, page_url: str) -> str:
        """Решить reCAPTCHA v2"""

        # Шаг 1: Отправить задачу
        resp = requests.post(f"{self.base_url}/in.php", data={
            "key": self.api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "json": 1
        }).json()

        if resp["status"] != 1:
            raise Exception(f"Error: {resp}")

        task_id = resp["request"]

        # Шаг 2: Ждать решения
        for _ in range(60):
            time.sleep(5)
            resp = requests.get(f"{self.base_url}/res.php", params={
                "key": self.api_key,
                "action": "get",
                "id": task_id,
                "json": 1
            }).json()

            if resp["status"] == 1:
                return resp["request"]  # g-recaptcha-response
            elif resp["request"] != "CAPCHA_NOT_READY":
                raise Exception(f"Error: {resp}")

        raise Exception("Timeout waiting for captcha")
```

---

## Модуль 4: Практика

### 4.1 Пошаговый план

| Шаг | Задача                              | Инструменты          |
|-----|-------------------------------------|----------------------|
| 1   | Поиск через DuckDuckGo              | duckduckgo-search    |
| 2   | Фильтрация ссылок на магазины       | Python regex         |
| 3   | Простой HTTP запрос                 | requests             |
| 4   | Парсинг HTML                        | BeautifulSoup        |
| 5   | Обработка JS-страниц                | Playwright           |
| 6   | Обход CAPTCHA                       | 2Captcha API         |
| 7   | Сохранение результатов              | SQLite/PostgreSQL    |

### 4.2 Тестовый скрипт

```python
#!/usr/bin/env python3
"""
Тестовый скрипт для изучения парсинга цен
"""

from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import json
import time
import random

def main():
    product = "Samsung Galaxy S24"

    # Шаг 1: Поиск
    print(f"[1] Поиск: {product}")
    with DDGS() as ddgs:
        results = list(ddgs.text(
            f"купить {product} цена",
            region="ru-ru",
            max_results=10
        ))

    print(f"    Найдено результатов: {len(results)}")

    # Шаг 2: Анализ результатов
    print("\n[2] Результаты поиска:")
    for i, r in enumerate(results[:5], 1):
        print(f"    {i}. {r['title'][:50]}...")
        print(f"       URL: {r['href']}")

    # Шаг 3: Попытка запроса к первому результату
    if results:
        url = results[0]["href"]
        print(f"\n[3] Запрос к: {url}")

        try:
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }, timeout=10)

            print(f"    Status: {resp.status_code}")
            print(f"    Content-Type: {resp.headers.get('content-type', 'unknown')}")
            print(f"    Size: {len(resp.content)} bytes")

            # Шаг 4: Базовый парсинг
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                title = soup.find("title")
                print(f"    Title: {title.text if title else 'N/A'}")

        except Exception as e:
            print(f"    Error: {e}")

if __name__ == "__main__":
    main()
```

---

## Следующие шаги

1. [ ] Установить зависимости: `pip install duckduckgo-search beautifulsoup4 lxml requests`
2. [ ] Запустить тестовый скрипт
3. [ ] Изучить структуру HTML разных магазинов
4. [ ] Добавить Playwright для JS-страниц
5. [ ] Создать базу CSS-селекторов для популярных магазинов

---

## Ресурсы

| Ресурс                   | Описание                                |
|--------------------------|-----------------------------------------|
| duckduckgo-search        | pip install duckduckgo-search           |
| BeautifulSoup docs       | https://beautiful-soup-4.readthedocs.io |
| Playwright Python        | https://playwright.dev/python/          |
| 2Captcha API             | https://2captcha.com/2captcha-api       |
| fake-useragent           | pip install fake-useragent              |
