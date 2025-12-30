# Price Scout

**Разведчик цен** - Telegram-бот для мониторинга и сравнения цен на товары с различных маркетплейсов и интернет-магазинов.

## Описание

Price Scout парсит ценовой агрегатор E-katalog.ru, который уже собирает цены из сотен магазинов (Wildberries, Ozon, DNS, М.Видео и др.), и предоставляет удобный интерфейс через Telegram-бот.

## Возможности

- Поиск товаров по названию
- Сравнение цен в разных магазинах
- Отслеживание изменения цен
- Уведомления о снижении цены
- История цен

## Технологический стек

- **Язык:** Rust 1.83+
- **Web Framework:** Axum
- **Telegram:** teloxide
- **База данных:** PostgreSQL + Redis
- **Парсинг:** scraper + chromiumoxide

## Быстрый старт

### Требования

- Rust 1.83+
- PostgreSQL 16+
- Redis 7+
- Docker (опционально)

### Установка

```bash
# Клонирование
git clone <repo-url>
cd price_scout

# Копирование конфигурации
cp .env.example .env
# Отредактируйте .env и укажите TELEGRAM_BOT_TOKEN

# Сборка
cargo build --release

# Запуск
./target/release/price_scout
```

### Docker

```bash
docker-compose up -d
```

## Команды бота

| Команда           | Описание                                   |
|-------------------|--------------------------------------------|
| /start            | Приветствие и справка                      |
| /search <query>   | Поиск товара по названию                   |
| /prices <id>      | Цены на товар в разных магазинах           |
| /track <id>       | Добавить товар в отслеживание              |
| /list             | Список отслеживаемых товаров               |
| /remove <id>      | Удалить из отслеживания                    |
| /help             | Справка                                    |

## Документация

- [Roadmap](docs/ROADMAP.md) - План развития
- [Tech Stack](docs/TECH_STACK.md) - Технологии и архитектура
- [API Research](docs/API_RESEARCH.md) - Исследование API
- [Parsing Strategy](docs/PARSING_STRATEGY.md) - Стратегия парсинга

## Лицензия

MIT
