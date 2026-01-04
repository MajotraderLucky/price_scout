-- Price Scout Database Schema
-- Version: 001
-- Description: Initial schema for price tracking system
-- Author: Price Scout Team
-- Created: 2026-01-04

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
-- Telegram bot users who track product prices

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,

    CONSTRAINT users_telegram_id_positive CHECK (telegram_id > 0)
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_last_active ON users(last_active_at DESC);

COMMENT ON TABLE users IS 'Telegram bot users';
COMMENT ON COLUMN users.telegram_id IS 'Telegram user ID';
COMMENT ON COLUMN users.last_active_at IS 'Last interaction with bot';

-- ============================================================================
-- STORES TABLE
-- ============================================================================
-- Online stores/marketplaces where we scrape prices

CREATE TABLE stores (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    base_url TEXT NOT NULL,
    method TEXT NOT NULL,
    parser TEXT NOT NULL,
    unstable BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT stores_name_not_empty CHECK (name <> ''),
    CONSTRAINT stores_method_valid CHECK (method IN (
        'firefox', 'playwright_direct', 'playwright_stealth',
        'ozon_firefox', 'citilink_firefox', 'avito_firefox',
        'yandex_market_special'
    ))
);

CREATE INDEX idx_stores_unstable ON stores(unstable) WHERE unstable = false;

COMMENT ON TABLE stores IS 'Online marketplaces and stores';
COMMENT ON COLUMN stores.method IS 'Scraping method: firefox, playwright_direct, etc.';
COMMENT ON COLUMN stores.parser IS 'Parser type: generic, citilink_json, etc.';
COMMENT ON COLUMN stores.unstable IS 'True if store has rate limiting or unreliable scraping';

-- ============================================================================
-- PRODUCTS TABLE
-- ============================================================================
-- Central product catalog with specifications

CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    specs JSONB,
    search_query TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT products_name_not_empty CHECK (name <> '')
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_specs ON products USING gin(specs);
CREATE INDEX idx_products_search_query ON products(search_query);
CREATE INDEX idx_products_updated_at ON products(updated_at DESC);

COMMENT ON TABLE products IS 'Product catalog with specifications';
COMMENT ON COLUMN products.specs IS 'JSON: {cpu: "M1 Pro", ram: 32, ssd: 512, screen: "16"}';
COMMENT ON COLUMN products.search_query IS 'Search query used to find this product';

-- ============================================================================
-- STORE_PRICES TABLE
-- ============================================================================
-- Current prices for products in stores (latest snapshot)

CREATE TABLE store_prices (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    price INTEGER NOT NULL,
    url TEXT,
    available BOOLEAN NOT NULL DEFAULT true,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT store_prices_unique_product_store UNIQUE(product_id, store_id),
    CONSTRAINT store_prices_price_positive CHECK (price > 0)
);

CREATE INDEX idx_store_prices_product ON store_prices(product_id);
CREATE INDEX idx_store_prices_store ON store_prices(store_id);
CREATE INDEX idx_store_prices_price ON store_prices(price);
CREATE INDEX idx_store_prices_available ON store_prices(available) WHERE available = true;
CREATE INDEX idx_store_prices_scraped_at ON store_prices(scraped_at DESC);

COMMENT ON TABLE store_prices IS 'Current prices (latest snapshot per product-store pair)';
COMMENT ON COLUMN store_prices.price IS 'Price in kopecks (100 kopecks = 1 RUB)';
COMMENT ON COLUMN store_prices.available IS 'Product availability in store';
COMMENT ON COLUMN store_prices.scraped_at IS 'When this price was scraped';

-- ============================================================================
-- PRICE_HISTORY TABLE
-- ============================================================================
-- Historical price data (time series)

CREATE TABLE price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    price INTEGER NOT NULL,
    available BOOLEAN NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT price_history_price_positive CHECK (price > 0)
);

CREATE INDEX idx_price_history_product ON price_history(product_id);
CREATE INDEX idx_price_history_store ON price_history(store_id);
CREATE INDEX idx_price_history_recorded_at ON price_history(recorded_at DESC);
CREATE INDEX idx_price_history_product_time ON price_history(product_id, recorded_at DESC);

COMMENT ON TABLE price_history IS 'Historical price data (append-only time series)';
COMMENT ON COLUMN price_history.price IS 'Price in kopecks';
COMMENT ON COLUMN price_history.recorded_at IS 'When this price point was recorded';

-- ============================================================================
-- TRACKINGS TABLE
-- ============================================================================
-- User subscriptions to product price changes

CREATE TABLE trackings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    target_price INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT trackings_unique_user_product UNIQUE(user_id, product_id),
    CONSTRAINT trackings_target_price_positive CHECK (target_price IS NULL OR target_price > 0)
);

CREATE INDEX idx_trackings_user ON trackings(user_id);
CREATE INDEX idx_trackings_product ON trackings(product_id);
CREATE INDEX idx_trackings_target_price ON trackings(target_price) WHERE target_price IS NOT NULL;

COMMENT ON TABLE trackings IS 'User price tracking subscriptions';
COMMENT ON COLUMN trackings.target_price IS 'Alert when price drops below this (kopecks)';

-- ============================================================================
-- SCRAPING_JOBS TABLE
-- ============================================================================
-- Scraping job queue and execution status

CREATE TABLE scraping_jobs (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    result JSONB,

    CONSTRAINT scraping_jobs_status_valid CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    )),
    CONSTRAINT scraping_jobs_priority_range CHECK (priority BETWEEN 1 AND 10),
    CONSTRAINT scraping_jobs_timestamps_valid CHECK (
        started_at IS NULL OR started_at >= scheduled_at
    ),
    CONSTRAINT scraping_jobs_completion_valid CHECK (
        completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at)
    )
);

CREATE INDEX idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX idx_scraping_jobs_pending ON scraping_jobs(status, priority DESC, scheduled_at)
    WHERE status = 'pending';
CREATE INDEX idx_scraping_jobs_product ON scraping_jobs(product_id);
CREATE INDEX idx_scraping_jobs_store ON scraping_jobs(store_id);
CREATE INDEX idx_scraping_jobs_scheduled_at ON scraping_jobs(scheduled_at DESC);

COMMENT ON TABLE scraping_jobs IS 'Scraping job queue for background worker';
COMMENT ON COLUMN scraping_jobs.status IS 'pending, running, completed, failed';
COMMENT ON COLUMN scraping_jobs.priority IS '1 (low) to 10 (high)';
COMMENT ON COLUMN scraping_jobs.store_id IS 'NULL = scrape all stores for product';
COMMENT ON COLUMN scraping_jobs.result IS 'JSON result from scraper';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Update product updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_product_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_product_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_product_updated_at();

-- Archive price to history when store_prices is updated
CREATE OR REPLACE FUNCTION archive_price_to_history()
RETURNS TRIGGER AS $$
BEGIN
    -- Only archive if price changed or availability changed
    IF (OLD.price <> NEW.price OR OLD.available <> NEW.available) THEN
        INSERT INTO price_history (product_id, store_id, price, available, recorded_at)
        VALUES (NEW.product_id, NEW.store_id, NEW.price, NEW.available, NEW.scraped_at);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_archive_price_to_history
    AFTER UPDATE ON store_prices
    FOR EACH ROW
    EXECUTE FUNCTION archive_price_to_history();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Best prices view (top 10 cheapest available products per store)
CREATE VIEW v_best_prices AS
SELECT
    p.id AS product_id,
    p.name AS product_name,
    p.category,
    s.id AS store_id,
    s.name AS store_name,
    sp.price,
    sp.url,
    sp.scraped_at,
    ROW_NUMBER() OVER (PARTITION BY sp.product_id ORDER BY sp.price) AS price_rank
FROM store_prices sp
JOIN products p ON sp.product_id = p.id
JOIN stores s ON sp.store_id = s.id
WHERE sp.available = true;

COMMENT ON VIEW v_best_prices IS 'Best available prices per product with ranking';

-- Active trackings view (with current best price)
CREATE VIEW v_active_trackings AS
SELECT
    t.id AS tracking_id,
    t.user_id,
    u.telegram_id,
    u.username,
    t.product_id,
    p.name AS product_name,
    t.target_price,
    MIN(sp.price) AS current_best_price,
    MIN(sp.price) FILTER (WHERE sp.price <= t.target_price) AS triggered_price,
    COUNT(sp.id) AS available_stores
FROM trackings t
JOIN users u ON t.user_id = u.id
JOIN products p ON t.product_id = p.id
LEFT JOIN store_prices sp ON sp.product_id = t.product_id AND sp.available = true
GROUP BY t.id, t.user_id, u.telegram_id, u.username, t.product_id, p.name, t.target_price;

COMMENT ON VIEW v_active_trackings IS 'Active trackings with current prices and alerts';

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Create default 'unknown' user for legacy data
INSERT INTO users (telegram_id, username, created_at)
VALUES (0, 'system', NOW())
ON CONFLICT (telegram_id) DO NOTHING;

-- ============================================================================
-- GRANTS (for application user)
-- ============================================================================

-- Create application user if not exists (uncomment if needed)
-- CREATE USER price_scout_app WITH PASSWORD 'your_secure_password';

-- Grant permissions (uncomment if needed)
-- GRANT CONNECT ON DATABASE price_scout TO price_scout_app;
-- GRANT USAGE ON SCHEMA public TO price_scout_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO price_scout_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO price_scout_app;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA public TO price_scout_app;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Show all tables
DO $$
BEGIN
    RAISE NOTICE 'Schema created successfully!';
    RAISE NOTICE 'Tables: users, stores, products, store_prices, price_history, trackings, scraping_jobs';
    RAISE NOTICE 'Views: v_best_prices, v_active_trackings';
    RAISE NOTICE 'Triggers: archive_price_to_history, update_product_updated_at';
END $$;
