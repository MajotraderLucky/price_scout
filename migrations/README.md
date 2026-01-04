# Price Scout Database Migrations

Database schema and migration scripts for Price Scout project.

## Overview

| Migration | Description                    | Tables Created | Status    |
|-----------|--------------------------------|----------------|-----------|
| 001       | Initial schema                 | 7 tables       | [+] Ready |
| 002       | Seed store data                | N/A (data)     | [+] Ready |

## Database Schema

### Tables

| Table          | Purpose                                | Rows (est.) |
|----------------|----------------------------------------|-------------|
| users          | Telegram bot users                     | 100-1000    |
| stores         | Marketplace configurations             | 10-15       |
| products       | Product catalog with specs             | 1000-10000  |
| store_prices   | Current prices (latest snapshot)       | 10000+      |
| price_history  | Historical price data (time series)    | 100000+     |
| trackings      | User price subscriptions               | 1000+       |
| scraping_jobs  | Job queue for background worker        | 1000+       |

### Views

| View                | Purpose                                    |
|---------------------|--------------------------------------------|
| v_best_prices       | Best prices per product with ranking       |
| v_active_trackings  | Active trackings with current prices       |

## Quick Start

### Prerequisites

1. PostgreSQL 17.5+ installed on Archbook (192.168.0.10)
2. Database created: `price_scout`
3. User with permissions (or use postgres superuser)

### Apply Migrations

```bash
# On Archbook server
psql -U postgres -d price_scout -f migrations/001_initial_schema.sql
psql -U postgres -d price_scout -f migrations/002_seed_stores.sql
```

### Verify Installation

```sql
-- Check tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Check stores
SELECT id, name, method, unstable FROM stores ORDER BY id;

-- Check views
SELECT viewname FROM pg_views WHERE schemaname = 'public';
```

## Migration Details

### 001_initial_schema.sql

Creates the complete database schema:

**Tables**:
- `users` - Telegram bot users
- `stores` - Marketplace configurations
- `products` - Product catalog with JSONB specs
- `store_prices` - Current prices (unique per product-store)
- `price_history` - Historical price data (append-only)
- `trackings` - User price subscriptions
- `scraping_jobs` - Job queue for scraper orchestration

**Triggers**:
- `update_product_updated_at` - Auto-update products.updated_at
- `archive_price_to_history` - Auto-archive price changes

**Views**:
- `v_best_prices` - Ranked prices per product
- `v_active_trackings` - Trackings with current prices

**Features**:
- Foreign key constraints with CASCADE delete
- Check constraints for data validation
- Composite unique indexes for performance
- GIN index on JSONB specs for fast filtering
- Automatic price history archiving

### 002_seed_stores.sql

Populates stores table with current marketplaces:

**Stable Stores** (8):
1. dns - DNS-Shop (Firefox + xdotool)
2. ozon - Ozon (Firefox + xdotool)
3. i-ray - i-ray.ru (Playwright Direct)
4. nix - nix.ru (Playwright Direct)
5. regard - regard.ru (Playwright Stealth)
6. kns - kns.ru (Playwright Direct)
7. yandex_market - Yandex Market (Playwright Stealth)
8. avito - Avito (Firefox + xdotool)

**Unstable Stores** (1):
9. citilink - Citilink (rate limiting, manual testing only)

## Database Connection

### Environment Variables

```bash
export DATABASE_URL="postgresql://user:password@192.168.0.10:5432/price_scout"
```

### Connection String Format

```
postgresql://[user]:[password]@[host]:[port]/[database]
```

### Rust (sqlx)

```rust
use sqlx::postgres::PgPoolOptions;

let pool = PgPoolOptions::new()
    .max_connections(10)
    .connect("postgresql://user:password@192.168.0.10:5432/price_scout")
    .await?;
```

### Python (psycopg2)

```python
import psycopg2

conn = psycopg2.connect(
    host="192.168.0.10",
    port=5432,
    database="price_scout",
    user="user",
    password="password"
)
```

## Backup and Restore

### Backup

```bash
# Full database backup
pg_dump -U postgres -d price_scout -F c -f price_scout_backup.dump

# Schema only
pg_dump -U postgres -d price_scout -s -f price_scout_schema.sql

# Data only
pg_dump -U postgres -d price_scout -a -f price_scout_data.sql
```

### Restore

```bash
# From custom format backup
pg_restore -U postgres -d price_scout -c price_scout_backup.dump

# From SQL file
psql -U postgres -d price_scout -f price_scout_backup.sql
```

### Automated Backups

Create systemd timer for daily backups:

```bash
# /etc/systemd/system/price-scout-backup.service
[Unit]
Description=Price Scout Database Backup

[Service]
Type=oneshot
User=postgres
ExecStart=/usr/bin/pg_dump -U postgres -d price_scout -F c -f /var/backups/price_scout/price_scout_$(date +\%Y\%m\%d).dump

# /etc/systemd/system/price-scout-backup.timer
[Unit]
Description=Price Scout Daily Backup Timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

## Performance Tuning

### Recommended PostgreSQL Settings

```sql
-- For 6GB RAM system (Archbook)
ALTER SYSTEM SET shared_buffers = '1536MB';
ALTER SYSTEM SET effective_cache_size = '4GB';
ALTER SYSTEM SET maintenance_work_mem = '384MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET max_connections = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

### Index Maintenance

```sql
-- Reindex all tables (monthly)
REINDEX DATABASE price_scout;

-- Analyze tables for query planner
ANALYZE;

-- Vacuum and analyze
VACUUM ANALYZE;
```

## Monitoring

### Table Sizes

```sql
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS total_size,
    pg_size_pretty(pg_relation_size(tablename::regclass)) AS table_size,
    pg_size_pretty(pg_total_relation_size(tablename::regclass) - pg_relation_size(tablename::regclass)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
```

### Active Connections

```sql
SELECT
    datname,
    count(*) AS connections
FROM pg_stat_activity
WHERE datname = 'price_scout'
GROUP BY datname;
```

### Slow Queries

```sql
-- Enable query logging (postgresql.conf)
log_min_duration_statement = 1000  -- Log queries slower than 1s

-- View slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE query LIKE '%price_scout%'
ORDER BY mean_time DESC
LIMIT 10;
```

## Troubleshooting

### Reset Database

```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS price_scout;"
psql -U postgres -c "CREATE DATABASE price_scout;"

# Apply migrations
psql -U postgres -d price_scout -f migrations/001_initial_schema.sql
psql -U postgres -d price_scout -f migrations/002_seed_stores.sql
```

### Common Issues

**Issue**: Connection refused
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Check listening ports
netstat -tuln | grep 5432

# Check pg_hba.conf for connection permissions
```

**Issue**: Out of memory
```bash
# Reduce shared_buffers and work_mem
# Add swap space if needed
```

**Issue**: Slow queries
```bash
# Run ANALYZE on tables
# Check index usage with EXPLAIN ANALYZE
# Consider adding indexes on frequently queried columns
```

## Next Steps

After applying migrations:

1. Test connection from Rust: `cargo run --example test_db_connection`
2. Populate products table with test data
3. Run scraper to populate store_prices
4. Verify triggers and views work correctly
5. Set up automated backups
6. Configure monitoring and alerts

## References

- PostgreSQL 17 Documentation: https://www.postgresql.org/docs/17/
- sqlx Documentation: https://docs.rs/sqlx/
- Price Scout Plan: `~/.claude/plans/cheerful-bubbling-catmull.md`
