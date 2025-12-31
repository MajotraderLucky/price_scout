# Price Scout - Project Dashboard

> Последнее обновление: 2025-12-31 13:15

---

## Kanban Board

### Backlog

| ID    | Задача                                   | Приоритет | План                   |
|-------|------------------------------------------|-----------|------------------------|
| PS-10 | Тест 2Captcha на реальном сайте          | High      | [LEARNING_PATH.md]     |
| PS-11 | Тест парсинга с домашнего ПК             | High      | [API_ENDPOINTS.md]     |
| PS-6  | Настроить PostgreSQL схему               | Medium    | [TECH_STACK.md]        |
| PS-7  | Настроить Redis кэширование              | Medium    | [TECH_STACK.md]        |
| PS-8  | Реализовать Telegram бот (teloxide)      | Medium    | [ROADMAP.md]           |

### In Progress

| ID    | Задача                                   | Приоритет | План                   |
|-------|------------------------------------------|-----------|------------------------|
| PS-12 | Исследование доступных магазинов         | High      | find_macbook_price.py  |

### Review

| ID   | Задача                                   | Приоритет | План                             |
|------|------------------------------------------|-----------|----------------------------------|
| PS-1 | Диагностика API E-katalog.ru             | High      | [API_ENDPOINTS.md] - BLOCKED     |
| PS-2 | Исследовать альтернативные источники     | High      | [API_ENDPOINTS.md] - NEEDS PROXY |

### Done

| ID    | Задача                                   | Дата       | Результат                        |
|-------|------------------------------------------|------------|----------------------------------|
| PS-13 | Верификация товара (5-point check)       | 2025-12-31 | find_macbook_price.py            |
| PS-9  | Интеграция 2Captcha                      | 2025-12-31 | test_captcha_solver.py           |
| PS-5  | Python прототип парсера                  | 2025-12-31 | test_search.py, Playwright tests |
| PS-4  | Playwright тесты DNS/Citilink            | 2025-12-31 | Blocked by CAPTCHA/401           |
| PS-3  | Путь обучения web scraping               | 2025-12-31 | [LEARNING_PATH.md]               |
| PS-0  | Документация и планирование              | 2025-12-31 | [README.md]                      |

---

## Quick Links

| Документ           | Описание                       | Путь                           |
|--------------------|--------------------------------|--------------------------------|
| README             | Обзор проекта                  | [README.md](README.md)         |
| Learning Path      | Путь обучения парсингу         | [docs/LEARNING_PATH.md]        |
| API Endpoints      | Результаты диагностики         | [docs/API_ENDPOINTS.md]        |
| Roadmap            | Фазы разработки                | [docs/ROADMAP.md]              |
| Tech Stack         | Архитектура и технологии       | [docs/TECH_STACK.md]           |
| Parsing Strategy   | Стратегия парсинга             | [docs/PARSING_STRATEGY.md]     |

---

## Scripts

| Скрипт                      | Описание                              | Статус      |
|-----------------------------|---------------------------------------|-------------|
| find_macbook_price.py       | Поиск цены с верификацией товара      | [+] Working |
| search_macbook.py           | Поиск по артикулу через DuckDuckGo    | [+] Working |
| check_url.py                | Проверка URL (HTTP)                   | [+] Working |
| check_url_playwright.py     | Проверка URL (Playwright)             | [+] Working |
| test_search.py              | Поиск через DuckDuckGo                | [+] Working |
| test_playwright_dns.py      | Парсинг DNS-Shop                      | [X] 401     |
| test_playwright_citilink.py | Парсинг Citilink                      | [X] CAPTCHA |
| test_captcha_solver.py      | Интеграция 2Captcha                   | [+] Ready   |

---

## Project Stats

| Метрика              | Значение           |
|----------------------|--------------------|
| Фаза                 | MVP (Phase 1)      |
| Статус               | Development        |
| Задач в Backlog      | 5                  |
| Задач In Progress    | 1                  |
| Задач в Review       | 2                  |
| Задач Done           | 6                  |
| Python скриптов      | 8                  |
| Документов           | 11                 |

---

## Current Focus

**Текущая задача: PS-12 - Исследование доступных магазинов**

Цель: Найти больше работающих магазинов для парсинга цен MacBook Pro 16 (Z14V0008D)

**Следующие шаги:**

1. **Исследовать результаты поиска DuckDuckGo**
   - Проверить все найденные ссылки
   - Найти магазины без CAPTCHA/блокировок
   - Расширить список верифицированных источников

2. **Улучшить верификацию**
   - Добавить больше паттернов проверки
   - Улучшить определение наличия товара

3. **Опционально: 2Captcha интеграция**
   - API ключ 2Captcha (~$3 для теста)
   - Протестировать на заблокированных магазинах

---

## Findings Summary

| Источник      | Метод      | Статус      | Проблема               | Решение          |
|---------------|------------|-------------|------------------------|------------------|
| DuckDuckGo    | HTTP       | [+] OK      | -                      | -                |
| i-ray.ru      | Playwright | [+] OK      | -                      | Verified, 4/4    |
| regard.ru     | Stealth    | [+] OK      | Bot detection          | Stealth bypass   |
| KNS.ru        | Playwright | [+] OK      | URL нестабилен         | Verified         |
| centrsvyazi   | Playwright | [+] OK      | -                      | Verified         |
| E-katalog.ru  | HTTP       | [X] Blocked | IP блокировка          | VPN/Proxy/Local  |
| DNS-Shop      | Playwright | [X] 401     | Bot detection          | Stealth/Proxy    |
| Citilink      | Playwright | [X] 429     | CAPTCHA + Rate limit   | 2Captcha         |

### Найденные цены (MacBook Pro 16 Z14V0008D)

| Магазин       | Цена        | Верификация | Наличие        | Метод   |
|---------------|-------------|-------------|----------------|---------|
| i-ray.ru      | 107,999 RUB | 4/4         | Нет в наличии  | Direct  |
| regard.ru     | 144,400 RUB | 3/4         | В наличии      | Stealth |
| centrsvyazi   | 103,500 RUB | 5/5         | Неизвестно     | Direct  |
| kns.ru        | 156,463 RUB | 5/5         | Нет в наличии  | Direct  |

---

## Changelog

| Дата       | Изменение                                            |
|------------|------------------------------------------------------|
| 2025-12-31 | Stealth scraper: обход защиты regard.ru (144,400)    |
| 2025-12-31 | Найден i-ray.ru: 107,999 RUB, В наличии, verified    |
| 2025-12-31 | find_macbook_price.py: верификация товара (5 checks) |
| 2025-12-31 | Скрипты поиска MacBook по артикулу Z14V0008D         |
| 2025-12-31 | Добавлена интеграция 2Captcha (PS-9)                 |
| 2025-12-31 | Тесты Playwright: DNS (401), Citilink (CAPTCHA)      |
| 2025-12-31 | Создан test_search.py - DuckDuckGo работает          |
| 2025-12-31 | Создан LEARNING_PATH.md - путь обучения              |
| 2025-12-31 | PS-1 заблокирован: e-katalog.ru недоступен           |
| 2025-12-31 | Создан дашборд проекта                               |
| 2025-12-31 | Начальная документация проекта                       |

---

## Environment

```bash
# Активация окружения
cd /home/ryazanov/Development/price_scout
source venv/bin/activate

# Установленные пакеты
# - duckduckgo-search
# - beautifulsoup4, lxml
# - playwright (+ chromium)
# - 2captcha-python
# - requests
```

[LEARNING_PATH.md]: docs/LEARNING_PATH.md
[PARSING_STRATEGY.md]: docs/PARSING_STRATEGY.md
[TECH_STACK.md]: docs/TECH_STACK.md
[ROADMAP.md]: docs/ROADMAP.md
[API_DIAGNOSTICS_PLAN.md]: docs/API_DIAGNOSTICS_PLAN.md
[API_ENDPOINTS.md]: docs/API_ENDPOINTS.md
[README.md]: README.md
