# Price Scout

**Разведчик цен** - система мониторинга и сравнения цен на товары с различных интернет-магазинов.

## Текущий статус

**Фаза:** MVP / Исследование
**Подход:** Python + Web Scraping через поисковики

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRICE SCOUT                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [1] ПОИСК                    [2] ПАРСИНГ                          │
│  ┌─────────────────┐          ┌─────────────────┐                  │
│  │ DuckDuckGo API  │ ──────>  │ Playwright      │                  │
│  │ (по артикулу)   │          │ (JS рендеринг)  │                  │
│  └─────────────────┘          └─────────────────┘                  │
│           │                            │                           │
│           v                            v                           │
│  ┌─────────────────┐          ┌─────────────────┐                  │
│  │ Список URL      │          │ HTML парсинг    │                  │
│  │ магазинов       │          │ (BeautifulSoup) │                  │
│  └─────────────────┘          └─────────────────┘                  │
│                                        │                           │
│  [3] ВЕРИФИКАЦИЯ                       v                           │
│  ┌─────────────────┐          ┌─────────────────┐                  │
│  │ Проверка:       │          │ Извлечение:     │                  │
│  │ - Артикул       │ <──────  │ - Цена          │                  │
│  │ - RAM/SSD/CPU   │          │ - Наличие       │                  │
│  │ - Тип страницы  │          │ - Schema.org    │                  │
│  └─────────────────┘          └─────────────────┘                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Возможности

- Поиск товаров по артикулу через DuckDuckGo
- Парсинг магазинов с JS-рендерингом (Playwright)
- Верификация товара (5-point check: артикул, RAM, SSD, CPU, тип страницы)
- Извлечение цен из Schema.org/JSON-LD и HTML
- Определение наличия товара
- Интеграция 2Captcha для обхода защиты

## Технологический стек

| Компонент       | Технология               | Статус      |
|-----------------|--------------------------|-------------|
| Поиск           | duckduckgo-search        | [+] Working |
| Браузер         | Playwright + Chromium    | [+] Working |
| Парсинг HTML    | BeautifulSoup + lxml     | [+] Working |
| CAPTCHA solving | 2captcha-python          | [+] Ready   |
| HTTP клиент     | requests                 | [+] Working |

## Быстрый старт

```bash
# Клонирование
git clone <repo-url>
cd price_scout

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install duckduckgo-search playwright beautifulsoup4 lxml requests 2captcha-python

# Установка браузера
playwright install chromium

# Запуск поиска
python scripts/find_macbook_price.py
```

## Скрипты

| Скрипт                   | Описание                           |
|--------------------------|------------------------------------|
| find_macbook_price.py    | Полный pipeline с верификацией     |
| search_macbook.py        | Поиск по артикулу через DuckDuckGo |
| check_url.py             | Проверка URL (HTTP)                |
| check_url_playwright.py  | Проверка URL (Playwright)          |
| test_captcha_solver.py   | Интеграция 2Captcha                |

## Результаты исследования

| Источник     | Метод      | Статус      | Проблема             |
|--------------|------------|-------------|----------------------|
| DuckDuckGo   | HTTP API   | [+] OK      | -                    |
| E-katalog.ru | HTTP       | [X] Blocked | IP блокировка        |
| DNS-Shop     | Playwright | [X] 401     | Bot detection        |
| Citilink     | Playwright | [X] 429     | CAPTCHA + Rate limit |
| KNS.ru       | Playwright | [+] OK      | -                    |
| centrsvyazi  | Playwright | [+] OK      | -                    |

## Документация

| Документ              | Описание                   |
|-----------------------|----------------------------|
| [Dashboard]           | Kanban доска проекта       |
| [Learning Path]       | Путь обучения web scraping |
| [API Endpoints]       | Результаты диагностики API |
| [Parsing Strategy]    | Стратегия парсинга         |
| [Roadmap]             | План развития              |

[Dashboard]: PROJECT_DASHBOARD.md
[Learning Path]: docs/LEARNING_PATH.md
[API Endpoints]: docs/API_ENDPOINTS.md
[Parsing Strategy]: docs/PARSING_STRATEGY.md
[Roadmap]: docs/ROADMAP.md

## Лицензия

MIT
