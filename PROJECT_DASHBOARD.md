# Price Scout - Project Dashboard

> Последнее обновление: 2026-01-03

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

### Review

| ID   | Задача                                   | Приоритет | План                             |
|------|------------------------------------------|-----------|----------------------------------|
| PS-1 | Диагностика API E-katalog.ru             | High      | [API_ENDPOINTS.md] - BLOCKED     |
| PS-2 | Исследовать альтернативные источники     | High      | [API_ENDPOINTS.md] - NEEDS PROXY |

### Done

| ID    | Задача                                   | Дата       | Результат                        |
|-------|------------------------------------------|------------|----------------------------------|
| PS-17 | Исправить парсер Avito                   | 2026-01-03 | Работает! 9/9 магазинов          |
| PS-16 | Advanced bypass (Firefox/Warmup)         | 2025-12-31 | Серверная защита, не обходится   |
| PS-15 | Stealth-тест на заблокированных          | 2025-12-31 | Citilink/DNS/Kotofoto - CAPTCHA  |
| PS-14 | Stealth scraper (playwright-stealth)     | 2025-12-31 | stealth_scraper.py, regard.ru OK |
| PS-12 | Исследование доступных магазинов         | 2025-12-31 | 7 магазинов верифицировано       |
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
| advanced_bypass.py          | Firefox/Warmup техники обхода         | [!] Limited |
| stealth_scraper.py          | Stealth-парсер (обход CAPTCHA)        | [+] Working |
| find_macbook_price.py       | Поиск цены с верификацией товара      | [+] Working |
| search_macbook.py           | Поиск по артикулу через DuckDuckGo    | [+] Working |
| check_url.py                | Проверка URL (HTTP)                   | [+] Working |
| check_url_playwright.py     | Проверка URL (Playwright)             | [+] Working |
| test_search.py              | Поиск через DuckDuckGo                | [+] Working |
| test_playwright_dns.py      | Парсинг DNS-Shop                      | [X] 401     |
| test_playwright_citilink.py | Парсинг Citilink                      | [X] CAPTCHA |
| test_captcha_solver.py      | Интеграция 2Captcha                   | [+] Ready   |
| parse_citilink.py           | Citilink парсер (archbook)            | [+] Working |
| test_dns_uc.py              | DNS undetected-chromedriver           | [X] 403     |
| test_dns_headful.py         | DNS headful via Xvfb                  | [X] 403     |
| dns_scraper.sh              | DNS Firefox + xdotool (archbook)      | [+] Working |
| dns_api_scraper.py          | DNS API scraper (catalog JSON)        | [+] Working |
| test_scrapers.py            | Unified test system (all methods)     | [+] Working |
| citilink_playwright.py      | Citilink Playwright + delay scraper   | [+] Working |
| citilink_scraper.sh         | Citilink Firefox + xdotool (backup)   | [!] Limited |

---

## Project Stats

| Метрика              | Значение           |
|----------------------|--------------------|
| Фаза                 | MVP (Phase 1)      |
| Статус               | Development        |
| Задач в Backlog      | 5                  |
| Задач In Progress    | 0                  |
| Задач в Review       | 2                  |
| Задач Done           | 10                 |
| Python скриптов      | 18                 |
| Документов           | 11                 |

---

## Current Focus

**Статус: ALL TESTS PASSED - 9/9 магазинов работают!**

**Инфраструктура:**
| Сервер   | IP              | Провайдер  | Статус       |
|----------|-----------------|------------|--------------|
| VPS      | 185.105.108.119 | Datacenter | [X] CAPTCHA  |
| Archbook | 91.122.50.46    | Ростелеком | [+] Working  |

**Результаты unified test (test_scrapers.py):**
| Магазин       | Цена        | Наличие | Время  | Метод                 | Статус   |
|---------------|-------------|---------|--------|-----------------------|----------|
| avito         | 54,900 RUB  | [+] Да  | 41.0s  | firefox+xvfb          | [+] PASS |
| dns           | 62,799 RUB  | [+] Да  | 38.2s  | firefox+xvfb          | [+] PASS |
| ozon          | 94,213 RUB  | [+] Да  | 52.4s  | ozon_firefox          | [+] PASS |
| i-ray         | 107,999 RUB | [+] Да  | 4.1s   | playwright            | [+] PASS |
| citilink      | 115,990 RUB | [+] Да  | 14.5s  | citilink_special      | [+] PASS |
| nix           | 129,563 RUB | [-] Нет | 3.6s   | playwright            | [+] PASS |
| regard        | 144,400 RUB | [+] Да  | 7.9s   | stealth               | [+] PASS |
| kns           | 156,463 RUB | [-] Нет | 3.5s   | playwright            | [+] PASS |
| yandex_market | 295,309 RUB | [+] Да  | 15.4s  | yandex_market_special | [+] PASS |

**Вывод:** ALL TESTS PASSED! 9/9 магазинов работают

**Текущие рабочие источники (10 магазинов):**

| Магазин       | Цена            | Наличие       | Метод                 | Время  |
|---------------|-----------------|---------------|-----------------------|--------|
| Avito         | 54,900-349,990  | 16 объявлений | Firefox+xdotool       | 41.0s  |
| DNS-Shop      | 62,799-419,999  | 77 моделей    | Firefox+xdotool       | 38.2s  |
| Ozon          | 94,213 RUB      | В наличии     | ozon_firefox          | 52.4s  |
| centrsvyazi   | 103,500 RUB     | Неизвестно    | Playwright            | -      |
| i-ray.ru      | 107,999 RUB     | В наличии     | Playwright            | 3.3s   |
| Citilink      | 115,990-208,690 | 10 моделей    | citilink_special      | -      |
| nix.ru        | 129,563 RUB     | Нет в наличии | Playwright            | 2.9s   |
| regard.ru     | 144,400 RUB     | В наличии     | Stealth               | 7.1s   |
| kns.ru        | 156,463 RUB     | Нет в наличии | Playwright            | 4.2s   |
| Yandex Market | 287,891 RUB     | В наличии     | yandex_market_special | 15.2s  |

---

## Findings Summary

| Источник      | Метод      | Статус      | Проблема               | Решение               |
|---------------|------------|-------------|------------------------|-----------------------|
| DuckDuckGo    | HTTP       | [+] OK      | -                      | -                     |
| i-ray.ru      | Playwright | [+] OK      | -                      | Verified, 4/4         |
| nix.ru        | Playwright | [+] OK      | -                      | Direct access         |
| regard.ru     | Stealth    | [+] OK      | Bot detection          | Stealth bypass        |
| kns.ru        | Playwright | [+] OK      | URL нестабилен         | Verified              |
| centrsvyazi   | Playwright | [+] OK      | -                      | Verified              |
| DNS-Shop      | Firefox    | [+] OK      | Qrator bypass          | xdotool + Xvfb        |
| Citilink      | Playwright | [!] 429     | Rate limit             | Delay + Stealth       |
| Yandex Market | Playwright | [+] OK      | -                      | yandex_market_special |
| E-katalog.ru  | HTTP       | [X] Blocked | IP блокировка          | VPN/Proxy/Local       |
| Ozon          | Firefox    | [+] OK      | Headless detection     | ozon_firefox          |
| Avito         | Firefox    | [+] OK      | VPS блокирован         | Firefox на Archbook   |

### Найденные цены (MacBook Pro 16)

| Магазин       | Цена        | Верификация | Наличие        | Метод                 |
|---------------|-------------|-------------|----------------|-----------------------|
| Avito         | 54,900 RUB  | -           | 16 объявлений  | Firefox+xdotool       |
| DNS-Shop      | 62,799+     | -           | 77 моделей     | Firefox+xdotool       |
| Ozon          | 94,213 RUB  | -           | В наличии      | ozon_firefox          |
| centrsvyazi   | 103,500 RUB | 5/5         | Неизвестно     | Playwright            |
| i-ray.ru      | 107,999 RUB | 4/4         | В наличии      | Playwright            |
| Citilink      | 115,990 RUB | -           | 10 моделей     | citilink_special      |
| nix.ru        | 129,563 RUB | -           | Нет в наличии  | Playwright            |
| regard.ru     | 144,400 RUB | 3/4         | В наличии      | Stealth               |
| kns.ru        | 156,463 RUB | 5/5         | Нет в наличии  | Playwright            |
| Yandex Market | 287,891 RUB | -           | В наличии      | yandex_market_special |

---

## Changelog

| Дата       | Изменение                                                   |
|------------|-------------------------------------------------------------|
| 2026-01-03 | Avito работает! Исправлен парсер, 9/9 магазинов, 54,900 RUB |
| 2026-01-02 | Ozon добавлен! 94,213 RUB через Firefox, 8/9 магазинов      |
| 2026-01-02 | Yandex Market добавлен! 287,891 RUB, 7/8 магазинов работают |
| 2026-01-02 | ALL TESTS PASSED! 6/6 unified test, все методы работают     |
| 2026-01-02 | test_scrapers.py: citilink_special + firefox xvfb fix       |
| 2026-01-02 | Citilink работает! Playwright + delay, 10 моделей           |
| 2026-01-02 | Добавлен nix.ru (129,563 RUB), 7/7 магазинов работают       |
| 2026-01-02 | DNS-Shop работает! Firefox + xdotool, 77 моделей            |
| 2025-12-31 | PS-19: DNS-Shop - IP banned + Qrator, нет доступа           |
| 2025-12-31 | PS-18: Citilink работает! 6 цен MacBook получено            |
| 2025-12-31 | PS-17: Деплой на Archbook - i-ray.ru работает!              |
| 2025-12-31 | PS-16: Advanced bypass - серверная защита, не обойти        |
| 2025-12-31 | PS-15: Stealth не обходит Citilink/DNS/Kotofoto             |
| 2025-12-31 | Stealth scraper: обход защиты regard.ru (144,400)           |
| 2025-12-31 | Найден i-ray.ru: 107,999 RUB, В наличии, verified           |
| 2025-12-31 | find_macbook_price.py: верификация товара (5 checks)        |
| 2025-12-31 | Скрипты поиска MacBook по артикулу Z14V0008D                |
| 2025-12-31 | Добавлена интеграция 2Captcha (PS-9)                        |
| 2025-12-31 | Тесты Playwright: DNS (401), Citilink (CAPTCHA)             |
| 2025-12-31 | Создан test_search.py - DuckDuckGo работает                 |
| 2025-12-31 | Создан LEARNING_PATH.md - путь обучения                     |
| 2025-12-31 | PS-1 заблокирован: e-katalog.ru недоступен                  |
| 2025-12-31 | Создан дашборд проекта                                      |
| 2025-12-31 | Начальная документация проекта                              |

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
