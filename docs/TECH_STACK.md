# Price Scout - Технологический стек (Rust)

## Выбор: Axum + PostgreSQL + Telegram Bot + E-katalog Parser

---

## Обзор технологий

### Backend

| Компонент     | Технология   | Обоснование                                         |
|---------------|--------------|-----------------------------------------------------|
| Язык          | Rust 1.83+   | Производительность, безопасность памяти, надёжность |
| Web Framework | Axum 0.8     | От команды Tokio, отличная эргономика, tower совм.  |
| Runtime       | Tokio        | Стандарт async runtime для Rust                     |
| Сериализация  | serde        | Де-факто стандарт для JSON/YAML/TOML                |
| Валидация     | validator    | Декларативная валидация структур                    |

### База данных

| Компонент  | Технология    | Обоснование                                  |
|------------|---------------|----------------------------------------------|
| Primary DB | PostgreSQL 16 | Надёжность, JSON поддержка, отличные индексы |
| ORM/Query  | SQLx          | Compile-time проверка SQL, async, без ORM    |
| Миграции   | sqlx-cli      | Встроено в SQLx                              |
| Pool       | sqlx::PgPool  | Async connection pooling                     |
| Cache      | Redis         | Кэширование результатов поиска               |

### Telegram Bot

| Компонент | Технология | Обоснование                              |
|-----------|------------|------------------------------------------|
| Framework | teloxide   | Самая популярная Rust библиотека для TG  |
| Dialogues | teloxide   | FSM для диалогов встроен                 |

### Парсинг (E-katalog)

| Компонент       | Технология     | Обоснование                             |
|-----------------|----------------|-----------------------------------------|
| Browser Engine  | chromiumoxide  | Headless Chrome для Rust                |
| HTTP Client     | reqwest        | Для прямых API запросов                 |
| HTML Parsing    | scraper        | CSS селекторы, на базе html5ever        |
| JSON Parsing    | serde_json     | Стандарт для JSON в Rust                |

### Планировщик задач

| Компонент | Технология         | Обоснование                            |
|-----------|--------------------|----------------------------------------|
| Scheduler | tokio-cron         | Cron-like планирование на tokio        |
| или       | apalis             | Job queue с поддержкой PostgreSQL      |

### DevOps

| Компонент   | Технология                   | Обоснование                      |
|-------------|------------------------------|----------------------------------|
| Контейнеры  | Docker                       | Стандарт контейнеризации         |
| Оркестрация | Docker Compose               | Для разработки и простого деплоя |
| CI/CD       | GitHub Actions               | Интеграция с GitHub              |
| Логирование | tracing + tracing-subscriber | Структурированные логи           |

---

## Структура проекта

```
price_scout/
├── src/
│   ├── main.rs                 # Точка входа
│   ├── lib.rs                  # Библиотека (для тестов)
│   ├── config.rs               # Конфигурация
│   │
│   ├── api/                    # REST API (Axum) - опционально
│   │   ├── mod.rs
│   │   ├── router.rs
│   │   └── handlers/
│   │       ├── mod.rs
│   │       ├── products.rs
│   │       └── health.rs
│   │
│   ├── bot/                    # Telegram Bot (teloxide)
│   │   ├── mod.rs
│   │   ├── commands.rs         # /search, /track, /list
│   │   ├── callbacks.rs        # Inline кнопки
│   │   ├── dialogues.rs        # FSM диалоги
│   │   └── keyboards.rs        # Inline клавиатуры
│   │
│   ├── parser/                 # Парсер E-katalog
│   │   ├── mod.rs
│   │   ├── ekatalog.rs         # Основной парсер
│   │   ├── models.rs           # SearchResult, ProductPrice
│   │   └── error.rs            # Ошибки парсинга
│   │
│   ├── services/               # Бизнес-логика
│   │   ├── mod.rs
│   │   ├── search.rs           # Поиск товаров
│   │   ├── tracking.rs         # Отслеживание
│   │   ├── notification.rs     # Уведомления
│   │   └── cache.rs            # Работа с Redis
│   │
│   ├── db/                     # База данных
│   │   ├── mod.rs
│   │   ├── models.rs           # User, Product, Tracking
│   │   └── queries/
│   │       ├── mod.rs
│   │       ├── users.rs
│   │       ├── products.rs
│   │       └── trackings.rs
│   │
│   └── utils/                  # Утилиты
│       ├── mod.rs
│       └── text.rs             # Форматирование текста
│
├── migrations/                 # SQL миграции
│   ├── 001_init.sql
│   └── ...
│
├── tests/
│   ├── common/mod.rs
│   ├── parser_test.rs
│   └── bot_test.rs
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── docs/
│   ├── README.md
│   ├── ROADMAP.md
│   ├── TECH_STACK.md
│   ├── MARKET_RESEARCH.md
│   ├── API_RESEARCH.md
│   └── PARSING_STRATEGY.md
│
├── .env.example
├── .gitignore
├── Cargo.toml
└── README.md
```

---

## Модели данных

### User

```rust
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct User {
    pub id: i64,
    pub telegram_id: i64,           // Unique, indexed
    pub username: Option<String>,
    pub first_name: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}
```

### Product (из E-katalog)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Product {
    pub id: i64,
    pub ekatalog_id: String,         // ID на E-katalog
    pub name: String,
    pub category: Option<String>,
    pub image_url: Option<String>,
    pub min_price: Decimal,
    pub max_price: Decimal,
    pub shops_count: i32,
    pub ekatalog_url: String,
    pub last_checked_at: DateTime<Utc>,
    pub created_at: DateTime<Utc>,
}
```

### ShopPrice (цена в конкретном магазине)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShopPrice {
    pub id: i64,
    pub product_id: i64,
    pub shop_name: String,
    pub price: Decimal,
    pub shop_url: String,
    pub in_stock: bool,
    pub recorded_at: DateTime<Utc>,
}
```

### Tracking

```rust
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct Tracking {
    pub id: i64,
    pub user_id: i64,
    pub product_id: i64,
    pub target_price: Option<Decimal>,
    pub notify_on_any_drop: bool,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
}
```

### PriceHistory

```rust
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct PriceHistory {
    pub id: i64,
    pub product_id: i64,
    pub min_price: Decimal,
    pub max_price: Decimal,
    pub shops_count: i32,
    pub recorded_at: DateTime<Utc>,
}
```

---

## Зависимости (Cargo.toml)

```toml
[package]
name = "price-scout"
version = "0.1.0"
edition = "2021"
rust-version = "1.83"
description = "Price comparison Telegram bot using E-katalog"

[dependencies]
# Async runtime
tokio = { version = "1.42", features = ["full"] }

# Web framework (optional, for future API)
axum = { version = "0.8", features = ["macros"] }
tower = "0.5"
tower-http = { version = "0.6", features = ["cors", "trace"] }

# Database
sqlx = { version = "0.8", features = [
    "runtime-tokio",
    "postgres",
    "chrono",
    "rust_decimal",
    "json"
]}

# Cache
redis = { version = "0.27", features = ["tokio-comp", "json"] }

# Telegram
teloxide = { version = "0.13", features = ["macros"] }

# HTTP client & parsing
reqwest = { version = "0.12", features = ["json", "gzip", "cookies"] }
scraper = "0.21"

# Browser automation (for complex pages)
chromiumoxide = { version = "0.7", features = ["tokio-runtime"] }
# или fantoccini для WebDriver

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Utils
chrono = { version = "0.4", features = ["serde"] }
rust_decimal = { version = "1.36", features = ["serde"] }
url = "2.5"
thiserror = "2.0"
anyhow = "1.0"

# Config
dotenvy = "0.15"
config = "0.14"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }

# Scheduler (Phase 2)
tokio-cron-scheduler = "0.13"

[dev-dependencies]
tokio-test = "0.4"
```

---

## Telegram Bot команды (MVP)

| Команда              | Описание                                   |
|----------------------|--------------------------------------------|
| /start               | Приветствие и краткая справка              |
| /search <query>      | Поиск товара по названию                   |
| /prices <id>         | Показать цены на товар в разных магазинах  |
| /track <id>          | Добавить товар в отслеживание              |
| /list                | Список отслеживаемых товаров               |
| /remove <id>         | Удалить товар из отслеживания              |
| /help                | Справка по командам                        |

---

## Переменные окружения

```env
# Application
RUST_LOG=info,price_scout=debug
APP_ENV=development

# Database
DATABASE_URL=postgres://user:pass@localhost:5432/price_scout

# Redis
REDIS_URL=redis://localhost:6379

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token

# Parser settings
PARSER_REQUEST_TIMEOUT_SECS=30
PARSER_DELAY_MIN_MS=2000
PARSER_DELAY_MAX_MS=5000
CACHE_TTL_SECS=3600
```

---

## API Endpoints (опционально, Phase 4)

| Method | Endpoint                      | Описание                    |
|--------|-------------------------------|-----------------------------|
| GET    | /health                       | Health check                |
| GET    | /api/v1/search                | Поиск товаров               |
| GET    | /api/v1/products/{id}         | Информация о товаре         |
| GET    | /api/v1/products/{id}/prices  | Цены по магазинам           |
| GET    | /api/v1/products/{id}/history | История цен                 |
