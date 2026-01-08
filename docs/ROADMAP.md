# Price Scout - Roadmap

> Последнее обновление: 2026-01-08

## Обзор проекта

**Price Scout** ("Разведчик цен") - Telegram-бот для мониторинга и сравнения цен на товары через парсинг интернет-магазинов.

**Архитектура:** Hybrid Rust + Python система с прямым парсингом 9+ магазинов (DNS, Ozon, Citilink, Yandex Market, AliExpress и др.).

---

## Фазы развития

### Фаза 1: MVP (Минимальный жизнеспособный продукт)

**Цель:** Базовый функционал поиска и сравнения цен через Telegram-бот

| Компонент        | Описание                                            | Статус   |
|------------------|-----------------------------------------------------|----------|
| Парсеры          | 9 магазинов (DNS, Ozon, Citilink, YMarket, etc.)    | [+] Done |
| Telegram-бот     | 11 команд, inline keyboards, локализация RU         | [+] Done |
| База данных      | PostgreSQL 17, 10 миграций, 7+ таблиц               | [+] Done |
| Кэширование      | Redis (опционально)                                 | [~] TODO |

**Результат:** Работающий Telegram-бот для поиска и сравнения цен

---

### Фаза 2: Отслеживание и уведомления

**Цель:** Автоматический мониторинг цен и уведомления

| Компонент        | Описание                                            | Статус   |
|------------------|-----------------------------------------------------|----------|
| Планировщик      | Автоматический сбор каждые 10 минут (systemd)       | [+] Done |
| Уведомления      | Smart Price Alerts с анализом причины               | [+] Done |
| История цен      | price_history таблица + /trends команда             | [+] Done |
| Избранное        | Auto-subscribe при поиске, user_price_alerts        | [+] Done |

---

### Фаза 3: Расширение источников

**Цель:** Дополнительные источники + аналитика

| Компонент        | Описание                                            | Статус   |
|------------------|-----------------------------------------------------|----------|
| Yandex Market    | Playwright + Stealth bypass                         | [+] Done |
| Ozon             | Firefox + xdotool (headful)                         | [+] Done |
| Аналитика        | 6 endpoints (trends, correlation, arbitrage)        | [+] Done |
| Статистика       | /stats команда, command logging                     | [+] Done |

---

### Фаза 4: Умные функции

**Цель:** ML-прогнозирование + рекомендации

| Компонент            | Описание                                        | Статус   |
|----------------------|-------------------------------------------------|----------|
| ML прогноз цены      | Random Forest, 7-дневные прогнозы               | [+] Done |
| Умные уведомления    | Currency correlation analysis в алертах         | [+] Done |
| Арбитраж             | /arbitrage - поиск разницы цен между магазинами | [+] Done |
| Store Analytics      | Auto-import, health tracking, auto-cleanup      | [+] Done |
| Web Search Filter    | Category URL filter, relevance check, stemming  | [+] Done |

---

## Архитектура системы

```
┌─────────────────┐     ┌─────────────────┐
│  Telegram Bot   │     │   REST API      │
│  (teloxide)     │     │   (Axum)        │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │     Rust Core         │
         │  (models, db, queue)  │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼───┐     ┌──────▼──────┐    ┌────▼────┐
│ PostgreSQL │ │ Python Bridge │  │ Scheduler │
│  17        │ │ (subprocess)  │  │ (systemd) │
└───────────┘ └──────┬──────┘    └───────────┘
                     │
         ┌───────────▼───────────┐
         │   Python Scrapers     │
         │  (Playwright/Firefox) │
         └───────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │         │         │         │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│  DNS  │ │ Ozon  │ │YMarket│ │ +6    │
└───────┘ └───────┘ └───────┘ └───────┘
```

**База данных PostgreSQL:**
- users, products, stores, store_prices
- price_history, currency_rates, command_log
- user_price_alerts, store_candidates
- 10 миграций, views, functions

---

## Реализованный функционал

### Core Features (Фаза 1-2)

- [+] 9 парсеров магазинов (DNS, Ozon, Citilink, YMarket, AliExpress, etc.)
- [+] Telegram-бот с 11 командами
- [+] PostgreSQL хранение с историей цен
- [+] Автоматический сбор цен (каждые 10 минут)
- [+] Smart Price Alerts с auto-subscribe
- [+] Inline keyboards во всех сообщениях

### Analytics (Фаза 3)

- [+] Price trends (волатильность, тренды)
- [+] Currency correlation (USD/EUR vs цены)
- [+] Store comparison (сравнение магазинов)
- [+] Market overview (обзор рынка)
- [+] /stats команда с логированием

### Smart Features (Фаза 4)

- [+] ML прогнозирование (Random Forest, 7 дней)
- [+] Arbitrage detector (разница цен 10%+)
- [+] Store auto-import из веб-поиска
- [+] Web search filtering (category URLs, relevance)
- [+] Currency analysis в price alerts

### Backlog (низкий приоритет)

- [~] Redis кэширование (PS-7)
- [~] 2Captcha live testing (PS-10)
- [ ] Web-интерфейс
- [ ] Платные тарифы

---

## Команды Telegram-бота

| Команда                 | Описание                                 |
|-------------------------|------------------------------------------|
| /start                  | Приветствие и краткая справка            |
| /help                   | Справка по командам                      |
| /search <query>         | Поиск товаров                            |
| /price <id>             | Цены товара по магазинам                 |
| /trends <id> [days]     | Тренды цен                               |
| /predict <id>           | ML прогноз на 7 дней                     |
| /arbitrage [min_profit] | Арбитражные возможности                  |
| /compare <id> [days]    | Сравнение магазинов                      |
| /web <query>            | Веб-поиск через DuckDuckGo               |
| /top [limit]            | Топ популярных товаров                   |
| /stats [period]         | Статистика системы                       |

---

## Пример использования

```
Пользователь: /search MacBook Pro 16

Бот: Ищу: MacBook Pro 16...

Найдено товаров: 3

1. MacBook Pro 16 M4 Pro (ID: 1)
   Мин: 149,990 RUB (DNS)
   Макс: 189,990 RUB (Ozon)

[Цены] [Тренды] [Прогноз]
[Арбитраж] [Топ] [Статистика]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/price <id> - посмотреть цены
/trends <id> - тренды цен
```
