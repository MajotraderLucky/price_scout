# Price Scout

**Разведчик цен** - система мониторинга и сравнения цен на товары с различных интернет-магазинов.

## Текущий статус: 8/8 магазинов работают

| Магазин       | Цена        | Метод                 | Время  | Статус   |
|---------------|-------------|-----------------------|--------|----------|
| DNS-Shop      | 62,799 RUB  | Firefox + xdotool     | 38.2s  | [+] PASS |
| Ozon          | 94,213 RUB  | Firefox + xdotool     | 52.4s  | [+] PASS |
| i-ray.ru      | 107,999 RUB | Playwright Direct     | 4.1s   | [+] PASS |
| Citilink      | 115,990 RUB | Playwright + Stealth  | 14.5s  | [+] PASS |
| nix.ru        | 129,563 RUB | Playwright Direct     | 3.6s   | [+] PASS |
| regard.ru     | 144,400 RUB | Playwright Stealth    | 7.9s   | [+] PASS |
| kns.ru        | 156,463 RUB | Playwright Direct     | 3.5s   | [+] PASS |
| Yandex Market | 295,309 RUB | Playwright + Stealth  | 15.4s  | [+] PASS |

## Архитектура

```
+---------------------------------------------------------------------+
| PRICE SCOUT |
+---------------------------------------------------------------------+
|----------------------------------------------------------------------|
| [1] МЕТОДЫ ПАРСИНГА                                                  |
| +---------------------+  +---------------------+  +---------------+  |
|                                                                      | Playwright Direct |  | Playwright Stealth |  | Firefox+xdotool |
|                                                                      | (i-ray, nix, kns) |  | (regard, citilink, |  | (DNS, Ozon) |
|                                                                      |  |  | yandex_market) |  |  |
| +---------------------+  +---------------------+  +---------------+  |
|----------------------------------------------------------------------|
| v                        v                      v                    |
| [2] ПАРСИНГ ДАННЫХ                                                   |
| +---------------------+  +---------------------+  +---------------+  |
|                                                                      | Schema.org/JSON-LD |  | Next.js (__NEXT__) |  | JSON API |
|                                                                      | itemprop="price" |  | data-meta-price |  | catalog.json |
| +---------------------+  +---------------------+  +---------------+  |
|----------------------------------------------------------------------|
| [3] ИНФРАСТРУКТУРА                                                   |
| +---------------------+  +---------------------+                     |
|                                                                      | VPS (datacenter IP) |  | Archbook (резид.IP) |  |
|                                                                      | [X] CAPTCHA blocked |  | [+] ALL TESTS PASS |  |
| +---------------------+  +---------------------+                     |
|----------------------------------------------------------------------|
+---------------------------------------------------------------------+
```

## Возможности

- Парсинг 8 интернет-магазинов
- Обход защиты: Qrator WAF, Rate Limiting, Bot Detection
- 3 метода парсинга: Playwright Direct, Stealth, Firefox+xdotool
- Retry логика для нестабильных источников (Citilink)
- Unified test system для всех магазинов

## Технологический стек

| Компонент       | Технология               | Статус      |
|-----------------|--------------------------|-------------|
| Браузер         | Playwright + Chromium    | [+] Working |
| Stealth         | playwright-stealth       | [+] Working |
| Firefox bypass  | Firefox + xdotool + Xvfb | [+] Working |
| Парсинг HTML    | BeautifulSoup + lxml     | [+] Working |
| HTTP клиент     | requests                 | [+] Working |
| CAPTCHA solving | 2captcha-python          | [+] Ready   |

## Быстрый старт

```bash
# Клонирование
git clone <repo-url>
cd price_scout

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install playwright playwright-stealth beautifulsoup4 lxml requests

# Установка браузера
playwright install chromium

# Для Firefox метода (DNS, Ozon)
sudo apt install firefox xvfb xdotool xclip i3

# Запуск всех тестов
python scripts/test_scrapers.py
```

## Скрипты

| Скрипт                 | Описание                           | Статус      |
|------------------------|------------------------------------|-------------|
| test_scrapers.py       | Unified test system (все магазины) | [+] Working |
| dns_scraper.sh         | DNS-Shop Firefox scraper           | [+] Working |
| ozon_scraper.sh        | Ozon Firefox scraper               | [+] Working |
| stealth_scraper.py     | Stealth парсер (regard.ru)         | [+] Working |
| citilink_playwright.py | Citilink с retry логикой           | [+] Working |

## Результаты тестирования

| Источник      | Метод      | Статус      | Защита               |
|---------------|------------|-------------|----------------------|
| DNS-Shop      | Firefox    | [+] OK      | Qrator WAF           |
| Ozon          | Firefox    | [+] OK      | Headless detection   |
| i-ray.ru      | Playwright | [+] OK      | Нет                  |
| Citilink      | Stealth    | [+] OK      | Rate Limit (429)     |
| nix.ru        | Playwright | [+] OK      | Нет                  |
| regard.ru     | Stealth    | [+] OK      | Bot detection        |
| kns.ru        | Playwright | [+] OK      | Нет                  |
| Yandex Market | Stealth    | [+] OK      | SmartCaptcha         |
| Avito         | -          | [X] Blocked | IP блокировка        |
| E-katalog.ru  | -          | [X] Blocked | IP блокировка        |

## Документация

| Документ           | Описание                   |
|--------------------|----------------------------|
| [Dashboard]        | Kanban доска проекта       |
| [Parsing Strategy] | Стратегия и методы         |
| [API Endpoints]    | Результаты тестирования    |
| [Learning Path]    | Путь обучения web scraping |
| [Roadmap]          | План развития              |

[Dashboard]: PROJECT_DASHBOARD.md
[Learning Path]: docs/LEARNING_PATH.md
[API Endpoints]: docs/API_ENDPOINTS.md
[Parsing Strategy]: docs/PARSING_STRATEGY.md
[Roadmap]: docs/ROADMAP.md

## Лицензия

MIT
