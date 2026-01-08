# Price Scout - Project Dashboard

> Последнее обновление: 2026-01-08 (PS-46 Phase 2 Auto-Import Complete)

---

## Kanban Board

### Backlog

| ID    | Задача                          | Приоритет | План               |
|-------|---------------------------------|-----------|--------------------|
| PS-10 | Тест 2Captcha на реальном сайте | Medium    | [LEARNING_PATH.md] |
| PS-7  | Настроить Redis кэширование     | Low       | [TECH_STACK.md]    |

### In Progress

| ID    | Задача                                 | Приоритет | План                                               |
|-------|----------------------------------------|-----------|----------------------------------------------------|
| PS-46 | Система аналитики магазинов (арбитраж) | High      | [План](~/.claude/plans/snuggly-floating-minsky.md) |

### Review

| ID | Задача | Приоритет | План |
|----|--------|-----------|------|

### Done

| ID    | Задача                                 | Дата       | Результат                           |
|-------|----------------------------------------|------------|-------------------------------------|
| PS-45 | Улучшить веб-поиск (извлечение цен)    | 2026-01-08 | Playwright + DuckDuckGo integration |
| PS-44 | Currency Auto-Collection (systemd)     | 2026-01-07 | Daily timer 12:00, CBR API          |
| PS-43 | Bot UX - Inline Keyboards              | 2026-01-07 | All messages have command buttons   |
| PS-42 | Analytics System (/stats, logging)     | 2026-01-07 | Stats command, command logging, fix |
| PS-40 | Bot Localization (Russian)             | 2026-01-06 | All UI strings translated to RU     |
| PS-30 | Bot Notifications + Command Hints      | 2026-01-06 | Auto-notifications, footer hints    |
| PS-39 | Market Research System                 | 2026-01-06 | Top 100, discovery, /top command    |
| PS-8  | Telegram Bot (teloxide)                | 2026-01-06 | 10 commands, standalone DB mode     |
| PS-38 | ML Price Predictions (Random Forest)   | 2026-01-05 | 7-day forecasts, Python ML script   |
| PS-37 | Arbitrage Detector                     | 2026-01-05 | Price differences across stores     |
| PS-36 | Analytics Dashboard                    | 2026-01-05 | 6 endpoints (trends, correlation)   |
| PS-35 | Automated Scheduled Scraping           | 2026-01-05 | Scheduler + 2 binaries, 10-min      |
| PS-34 | Currency Rates Tracking                | 2026-01-05 | Dual sources (CBR + open.er-api)    |
| PS-33 | Add AliExpress Russia marketplace      | 2026-01-05 | Fallback DOM parser, 9th store      |
| PS-28 | API Server (Axum REST endpoints)       | 2026-01-05 | 13 endpoints, analytics ready       |
| PS-29 | Scraper Orchestration (Queue + Worker) | 2026-01-04 | Job queue + background worker       |
| PS-23 | Python Bridge Implementation           | 2026-01-04 | Rust-Python subprocess bridge       |
| PS-22 | Rust Workspace Bootstrap               | 2026-01-04 | 5 crates, 335 dependencies          |
| PS-21 | PostgreSQL Schema Implementation       | 2026-01-04 | 7 tables, migrations applied        |
| PS-20 | Управление Citilink Rate Limiting      | 2026-01-04 | Исключен из регулярных тестов       |
| PS-19 | Фильтрация товаров по характеристикам  | 2026-01-03 | Phase 1: DNS specs filter (80%)     |
| PS-18 | Исправить Citilink rate limiting       | 2026-01-03 | Задержки 90-210s, стабильно         |
| PS-17 | Исправить парсер Avito                 | 2026-01-03 | Работает! 9/9 магазинов             |
| PS-16 | Advanced bypass (Firefox/Warmup)       | 2025-12-31 | Серверная защита, не обходится      |
| PS-15 | Stealth-тест на заблокированных        | 2025-12-31 | Citilink/DNS/Kotofoto - CAPTCHA     |
| PS-14 | Stealth scraper (playwright-stealth)   | 2025-12-31 | stealth_scraper.py, regard.ru OK    |
| PS-12 | Исследование доступных магазинов       | 2025-12-31 | 7 магазинов верифицировано          |
| PS-13 | Верификация товара (5-point check)     | 2025-12-31 | find_macbook_price.py               |
| PS-9  | Интеграция 2Captcha                    | 2025-12-31 | test_captcha_solver.py              |
| PS-5  | Python прототип парсера                | 2025-12-31 | test_search.py, Playwright tests    |
| PS-4  | Playwright тесты DNS/Citilink          | 2025-12-31 | Blocked by CAPTCHA/401              |
| PS-3  | Путь обучения web scraping             | 2025-12-31 | [LEARNING_PATH.md]                  |
| PS-0  | Документация и планирование            | 2025-12-31 | [README.md]                         |

---

## Quick Links

| Документ           | Описание                                    | Путь                                                                   |
|--------------------|---------------------------------------------|------------------------------------------------------------------------|
| README             | Обзор проекта                               | [README.md](README.md)                                                 |
| Market Analysis    | План развития: Анализ рынка и торговля      | [~/.claude/plans/cheerful-bubbling-catmull.md]                         |
| Learning Path      | Путь обучения парсингу                      | [docs/LEARNING_PATH.md]                                                |
| API Endpoints      | Результаты диагностики                      | [docs/API_ENDPOINTS.md]                                                |
| Roadmap            | Фазы разработки                             | [docs/ROADMAP.md]                                                      |
| Tech Stack         | Архитектура и технологии                    | [docs/TECH_STACK.md]                                                   |
| Parsing Strategy   | Стратегия парсинга                          | [docs/PARSING_STRATEGY.md]                                             |

---

## Scripts

| Скрипт                      | Описание                              | Статус      |
|-----------------------------|---------------------------------------|-------------|
| specs_filter.py             | Фильтрация товаров по характеристикам | [+] Working |
| test_specs_filter.py        | Unit-тесты фильтрации (15 тестов)     | [+] Working |
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
| store_discovery.py          | Auto-import store candidates          | [+] Working |
| web_search.py               | DuckDuckGo price search + tracking    | [+] Working |
| store_parsers.py            | Playwright price extraction           | [+] Working |
| citilink_playwright.py      | Citilink Playwright + delay scraper   | [+] Working |
| citilink_scraper.sh         | Citilink Firefox + xdotool (backup)   | [!] Limited |

---

## Project Stats

| Метрика           | Значение         |
|-------------------|------------------|
| Фаза              | Phase 4 Complete |
| Статус            | Bot UX Complete  |
| Задач в Backlog   | 2                |
| Задач In Progress | 1                |
| Задач в Review    | 0                |
| Задач Done        | 30               |
| Python скриптов   | 28               |
| Rust modules      | 10               |
| Bot commands      | 11               |
| Документов        | 20               |

---

## Current Focus

**Статус: MARKET RESEARCH SYSTEM COMPLETE - Phase 4 Done!**

**Новые возможности (Phase 4):**
- [+] Market Research System: Top 100 популярных товаров (1,000-15,000 RUB)
- [+] Product Discovery: DuckDuckGo поиск + hourly scheduler
- [+] Popularity Scoring: 4 метрики (tracking, volatility, availability, arbitrage)
- [+] Telegram /top command: Просмотр рейтинга популярности
- [+] Telegram /web command: Веб-поиск через DuckDuckGo
- [+] API endpoints: /api/market-research/* (top-100, popular-queries, categories)

**Возможности (Phase 3):**
- [+] Analytics API (6 endpoints): Price trends, currency correlation, store comparison, market overview
- [+] Arbitrage detector: Find price differences across stores (10%+ profit opportunities)
- [+] ML Price predictions: 7-day forecasts using Random Forest (Python + scikit-learn)
- [+] Automated scraping: Every 10 minutes for products in 5,000-15,000 RUB range
- [+] Currency tracking: Dual sources (ЦБ РФ + open.er-api.com)

**Инфраструктура:**
| Сервер   | IP              | Провайдер  | Статус       |
|----------|-----------------|------------|--------------|
| VPS      | 185.105.108.119 | Datacenter | [X] CAPTCHA  |
| Archbook | 91.122.50.46    | Ростелеком | [+] Working  |

**Результаты unified test (test_scrapers.py):**
| Магазин       | Цена        | Наличие | Время  | Метод                 | Статус       | Примечание              |
|---------------|-------------|---------|--------|-----------------------|--------------|-------------------------|
| avito         | 82,900 RUB  | [+] Да  | 46.6s  | avito_firefox         | [+] PASS     | Score: 80% (1/32)       |
| dns           | 62,799 RUB  | [+] Да  | 38.3s  | firefox               | [+] PASS     | Score: 0% (0/18)        |
| ozon          | 105,562 RUB | [+] Да  | 52.5s  | ozon_firefox          | [+] PASS     | Score: 0% (0/17)        |
| i-ray         | 107,999 RUB | [+] Да  | 3.9s   | playwright_direct     | [+] PASS     | Score: 0% (0/1)         |
| nix           | 129,563 RUB | [-] Нет | 3.8s   | playwright_direct     | [+] PASS     | Score: 0% (0/1)         |
| regard        | 144,400 RUB | [+] Да  | 8.6s   | playwright_stealth    | [+] PASS     | Score: 0% (0/1)         |
| kns           | 156,463 RUB | [-] Нет | 3.9s   | playwright_direct     | [+] PASS     | Score: 0% (0/1)         |
| yandex_market | 181,550 RUB | [+] Да  | 15.4s  | yandex_market_special | [+] PASS     | Score: 10% (0/1)        |
| citilink      | N/A         | [~] Да  | N/A    | citilink_firefox      | [~] UNSTABLE | Только --store=citilink |

**Примечание:**
- Citilink исключен из регулярных тестов из-за rate limiting
- Для тестирования: `python test_scrapers.py --store=citilink` (интервал 5+ мин)
- Остальные магазины: `python test_scrapers.py --skip-unstable`

**Вывод:** 8/8 стабильных магазинов работают (Citilink UNSTABLE, тестируется вручную)

**Текущие рабочие источники (10 магазинов):**

| Магазин       | Цена            | Наличие       | Метод                 | Время  |
|---------------|-----------------|---------------|-----------------------|--------|
| Avito         | 51,799-349,990  | 16 объявлений | Firefox+xdotool       | 46.4s  |
| DNS-Shop      | 62,799-419,999  | 77 моделей    | Firefox+xdotool       | 38.3s  |
| Ozon          | 75,024 RUB      | В наличии     | ozon_firefox          | 52.4s  |
| centrsvyazi   | 103,500 RUB     | Неизвестно    | Playwright            | -      |
| i-ray.ru      | 107,999 RUB     | В наличии     | Playwright            | 3.5s   |
| Citilink      | 115,990 RUB     | В наличии     | citilink_special      | 24.4s  |
| nix.ru        | 129,563 RUB     | Нет в наличии | Playwright            | 3.5s   |
| regard.ru     | 144,400 RUB     | В наличии     | Stealth               | 7.9s   |
| kns.ru        | 156,463 RUB     | Нет в наличии | Playwright            | 3.3s   |
| Yandex Market | 287,891 RUB     | В наличии     | yandex_market_special | 16.0s  |

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
| Citilink      | Playwright | [+] OK      | Rate limit (429)       | Delays 90-210s        |
| Yandex Market | Playwright | [+] OK      | -                      | yandex_market_special |
| E-katalog.ru  | HTTP       | [X] Blocked | IP блокировка          | VPN/Proxy/Local       |
| Ozon          | Firefox    | [+] OK      | Headless detection     | ozon_firefox          |
| Avito         | Firefox    | [+] OK      | VPS блокирован         | Firefox на Archbook   |

### Найденные цены (MacBook Pro 16)

| Магазин       | Цена        | Верификация | Наличие        | Метод                 |
|---------------|-------------|-------------|----------------|-----------------------|
| Avito         | 51,799 RUB  | -           | 16 объявлений  | Firefox+xdotool       |
| DNS-Shop      | 62,799+     | -           | 77 моделей     | Firefox+xdotool       |
| Ozon          | 75,024 RUB  | -           | В наличии      | ozon_firefox          |
| centrsvyazi   | 103,500 RUB | 5/5         | Неизвестно     | Playwright            |
| i-ray.ru      | 107,999 RUB | 4/4         | В наличии      | Playwright            |
| Citilink      | 115,990 RUB | -           | В наличии      | citilink_special      |
| nix.ru        | 129,563 RUB | -           | Нет в наличии  | Playwright            |
| regard.ru     | 144,400 RUB | 3/4         | В наличии      | Stealth               |
| kns.ru        | 156,463 RUB | 5/5         | Нет в наличии  | Playwright            |
| Yandex Market | 287,891 RUB | -           | В наличии      | yandex_market_special |

---

## Changelog

| Дата       | Изменение                                                         |
|------------|-------------------------------------------------------------------|
| 2026-01-08 | PS-46 Phase 2: Auto-Import - store_discovery.py, web_search track |
| 2026-01-08 | PS-46 Phase 1: CRUD API - migrations, stores endpoint, health     |
| 2026-01-08 | PS-45: Web Search Price Extraction - Playwright + DuckDuckGo      |
| 2026-01-07 | PS-44: Currency Auto-Collection - systemd timer daily 12:00 MSK   |
| 2026-01-07 | PS-43: Bot UX - inline keyboards for all messages, product lists  |
| 2026-01-07 | PS-42: Analytics - /stats command, command logging, daily reports |
| 2026-01-07 | fix: STDDEV type mismatch in get_price_trends (::float8 cast)     |
| 2026-01-07 | fix: ML predictor SQL (CTE), venv/bin/python, currency_rates      |
| 2026-01-06 | PS-40: Bot Localization - all UI strings translated to Russian    |
| 2026-01-06 | PS-30: Bot Notifications - auto-analytics, command footer hints   |
| 2026-01-06 | Project cleanup: reports moved to docs/reports/, debug files del  |
| 2026-01-06 | PS-39: Market Research - Top 100, discovery, /top, /web commands  |
| 2026-01-06 | PS-8: Telegram Bot - teloxide, 10 commands, standalone mode       |
| 2026-01-05 | PS-38: ML Price Predictions - Random Forest 7-day forecasts       |
| 2026-01-05 | PS-37: Arbitrage Detector - Price differences across stores       |
| 2026-01-05 | PS-36: Analytics Dashboard - 6 endpoints (trends, correlation)    |
| 2026-01-05 | PS-35: Automated Scheduled Scraping - 10-minute intervals         |
| 2026-01-05 | PS-34: Currency Rates Tracking - Dual sources (CBR + open.er)     |
| 2026-01-05 | PS-33: AliExpress Russia added - 9th store with fallback parser   |
| 2026-01-05 | PS-28: API Server - Axum REST API (13 endpoints, analytics ready) |
| 2026-01-04 | PS-29: Scraper Orchestration - Queue + Worker (1,770 lines)       |
| 2026-01-04 | PS-23: Python Bridge - Rust-Python subprocess communication       |
| 2026-01-04 | PS-22: Rust workspace initialized - 5 crates compiled             |
| 2026-01-04 | PS-21: PostgreSQL schema created - 7 tables, 9 stores             |
| 2026-01-03 | Citilink rate limiting исправлен! Задержки 90-210s, 24.4s         |
| 2026-01-03 | Avito работает! Исправлен парсер, 9/9 магазинов, 51,799 RUB       |
| 2026-01-02 | Ozon добавлен! 75,024 RUB через Firefox, 8/9 магазинов            |
| 2026-01-02 | Yandex Market добавлен! 287,891 RUB, 7/8 магазинов работают       |
| 2026-01-02 | ALL TESTS PASSED! 6/6 unified test, все методы работают           |
| 2026-01-02 | test_scrapers.py: citilink_special + firefox xvfb fix             |
| 2026-01-02 | Citilink работает! Playwright + delay, 10 моделей                 |
| 2026-01-02 | Добавлен nix.ru (129,563 RUB), 7/7 магазинов работают             |
| 2026-01-02 | DNS-Shop работает! Firefox + xdotool, 77 моделей                  |
| 2025-12-31 | PS-19: DNS-Shop - IP banned + Qrator, нет доступа                 |
| 2025-12-31 | PS-18: Citilink работает! 6 цен MacBook получено                  |
| 2025-12-31 | PS-17: Деплой на Archbook - i-ray.ru работает!                    |
| 2025-12-31 | PS-16: Advanced bypass - серверная защита, не обойти              |
| 2025-12-31 | PS-15: Stealth не обходит Citilink/DNS/Kotofoto                   |
| 2025-12-31 | Stealth scraper: обход защиты regard.ru (144,400)                 |
| 2025-12-31 | Найден i-ray.ru: 107,999 RUB, В наличии, verified                 |
| 2025-12-31 | find_macbook_price.py: верификация товара (5 checks)              |
| 2025-12-31 | Скрипты поиска MacBook по артикулу Z14V0008D                      |
| 2025-12-31 | Добавлена интеграция 2Captcha (PS-9)                              |
| 2025-12-31 | Тесты Playwright: DNS (401), Citilink (CAPTCHA)                   |
| 2025-12-31 | Создан test_search.py - DuckDuckGo работает                       |
| 2025-12-31 | Создан LEARNING_PATH.md - путь обучения                           |
| 2025-12-31 | PS-1 заблокирован: e-katalog.ru недоступен                        |
| 2025-12-31 | Создан дашборд проекта                                            |
| 2025-12-31 | Начальная документация проекта                                    |

---

## Описание задач

### PS-46: Store Analytics System (арбитраж)

**Статус:** In Progress (Phase 2 Complete)

**Цель:** Система аналитики до 100 магазинов с автоимпортом и арбитражем.

**Прогресс:**

| Phase   | Описание                        | Статус      |
|---------|---------------------------------|-------------|
| Phase 1 | CRUD API для магазинов          | [+] Done    |
| Phase 2 | Автоимпорт из веб-поиска        | [+] Done    |
| Phase 3 | Аналитика арбитража             | [ ] Pending |
| Phase 4 | Автоочистка неактивных          | [ ] Pending |

**Phase 1 - CRUD API (Complete):**
- [+] Migration 007_store_management.sql - расширение stores, store_candidates
- [+] Rust модели: NewStore, UpdateStore, StoreHealthStats, StoreCandidate
- [+] DB операции: create/update/delete store, health tracking
- [+] API endpoints: /api/stores, /api/stores/:id, /api/stores/health

**Phase 2 - Auto-Import (Complete):**
- [+] scripts/store_discovery.py - модуль обнаружения магазинов
  - track_candidate() - трекинг кандидатов из поиска
  - validate_candidate() - валидация 4/5 тестов
  - promote_to_store() - продвижение в полноценный магазин
- [+] scripts/web_search.py - интеграция трекинга
  - Автоматический трекинг неизвестных доменов с ценами
  - Blacklist для агрегаторов и форумов
- [+] Deployed и протестировано на archbook

**Workflow автоимпорта:**
```
Web Search → Price Found → Unknown Domain → Track Candidate
    ↓                                              ↓
3+ успешных извлечений               →        Testing Phase
    ↓                                              ↓
4/5 тестов прошли                    →        Promote to Store
```

**Текущие кандидаты:**
```
store_candidates:
  total: 1
  candidates: 1
  testing: 0
  promoted: 0
  rejected: 0
```

**Файлы:**
- migrations/007_store_management.sql
- scripts/store_discovery.py
- scripts/web_search.py (updated)
- crates/db/src/lib.rs (store CRUD)
- crates/api/src/main.rs (stores endpoints)
- crates/models/src/lib.rs (new models)

**План:** [~/.claude/plans/snuggly-floating-minsky.md]

---

### PS-44: Currency Auto-Collection

**Статус:** Complete (2026-01-07)

**Цель:** Настроить автоматический сбор курсов валют для ML-предиктора.

**Реализовано:**

| Компонент                            | Описание                           |
|--------------------------------------|------------------------------------|
| price-scout-currency-user.service    | Oneshot сервис для сбора курсов    |
| price-scout-currency-user.timer      | Таймер: ежедневно в 12:00 MSK      |
| collect_currency_rates.py            | Python скрипт (ЦБ РФ API)          |

**Расписание:**
- ЦБ РФ обновляет курсы в 11:30 MSK
- Таймер запускается в 12:00 MSK (+5 мин random delay)
- Сохраняет USD и EUR курсы в currency_rates

**Использование курсов:**
- ML-предиктор использует USD/EUR как фичи для прогнозирования цен
- Корреляция курсов валют с ценами на импортную электронику

**Текущие данные:**
```
currency_rates:
 id | currency_code | rate_to_rub | source
  1 | USD           | 78.2267     | cbr_ru
  2 | EUR           | 92.0938     | cbr_ru
```

**Файлы:**
- config/price-scout-currency-user.service
- config/price-scout-currency-user.timer
- scripts/collect_currency_rates.py

---

### PS-43: Bot UX - Inline Keyboards

**Статус:** Complete (2026-01-07)

**Цель:** Улучшить UX бота - добавить inline кнопки ко всем сообщениям, сделать кнопки функциональными.

**Реализовано:**

| Компонент                    | Описание                                    |
|------------------------------|---------------------------------------------|
| stats_keyboard()             | Период (24ч/7д/30д) + быстрые команды       |
| quick_commands_keyboard()    | Цены, Тренды, Арбитраж, Топ                 |
| product_keyboard()           | Цены, Тренды, Прогноз + Арбитраж, Топ, Стат |
| products_list_keyboard()     | Список товаров с кнопками выбора            |

**Callback handlers обновлены:**
- cmd_price: показывает список товаров с кнопками
- cmd_trends: показывает список товаров с кнопками
- price_<id>: выполняет команду /price напрямую
- trends_<id>: выполняет команду /trends напрямую
- predict_<id>: выполняет команду /predict напрямую
- cmd_stats: выполняет команду /stats

**Файлы:**
- crates/bot/src/main.rs (keyboards, callbacks, reply_markup)

---

### PS-42: Analytics System (/stats, command logging)

**Статус:** Complete (2026-01-07)

**Цель:** Добавить команду /stats для просмотра статистики системы, логирование команд.

**Реализовано:**

| Компонент            | Описание                              |
|----------------------|---------------------------------------|
| /stats command       | Статистика за 1д/7д/30д               |
| command_log table    | Логирование всех команд пользователей |
| Inline buttons       | Переключение периодов без ввода       |
| ComprehensiveStats   | Агрегированная статистика системы     |

**Формат /stats:**
```
[i] Price Scout - Статистика (7д)

[SYS] Здоровье системы:
  Скрейпинг: 220/220 (100%)
  Магазины: 4/11 активных

[USR] Пользователи:
  Всего: 1
  Команд за 7д: 15
  Популярные: /stats (8)

[MKT] Рынок:
  Товаров: 5
  Цен собрано: 20

[TOP] Топ магазинов:
  1. kns - 99K (мин)
```

**Файлы:**
- crates/bot/src/main.rs (Command::Stats, format_stats_message)
- crates/db/src/lib.rs (get_comprehensive_stats, log_command)
- migrations/006_command_log.sql

---

### PS-40: Bot Localization (Russian)

**Статус:** Complete (2026-01-06)

**Цель:** Локализовать интерфейс Telegram бота на русский язык для российских пользователей.

**Реализовано:**

| Категория            | Количество | Примеры                                   |
|----------------------|------------|-------------------------------------------|
| Command descriptions | 10         | "Поиск товаров", "Цены товара"            |
| Welcome/Help         | 2          | "Добро пожаловать в Price Scout!"         |
| Error messages       | 15         | "Товар не найден", "Укажите ID товара"    |
| Status messages      | 10         | "Ищу:", "Получаю цены для товара"         |
| Format headers       | 8          | "Найдено товаров:", "Тренды цен"          |
| Hints                | 6          | "Ниже средняя = лучше цена"               |

**Примеры переводов:**

| English                           | Russian                              |
|-----------------------------------|--------------------------------------|
| Welcome to Price Scout Bot!       | Добро пожаловать в Price Scout!      |
| Searching for:                    | Ищу:                                 |
| Product not found                 | Товар не найден                      |
| Arbitrage Opportunities           | Арбитражные возможности              |
| Lower average = better price      | Ниже средняя = лучше цена            |
| Use /price <id> to see prices     | /price <id> - посмотреть цены        |

**Файлы:**
- crates/bot/src/main.rs (~100 строк изменений)

---

### PS-30: Bot Notifications + Command Hints

**Статус:** Complete (2026-01-06)

**Цель:** Добавить автоматические уведомления об аналитике после scraping и подсказки команд во все сообщения бота.

**Реализовано:**

| Компонент              | Описание                                    |
|------------------------|---------------------------------------------|
| NotificationService    | Сервис отправки уведомлений                 |
| notification_poller    | Background task, polling каждые 5 мин       |
| Command hints footer   | Footer со всеми 10 командами в сообщениях   |
| chat_id tracking       | Сохранение chat_id при /start               |
| Batch tracking         | Статистика scraping batch-ов                |

**Новые таблицы БД (migration 005):**
- `scraping_batches` - Статистика batch-ов (total, success, failed, price_changes)
- `notification_log` - История отправленных уведомлений
- `price_change_events` - События изменения цен
- `users.chat_id` - ID чата для уведомлений
- `users.notifications_enabled` - Флаг включения уведомлений

**Формат уведомления:**
```
[!] Price Scout Analytics Update

Summary:
[+] Updated: 45 products
[X] Failed: 3 products

Price Changes (5):
1. [v] MacBook Pro 16: -2.3%
2. [^] iPhone 15 Pro: +1.5%
...

[$$] Arbitrage: 3 opportunities found!
Use /arbitrage to see details

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commands:
/start /help /search /price /trends
/predict /arbitrage /compare /web /top
```

**Файлы:**
- migrations/005_bot_notifications.sql
- crates/bot/src/notifications.rs [NEW]
- crates/bot/src/main.rs (footer, /start, poller)
- crates/models/src/lib.rs (ScrapingBatch, PriceChangeEvent)
- crates/db/src/lib.rs (notification methods)
- crates/scraper/src/worker.rs (batch tracking)

---

### PS-39: Market Research System

**Статус:** Complete (2026-01-06)

**Цель:** Система автоматического обнаружения товаров и рейтинга популярности для поддержания Top 100 товаров в ценовом диапазоне 1,000-15,000 RUB.

**Реализовано:**
- [+] Migration 004_market_research.sql - Новые таблицы и materialized view
- [+] Rust модели: SearchQuery, DiscoveryJob, ProductPopularity
- [+] DB методы: get_top_products, record_search_query, refresh_popularity_metrics
- [+] Python Discovery Engine (scripts/discovery.py)
- [+] API endpoints: /api/market-research/* (4 endpoints)
- [+] Telegram команда /top [limit]
- [+] Hourly discovery scheduler (systemd timer)

**Формула рейтинга популярности (0-100):**

| Критерий     | Вес | Описание                    |
|--------------|-----|-----------------------------|
| Tracking     | 40% | Частота отслеживания        |
| Volatility   | 30% | Волатильность цены          |
| Availability | 20% | Наличие в магазинах         |
| Arbitrage    | 10% | Арбитражный потенциал       |

**Новые таблицы БД:**
- `search_queries` - Отслеживание поисковых запросов
- `discovery_jobs` - Очередь задач обнаружения
- `mv_product_popularity` - Materialized view рейтинга
- `v_top_100_products` - View Top 100 товаров

**Telegram бот (10 команд):**

| Команда                      | Описание                           |
|------------------------------|------------------------------------|
| /start                       | Приветствие                        |
| /help                        | Список команд                      |
| /search <query>              | Поиск товаров                      |
| /price <id>                  | Цены товара                        |
| /trends <id> [days]          | Тренды цен                         |
| /predict <id>                | ML прогноз                         |
| /arbitrage [min_profit]      | Арбитраж                           |
| /compare <id> [days]         | Сравнение магазинов                |
| /web <query>                 | Веб-поиск DuckDuckGo               |
| /top [limit]                 | Top популярных товаров             |

**API endpoints:**
```
GET  /api/market-research/top-100          - Top 100 товаров
GET  /api/market-research/popular-queries  - Популярные запросы
GET  /api/market-research/categories       - Категории товаров
POST /api/market-research/refresh          - Обновить рейтинги
```

**Файлы:**
- migrations/004_market_research.sql
- crates/models/src/lib.rs (Market Research models)
- crates/db/src/lib.rs (Market Research methods)
- crates/api/src/main.rs (Market Research endpoints)
- crates/bot/src/main.rs (/top, /web commands)
- scripts/discovery.py
- config/price-scout-discovery.service
- config/price-scout-discovery.timer

---

### PS-20: Управление Citilink Rate Limiting

**Статус:** Complete (2026-01-04)

**Проблема:**
Citilink имеет агрессивный rate limiting на API уровне:
- HTTP 200, но `effectorValues` пустой объект `{}`
- Товары не загружаются при частых запросах (каждые 5-10 минут)
- Firefox метод НЕ обходит ограничения - блокировка на уровне сервера
- Надежность: 50-70% в зависимости от IP репутации и частоты запросов

**Решение: Вариант 2 - Увеличенные интервалы**

Исключить Citilink из регулярных полных тестов, тестировать только по запросу с интервалом 5+ минут.

**Реализовано:**
- [+] `unstable: bool = False` поле в StoreConfig dataclass
- [+] `unstable=True` для Citilink конфигурации
- [+] `--skip-unstable` флаг для пропуска нестабильных магазинов
- [+] Обновлена `run_all_tests()` для обработки skip_unstable
- [+] `--help` информация с примерами использования
- [+] Документация API_ENDPOINTS.md - Citilink секция обновлена
- [+] Документация PARSING_STRATEGY.md - новая секция "Управление нестабильными магазинами"
- [+] Создан docs/CITILINK_USAGE.md - руководство оператора
- [+] PROJECT_DASHBOARD.md обновлен с PS-20 задачей

**Использование:**
```bash
# Стабильные магазины (8/8)
python test_scrapers.py --skip-unstable

# Citilink отдельно (интервал 5+ мин)
python test_scrapers.py --store=citilink

# Помощь
python test_scrapers.py --help
```

**Файлы:**
- scripts/test_scrapers.py:88 - StoreConfig.unstable поле
- scripts/test_scrapers.py:122 - Citilink unstable=True
- scripts/test_scrapers.py:1395 - run_all_tests() с skip_unstable
- scripts/test_scrapers.py:1511 - --skip-unstable флаг парсинг
- docs/API_ENDPOINTS.md:169-244 - Citilink Rate Limiting документация
- docs/PARSING_STRATEGY.md:227-253 - Управление нестабильными магазинами
- docs/CITILINK_USAGE.md - Полное руководство оператора

**План:** ~/.claude/plans/cheerful-bubbling-catmull.md

---

### PS-19: Фильтрация товаров по характеристикам

**Статус:** Phase 1 Complete (2026-01-03)

**Проблема:**
Парсеры возвращают множество товаров разных конфигураций и берут минимальную цену:
- DNS-Shop: 62,799 RUB из 77 товаров (M4/M4 Pro/M5, 16-48GB RAM, 256-2000GB SSD)
- Citilink: 115,990 RUB из 10 товаров (диапазон 115,990-208,690 RUB)
- Целевая модель (M1 Pro 32GB 512GB) стоит ~156,000 RUB, но не находится

**Решение:**
Двухуровневая система фильтрации:
1. Извлечение характеристик (CPU, RAM, SSD, Screen, Article) из названий товаров
2. Фильтрация по score соответствия (≥80%), возврат топ-3 результатов

**Phase 1 - Реализовано (DNS-Shop):**
- [+] Модуль `specs_filter.py` - ProductSpecs, TargetSpecs, filter_and_rank()
- [+] Unit-тесты `test_specs_filter.py` - 15/15 тестов прошли
- [+] Обновлён `dns_scraper.sh` - извлечение CPU/Screen/RAM/SSD
- [+] Интеграция в `test_scrapers.py` - parse_dns_json() с фильтрацией
- [+] Система скоринга: CPU 40%, RAM 30%, SSD 20%, Screen 10%
- [+] Артикул даёт instant 100% match

**Реальный результат (DNS-Shop, 2026-01-03):**
```
Целевая модель: M1 Pro 32GB 512GB 16"
Найдено товаров: 18 (M4, M4 PRO, M5)
Фильтрация: 0 matches (threshold 80%)
Причина: DNS больше не продаёт M1 Pro (только M4/M5)

Тест с M4 PRO 24GB 512GB 16":
  [+] 3 matches found
  Score: 100% - M4 PRO | 24GB | 512GB | 16"
  Score: 100% - M4 PRO | 24GB | 512GB | 16"
  Score: 90%  - M4 PRO | 24GB | 512GB | 14" (wrong screen)
```

**Вывод:** Фильтрация работает корректно! Система правильно исключает несоответствующие товары.

**Phase 2 - TODO:**
- [ ] Citilink: добавить specs extraction
- [ ] Ozon: добавить specs extraction
- [ ] Avito: добавить specs extraction
- [ ] Остальные 5 магазинов
- [ ] Smart search комбинация (article → specs filter)

**План:** `/home/ryazanov/.claude/plans/cheerful-bubbling-catmull.md`

---

### PS-21: PostgreSQL Schema Implementation

**Статус:** Complete (2026-01-04)

**Цель:** Создать production-ready PostgreSQL схему для price tracking системы.

**Реализовано:**
- [+] `migrations/001_initial_schema.sql` - Полная схема БД (360 строк)
- [+] `migrations/002_seed_stores.sql` - Seed данные для 9 магазинов
- [+] `migrations/apply_migrations.sh` - Скрипт применения миграций
- [+] `migrations/README.md` - Документация
- [+] Применены на Archbook через Ansible

**Схема:**
- 7 таблиц: users, stores, products, store_prices, price_history, trackings, scraping_jobs
- 2 view: best_prices_view, product_price_stats
- 2 триггера: auto_archive_price_history, update_product_timestamp
- Индексы для производительности
- JSONB для гибких характеристик товаров

**Результат:**
```sql
Database: price_scout
Tables created: 7
Views created: 2
Stores seeded: 9 (8 stable, 1 unstable)
PostgreSQL version: 17.5
Server: Archbook (192.168.0.10)
```

**Файлы:**
- `/home/ryazanov/Development/price_scout/migrations/001_initial_schema.sql`
- `/home/ryazanov/Development/price_scout/migrations/002_seed_stores.sql`
- `/home/ryazanov/Development/price_scout/migrations/MIGRATION_REPORT.md`

---

### PS-22: Rust Workspace Bootstrap

**Статус:** Complete (2026-01-04)

**Цель:** Инициализировать Rust workspace с 5 crates для hybrid Rust+Python архитектуры.

**Реализовано:**
- [+] `Cargo.toml` - Workspace configuration
- [+] `crates/models/` - Shared data models (User, Store, Product, StorePrice, etc.)
- [+] `crates/db/` - Database layer (sqlx, connection pooling, operations)
- [+] `crates/api/` - API server placeholder (Axum)
- [+] `crates/bot/` - Telegram bot placeholder (teloxide)
- [+] `crates/scraper/` - Scraper orchestration + Python bridge placeholder
- [+] `README_RUST.md` - Rust documentation
- [+] `.env.example` - Environment variables

**Dependencies:**
- tokio 1.42 (async runtime)
- sqlx 0.8 (PostgreSQL driver)
- axum 0.7 (HTTP server)
- teloxide 0.13 (Telegram bot)
- serde, chrono, anyhow, tracing

**Результат:**
```bash
Workspace compiled: SUCCESS
Crates: 5
Dependencies loaded: 335
Build time: 24.3s (clean)
Check time: 5.7s
```

**Файлы:**
- `/home/ryazanov/Development/price_scout/Cargo.toml`
- `/home/ryazanov/Development/price_scout/README_RUST.md`
- `/home/ryazanov/Development/price_scout/RUST_WORKSPACE_REPORT.md`

---

### PS-23: Python Bridge Implementation

**Статус:** Complete (2026-01-04)

**Цель:** Реализовать Rust ↔ Python bridge для вызова Python scrapers из Rust.

**Реализовано:**
- [+] `scripts/test_scrapers.py` - Added `output_json()` function with `--json` flag
- [+] `crates/scraper/src/python_bridge.rs` - Main bridge implementation (199 lines)
- [+] `run_python_scraper()` - Subprocess spawn + JSON parsing
- [+] `run_python_scraper_with_timeout()` - Custom timeout variant
- [+] Error handling (script not found, execution errors, timeout, JSON parse)
- [+] Test examples: `test_bridge_minimal.rs`, `test_python_bridge.rs`
- [+] Updated `ScraperResponse` model with `method` field

**Архитектура:**
```
Rust Application
  ↓ ScraperRequest {store, query, method}
run_python_scraper()
  ↓ subprocess: python3 test_scrapers.py --json --store=X
Python Script
  ↓ stdout: JSON
serde_json::from_str()
  ↓ ScraperResponse {store, status, price, count, time, error, method}
Rust Application
```

**Тестирование:**
```
[+] Subprocess spawn: OK
[+] JSON output: OK
[+] JSON parsing: OK
[+] Data extraction: OK
[+] Error handling: OK
```

**Performance:**
- Subprocess overhead: ~150-300ms
- JSON parsing: ~1ms
- Total overhead minimal compared to scraping time (3-60s)

**Файлы:**
- `/home/ryazanov/Development/price_scout/crates/scraper/src/python_bridge.rs`
- `/home/ryazanov/Development/price_scout/crates/scraper/examples/test_bridge_minimal.rs`
- `/home/ryazanov/Development/price_scout/PYTHON_BRIDGE_REPORT.md`

**Следующий шаг:** PS-28 - API Server (Axum), PS-30 - Telegram Bot

---

### PS-29: Scraper Orchestration (Queue + Worker)

**Статус:** Complete (2026-01-04)

**Цель:** Реализовать систему оркестрации скрейперов с очередью заданий и фоновым воркером.

**Реализовано:**
- [+] `crates/scraper/src/queue.rs` - Управление очередью заданий (298 строк)
- [+] `crates/scraper/src/worker.rs` - Фоновый воркер обработки (378 строк)
- [+] `crates/scraper/examples/test_worker.rs` - Интеграционный тест (194 строки)
- [+] `PS29_ORCHESTRATION_REPORT.md` - Полная документация (900+ строк)

**ScraperQueue - Управление очередью:**
- Постановка заданий в очередь с приоритетами (enqueue, enqueue_all_stores)
- Получение pending заданий с сортировкой
- Управление статусами (pending → running → completed/failed)
- Повтор неудачных заданий с задержкой
- Статистика очереди (pending/running/completed/failed)
- Очистка старых заданий

**ScraperWorker - Фоновый воркер:**
- Непрерывный цикл опроса с конфигурируемыми интервалами
- Пакетная обработка заданий (batch_size)
- Поиск продуктов и магазинов
- Вызов Python скрейперов через bridge
- Сохранение результатов в БД (upsert store_prices)
- Обработка ошибок
- Graceful shutdown через Arc<AtomicBool>

**WorkerConfig:**
```rust
batch_size: 10           // Заданий за раз
poll_interval: 5s        // Задержка при отсутствии заданий
max_retries: 3          // Максимум попыток
scraper_timeout: 120s   // Таймаут на задание
```

**Архитектура:**
```
Application → ScraperQueue → ScraperWorker → Python Bridge → Scrapers
           (PostgreSQL)    (Background)     (Subprocess)    (Python)
```

**Workflow:**
1. API/Bot вызывает queue.enqueue() или enqueue_all_stores()
2. Worker опрашивает get_pending_jobs()
3. Для каждого задания:
   - Получает product и store из БД
   - Вызывает run_python_scraper()
   - Парсит JSON ответ
   - Сохраняет StorePrice в БД
   - Обновляет статус задания

**Результат:**
```bash
cargo check --workspace
Finished in 2.85s - SUCCESS
```

**Deployment:**
- Systemd service: price-scout-worker.service
- Множественные воркеры для параллельной обработки
- Мониторинг через queue.get_stats()

**Файлы:**
- `/home/ryazanov/Development/price_scout/crates/scraper/src/queue.rs`
- `/home/ryazanov/Development/price_scout/crates/scraper/src/worker.rs`
- `/home/ryazanov/Development/price_scout/crates/scraper/examples/test_worker.rs`
- `/home/ryazanov/Development/price_scout/PS29_ORCHESTRATION_REPORT.md`

**Следующие задачи:**
- PS-30: Telegram Bot (teloxide integration)
- Phase 2: Retry logic, parallel workers, monitoring
- Phase 3: API improvements (pagination, filtering, proper status codes)

---

### PS-28: API Server (Axum REST endpoints)

**Статус:** Complete (2026-01-05)

**Цель:** Реализовать REST API сервер для Price Scout с полным набором endpoints.

**Реализовано:**
- [+] `crates/api/src/main.rs` - API server (267 строк)
- [+] `crates/api/examples/test_api.rs` - Test client (138 строк)
- [+] `docs/REST_API.md` - Полная документация API (550+ строк)
- [+] `PS28_API_SERVER_REPORT.md` - Отчёт о реализации

**REST API Endpoints:**
1. `GET /health` - Health check
2. `GET /api/stores` - Список всех магазинов
3. `GET /api/products/:id` - Детали продукта
4. `GET /api/products/:id/prices` - Цены продукта по магазинам
5. `POST /api/search` - Поиск продуктов
6. `POST /api/products/:id/scrape` - Запуск scraping
7. `GET /api/queue/stats` - Статистика очереди

**Особенности:**
- Application state (Database + ScraperQueue)
- Кастомная обработка ошибок с JSON responses
- CORS поддержка
- Type-safe request/response models
- Интеграция с PS-27 (Database) и PS-29 (Queue)

**Архитектура:**
```
HTTP Client → Axum Router → Handler → Database/Queue → JSON Response
```

**Результат компиляции:**
```bash
cargo check --package price-scout-api
Finished in 1.05s - SUCCESS (0 warnings)
```

**Использование:**
```bash
# Запуск сервера
export DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout
cargo run --bin price-scout-api

# Тестирование
cargo run --example test_api

# curl примеры
curl http://localhost:3000/health
curl http://localhost:3000/api/stores
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "MacBook"}'
curl -X POST http://localhost:3000/api/products/1/scrape \
  -H "Content-Type: application/json" \
  -d '{"priority": 8}'
```

**Deployment:**
- Systemd service: `price-scout-api.service`
- Слушает на `0.0.0.0:3000`
- Auto-restart на failure

**Интеграция:**
- PS-27 (Database): Все endpoints используют Database operations
- PS-29 (Queue): Scrape endpoint использует ScraperQueue
- PS-30 (Bot, Future): Telegram bot будет использовать этот API

**Файлы:**
- `/home/ryazanov/Development/price_scout/crates/api/src/main.rs`
- `/home/ryazanov/Development/price_scout/crates/api/examples/test_api.rs`
- `/home/ryazanov/Development/price_scout/docs/REST_API.md`
- `/home/ryazanov/Development/price_scout/PS28_API_SERVER_REPORT.md`

**Production Readiness:** 85%
- [+] Core functionality: Complete
- [+] Error handling: Good
- [+] Documentation: Excellent
- [~] Testing: Manual (нужны integration tests)
- [-] Security: Needs authentication (Phase 4)

**Следующий шаг:** PS-30 - Telegram Bot (teloxide integration)

---

### PS-33: Add AliExpress Russia Marketplace

**Статус:** Complete (2026-01-05)

**Цель:** Добавить AliExpress.ru как 9-й marketplace с обходом CAPTCHA защиты.

**Реализовано:**
- [+] StoreConfig для AliExpress в test_scrapers.py
- [+] Fallback DOM parser (window.runParams не найден)
- [+] Playwright Stealth метод (5s задержки)
- [+] 3 stability tests passed
- [+] Migration 002_seed_stores.sql updated (unstable=true)
- [+] TEST_ARTICLE bug fixed (empty string → fallback to query)

**Результат:**
```
Store: aliexpress
Method: playwright_stealth
Price: 62,110 RUB
Status: PASS (3/3 stability tests)
Marked: unstable=true (needs more testing)
```

**Особенности:**
- window.runParams extraction не работает (перешли на DOM parsing)
- XPath селекторы с fallback цепочкой
- 5s задержки между запросами для обхода rate limiting
- Артикул TEST_ARTICLE → None для корректного fallback

**Файлы:**
- scripts/test_scrapers.py:158 - AliExpress StoreConfig
- migrations/002_seed_stores.sql - AliExpress seed data

---

### PS-34: Currency Rates Tracking

**Статус:** Complete (2026-01-05)

**Цель:** Реализовать отслеживание курсов валют (USD/EUR) из двух источников для корреляционного анализа.

**Реализовано:**
- [+] Migration 003_add_currency_rates.sql - Схема БД
- [+] scripts/collect_currency_rates.py - Python скрипт для сбора курсов
- [+] crates/db/src/lib.rs - Currency methods (save, get_latest, get_history)
- [+] Dual sources: ЦБ РФ (cbr_ru) + open.er-api.com (open_er)

**Database Schema:**
```sql
CREATE TABLE currency_rates (
    id BIGSERIAL PRIMARY KEY,
    currency_code TEXT NOT NULL CHECK (currency_code IN ('USD', 'EUR')),
    rate_to_rub NUMERIC(10, 4) NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('cbr_ru', 'open_er')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**API Sources:**
- **ЦБ РФ**: https://www.cbr-xml-daily.ru/daily_json.js (ежедневно 11:30 МСК)
- **open.er-api.com**: https://open.er-api.com/v6/latest/USD (реалтайм, каждые 10 мин)

**Использование:**
```bash
# Test dry run
python3 scripts/collect_currency_rates.py --dry-run

# Collect and save
python3 scripts/collect_currency_rates.py
```

**Файлы:**
- migrations/003_add_currency_rates.sql
- scripts/collect_currency_rates.py
- crates/db/src/lib.rs (currency methods)

---

### PS-35: Automated Scheduled Scraping

**Статус:** Complete (2026-01-05)

**Цель:** Автоматизировать сбор цен каждые 10 минут для товаров в диапазоне 5,000-15,000 RUB.

**Реализовано:**
- [+] crates/scraper/src/scheduler.rs - Scheduler module (188 строк)
- [+] crates/scraper/src/bin/worker.rs - Continuous worker binary
- [+] crates/scraper/src/bin/scheduler.rs - One-shot scheduler binary
- [+] WorkerConfig poll_interval = 600s (10 минут)
- [+] SchedulerConfig price range (500,000-1,500,000 kopecks)
- [+] config/price-scout-worker.service - Systemd service
- [+] config/price-scout-scheduler.timer - Systemd timer

**Архитектура:**
```
Scheduler (one-shot)                    Worker (continuous)
     ↓                                        ↓
enqueue_all_products()               poll_pending_jobs()
     ↓                                        ↓
ScraperQueue (PostgreSQL)            process_batch()
                                             ↓
                                    Python Bridge → Scrapers
```

**Два режима деплоя:**
1. **Continuous Worker**: Непрерывный опрос очереди каждые 10 минут
2. **Timer-based Scheduler**: Systemd timer запускает scheduler каждые 10 минут

**Использование:**
```bash
# Continuous worker (рекомендуется)
systemctl enable --now price-scout-worker.service

# Timer-based (альтернатива)
systemctl enable --now price-scout-scheduler.timer
```

**Файлы:**
- crates/scraper/src/scheduler.rs
- crates/scraper/src/bin/worker.rs
- crates/scraper/src/bin/scheduler.rs
- config/price-scout-worker.service
- config/price-scout-scheduler.timer

---

### PS-36: Analytics Dashboard

**Статус:** Complete (2026-01-05)

**Цель:** Реализовать аналитическую платформу для анализа цен, корреляций и рыночных трендов.

**Реализовано:**
- [+] 4 SQL analytics queries в crates/db/src/lib.rs:
  - get_price_trends() - Дневная агрегация цен с volatility (STDDEV)
  - calculate_price_currency_correlation() - Pearson correlation
  - get_store_comparison() - Сравнение магазинов по ценам и доступности
  - get_market_overview() - Агрегированная статистика рынка
- [+] 4 REST API endpoints в crates/api/src/main.rs:
  - GET /api/analytics/price-trends/:id?days=7
  - GET /api/analytics/currency-correlation/:id?currency=USD&days=30
  - GET /api/analytics/store-comparison/:id?days=30
  - GET /api/analytics/market-overview?min_price=5000&max_price=15000
- [+] docs/ANALYTICS_API.md - Полная документация (11KB)
- [+] docs/REST_API.md - Обновлена с новыми endpoints

**Ключевые возможности:**
- **Price Trends**: Отслеживание изменений цен во времени с volatility index
- **Currency Correlation**: Выявление импортных товаров (высокая корреляция с USD/EUR)
- **Store Comparison**: Поиск лучших магазинов (цена + доступность)
- **Market Overview**: Общая картина рынка в ценовом диапазоне

**Использование:**
```bash
# Price trends
curl "http://localhost:3000/api/analytics/price-trends/1?days=30" | jq

# Currency correlation
curl "http://localhost:3000/api/analytics/currency-correlation/1?currency=USD" | jq

# Store comparison
curl "http://localhost:3000/api/analytics/store-comparison/1?days=7" | jq

# Market overview
curl "http://localhost:3000/api/analytics/market-overview?min_price=5000&max_price=15000" | jq
```

**Файлы:**
- crates/db/src/lib.rs (analytics methods)
- crates/api/src/main.rs (analytics endpoints)
- docs/ANALYTICS_API.md

---

### PS-37: Arbitrage Detector

**Статус:** Complete (2026-01-05)

**Цель:** Обнаружение арбитражных возможностей (разница цен между магазинами на один товар).

**Реализовано:**
- [+] find_arbitrage_opportunities() SQL query в crates/db/src/lib.rs
- [+] GET /api/arbitrage?min_profit=10 REST endpoint
- [+] docs/ANALYTICS_API.md updated с arbitrage section
- [+] CTE-based query с cross-store joins

**SQL Logic:**
```sql
WITH price_pairs AS (
  SELECT
    product_id,
    buy_store_id,
    buy_price,
    sell_store_id,
    sell_price,
    (sell_price - buy_price) as profit,
    ((sell_price - buy_price)::float / buy_price::float * 100) as profit_percent
  FROM products
  JOIN store_prices sp1 ON product_id = sp1.product_id
  JOIN store_prices sp2 ON product_id = sp2.product_id
  WHERE sp1.store_id != sp2.store_id
    AND sell_price > buy_price
    AND profit_percent >= min_profit
)
SELECT * FROM price_pairs
ORDER BY profit_percent DESC LIMIT 100
```

**Response Example:**
```json
{
  "opportunities": [
    {
      "product_name": "MacBook Pro 16\" M1 Pro",
      "buy_store": "dns-shop",
      "buy_price": 10500000,
      "sell_store": "ozon",
      "sell_price": 12000000,
      "profit_percent": 14.29
    }
  ],
  "count": 1
}
```

**Use Cases:**
- Поиск лучших предложений для покупателей
- Мониторинг конкурентных цен для ритейлеров
- Выявление ошибок ценообразования
- Анализ эффективности рынка

**Файлы:**
- crates/db/src/lib.rs:716-792
- crates/api/src/main.rs:502-548
- docs/ANALYTICS_API.md:210-287

---

### PS-38: ML Price Predictions (Random Forest)

**Статус:** Complete (2026-01-05)

**Цель:** Прогнозирование цен на 7 дней вперёд с помощью машинного обучения.

**Реализовано:**
- [+] scripts/ml_predictor.py - Python ML trainer/predictor (14KB)
- [+] GET /api/analytics/predictions/:id REST endpoint
- [+] docs/ANALYTICS_API.md updated с predictions section
- [+] scripts/ML_PREDICTIONS_README.md - Полная документация (11KB)

**ML Model:**
- **Algorithm**: Random Forest Regressor (100 trees, max depth 10)
- **Training split**: 80/20 (time-ordered, no shuffle)
- **Features** (7):
  1. price_7d_avg - 7-дневная скользящая средняя
  2. price_30d_avg - 30-дневная скользящая средняя
  3. price_trend - Изменение цены за 7 дней
  4. usd_rate - Курс USD → RUB
  5. eur_rate - Курс EUR → RUB
  6. day_of_week - День недели (0=Mon, 6=Sun)
  7. days_since_start - Дни с начала наблюдений
- **Target**: Цена через 7 дней
- **Confidence interval**: ±2σ (~95%)
- **Model persistence**: models/product_{id}_predictor.pkl

**Usage:**
```bash
# Train model
python3 scripts/ml_predictor.py train --product-id 1

# Predict via CLI
python3 scripts/ml_predictor.py predict --product-id 1 --output json

# Predict via API
curl "http://localhost:3000/api/analytics/predictions/1" | jq
```

**Response Example:**
```json
{
  "product_id": 1,
  "current_price": 10500000,
  "predicted_price": 10350000,
  "prediction_horizon_days": 7,
  "lower_bound": 10100000,
  "upper_bound": 10600000,
  "confidence": "medium",
  "model_accuracy": {
    "r2_score": 0.78,
    "mae_rub": 1250.32
  }
}
```

**Confidence Levels:**
- **high**: R² > 0.7 (надёжные прогнозы)
- **medium**: R² 0.5-0.7 (умеренная точность)
- **low**: R² < 0.5 (ограниченная точность)

**Requirements:**
- Minimum 20 days of historical data
- 60+ days recommended for better accuracy
- Currency rate data for same period
- Python packages: pandas, scikit-learn, psycopg2-binary, joblib

**Файлы:**
- scripts/ml_predictor.py (ML trainer/predictor)
- scripts/ML_PREDICTIONS_README.md (documentation)
- crates/api/src/main.rs:576-608 (API endpoint)
- docs/ANALYTICS_API.md:290-414 (API specs)

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
