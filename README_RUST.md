# Price Scout - Rust Workspace

Hybrid Rust + Python architecture for price tracking and scraping.

## Project Structure

```
price_scout/
├── Cargo.toml                  # Workspace root
├── crates/
│   ├── models/                 # Shared data models
│   ├── db/                     # PostgreSQL database layer (sqlx)
│   ├── api/                    # Axum REST API server
│   ├── bot/                    # teloxide Telegram bot
│   └── scraper/                # Scraper orchestration + Python bridge
├── scripts/                    # Python scrapers (existing)
└── migrations/                 # PostgreSQL migrations
```

## Crates

### price-scout-models

**Purpose**: Shared data structures

**Key types**:
- `User` - Telegram bot users
- `Store` - Marketplace configurations
- `Product` - Product catalog with JSONB specs
- `StorePrice` - Current prices
- `PriceHistory` - Historical price data
- `Tracking` - User price subscriptions
- `ScrapingJob` - Job queue
- `ScraperRequest` / `ScraperResponse` - Python bridge communication

**Dependencies**: serde, chrono, sqlx

### price-scout-db

**Purpose**: Database operations with PostgreSQL

**Key features**:
- Connection pooling (sqlx)
- Store operations
- Product CRUD
- Price tracking
- User management
- Job queue

**Example**:
```rust
use price_scout_db::Database;

let db = Database::connect("postgresql://...").await?;
let stores = db.get_stable_stores().await?;
```

**Dependencies**: models, sqlx, tokio

### price-scout-scraper

**Purpose**: Python scraper orchestration

**Status**: In development (PS-23)

**Planned features**:
- Python subprocess bridge
- JSON communication
- Job queue processing

**Dependencies**: models, db, tokio

### price-scout-api

**Purpose**: REST API server (Axum)

**Status**: Planned (Phase 3, Week 5)

**Planned endpoints**:
- `GET /api/stores`
- `GET /api/products/:id/prices`
- `POST /api/search`

**Dependencies**: models, db, axum, tower

### price-scout-bot

**Purpose**: Telegram bot (teloxide)

**Status**: Planned (Phase 4, Week 7)

**Planned commands**:
- `/start` - Welcome message
- `/search` - Search products
- `/track` - Track price
- `/list` - List tracked products

**Dependencies**: models, db, teloxide

## Development

### Prerequisites

1. Rust 1.75+ (edition 2021)
2. PostgreSQL 17.5+ on Archbook
3. Python 3.10+ (for scrapers)

### Setup

```bash
# Clone repository
git clone <repo>
cd price_scout

# Apply database migrations
./migrations/apply_migrations.sh

# Build Rust workspace
cargo build

# Run tests
cargo test
```

### Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout

# Logging
RUST_LOG=info,price_scout=debug

# Application
APP_ENV=development
```

### Testing Database Connection

```bash
# Test from local machine
DATABASE_URL=postgresql://postgres@192.168.0.10:5432/price_scout \
  cargo run --example test_connection

# Test on Archbook
DATABASE_URL=postgresql://postgres@localhost:5432/price_scout \
  cargo run --example test_connection
```

## Database Schema

| Table          | Purpose                       |
|----------------|-------------------------------|
| users          | Telegram bot users            |
| stores         | Marketplace configurations    |
| products       | Product catalog (JSONB specs) |
| store_prices   | Current prices                |
| price_history  | Historical prices             |
| trackings      | User subscriptions            |
| scraping_jobs  | Job queue                     |

## Dependencies

### Core

| Crate              | Version | Purpose                |
|--------------------|---------|------------------------|
| tokio              | 1.42    | Async runtime          |
| serde              | 1.0     | Serialization          |
| sqlx               | 0.8     | PostgreSQL driver      |
| chrono             | 0.4     | Date/time              |
| anyhow             | 1.0     | Error handling         |

### Web Framework

| Crate              | Version | Purpose                |
|--------------------|---------|------------------------|
| axum               | 0.7     | HTTP server            |
| tower              | 0.5     | Middleware             |
| tower-http         | 0.6     | HTTP utilities         |

### Telegram Bot

| Crate              | Version | Purpose                |
|--------------------|---------|------------------------|
| teloxide           | 0.13    | Telegram bot framework |

### Utilities

| Crate              | Version | Purpose                |
|--------------------|---------|------------------------|
| tracing            | 0.1     | Logging                |
| dotenv             | 0.15    | Environment variables  |
| uuid               | 1.11    | UUID generation        |

## Build Profiles

### Development

```bash
cargo build
# opt-level=0, debug symbols included
```

### Release

```bash
cargo build --release
# opt-level=3, LTO enabled, stripped
```

## Examples

### Test Database Connection

```bash
cargo run --example test_connection
```

Expected output:
```
[+] Connected to database
[+] Found 9 stores (8 stable)
```

## Testing

```bash
# Run all tests
cargo test

# Run tests for specific crate
cargo test -p price-scout-models

# Run with output
cargo test -- --nocapture
```

## Deployment

### Build on Archbook

```bash
# Copy to Archbook
rsync -avz -e "ssh -i ~/.ssh/archbook_key -p 2222" \
  ./ sergey@192.168.0.10:/home/sergey/price_scout/

# SSH to Archbook
ssh -i ~/.ssh/archbook_key -p 2222 sergey@192.168.0.10

# Build release
cd /home/sergey/price_scout
cargo build --release

# Binaries in target/release/
ls -lh target/release/price-scout-*
```

### Systemd Services

Planned services:
- `price-scout-api.service` - API server
- `price-scout-worker.service` - Scraper queue
- `price-scout-bot.service` - Telegram bot
- `price-scout-alerts.service` - Price alerts

## Roadmap

### Phase 1: Database + Rust Foundation (Weeks 1-2)

- [+] PS-21: PostgreSQL schema
- [+] PS-22: Rust workspace
- [ ] PS-23: Python bridge

### Phase 2: Marketplace Expansion (Weeks 3-4)

- [ ] PS-24: Add 3-4 new stores
- [ ] PS-25: Retry logic
- [ ] PS-26: Enhanced filtering

### Phase 3: Rust Migration (Weeks 4-6)

- [ ] PS-27: Database layer
- [ ] PS-28: API server
- [ ] PS-29: Scraper orchestration

### Phase 4: MVP Telegram Bot (Weeks 6-8)

- [ ] PS-30: Telegram bot
- [ ] PS-31: Price alerts
- [ ] PS-32: Documentation + deployment

## Architecture

### Hybrid Rust + Python

```
┌─────────────────────────────────────────┐
│         Telegram Bot (Rust)             │
│            teloxide                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│         API Server (Rust)               │
│              Axum                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│      Database Layer (Rust)              │
│             sqlx                        │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│         PostgreSQL 17.5                 │
│          (Archbook)                     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│    Scraper Orchestrator (Rust)          │
│         + Python Bridge                 │
└──────────────┬──────────────────────────┘
               │ subprocess + JSON
               │
┌──────────────┴──────────────────────────┐
│      Python Scrapers (Existing)         │
│  test_scrapers.py + specs_filter.py     │
└─────────────────────────────────────────┘
```

### Data Flow

1. **User** → Telegram Bot → Database
2. **Bot** → Scraper Queue → Job
3. **Worker** → Python Scraper → Prices
4. **Prices** → Database → History
5. **Alert** → Bot → User

## Performance

### Database Connection Pool

- Max connections: 10
- Acquire timeout: 5s
- Connection reuse

### Async Runtime

- Tokio multi-threaded
- Work stealing scheduler
- Efficient I/O

## Security

- Environment variables for secrets
- No credentials in code
- Prepared statements (sqlx)
- Input validation

## Monitoring

### Logging

```bash
# Set log level
export RUST_LOG=info,price_scout=debug

# Run with logging
cargo run
```

### Metrics

Planned:
- Request latency
- Database query times
- Scraper success rate
- Active users

## Contributing

1. Check plan: `~/.claude/plans/cheerful-bubbling-catmull.md`
2. Create branch: `git checkout -b feature/PS-XX`
3. Run tests: `cargo test`
4. Format code: `cargo fmt`
5. Check lints: `cargo clippy`
6. Commit: Follow conventional commits

## References

- Plan: `~/.claude/plans/cheerful-bubbling-catmull.md`
- Migrations: `migrations/README.md`
- Python scrapers: `scripts/test_scrapers.py`
- Database schema: `migrations/001_initial_schema.sql`

## License

MIT
