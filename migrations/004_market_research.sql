-- Price Scout Market Research Migration
-- Version: 004
-- Description: Market research tables for product discovery and popularity ranking
-- Author: Price Scout Team
-- Created: 2026-01-06

-- ============================================================================
-- SEARCH QUERIES TRACKING
-- ============================================================================
-- Tracks all search queries from bot users and discovery processes

CREATE TABLE IF NOT EXISTS search_queries (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN (
        'telegram_bot',      -- User searches in Telegram bot
        'web_discovery',     -- DuckDuckGo web search
        'catalog_parse',     -- Direct store catalog parsing
        'manual'             -- Manual additions by admin
    )),
    category TEXT,           -- Auto-detected or assigned category
    search_count INTEGER NOT NULL DEFAULT 1,
    last_searched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for search_queries
CREATE INDEX IF NOT EXISTS idx_search_queries_query ON search_queries(query);
CREATE INDEX IF NOT EXISTS idx_search_queries_category ON search_queries(category);
CREATE INDEX IF NOT EXISTS idx_search_queries_count ON search_queries(search_count DESC);
CREATE INDEX IF NOT EXISTS idx_search_queries_recent ON search_queries(last_searched_at DESC);

-- Unique constraint to prevent duplicates (upsert on conflict)
CREATE UNIQUE INDEX IF NOT EXISTS idx_search_queries_unique ON search_queries(LOWER(query), source);

-- ============================================================================
-- DISCOVERY JOBS QUEUE
-- ============================================================================
-- Queue for product discovery tasks from various sources

CREATE TABLE IF NOT EXISTS discovery_jobs (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN (
        'duckduckgo',
        'ozon_catalog',
        'dns_catalog',
        'yandex_market_catalog'
    )),
    category TEXT,
    query TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'running',
        'completed',
        'failed'
    )),
    products_found INTEGER DEFAULT 0,
    products_new INTEGER DEFAULT 0,
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT
);

-- Indexes for discovery_jobs
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_status ON discovery_jobs(status);
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_pending ON discovery_jobs(status, scheduled_at)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_discovery_jobs_scheduled ON discovery_jobs(scheduled_at DESC);

-- ============================================================================
-- PRODUCT POPULARITY MATERIALIZED VIEW
-- ============================================================================
-- Calculates popularity score for products in price range 1,000-15,000 RUB
-- Refreshed hourly by discovery scheduler

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_product_popularity AS
SELECT
    p.id AS product_id,
    p.name,
    p.category,

    -- Tracking score (0-40 points): how many users track this product
    LEAST(
        COALESCE((SELECT COUNT(*) FROM trackings t WHERE t.product_id = p.id), 0) * 4,
        40
    )::INTEGER AS tracking_score,

    -- Volatility score (0-30 points): price fluctuation indicates market activity
    LEAST(
        COALESCE(
            (SELECT
                CASE
                    WHEN AVG(price) > 0 THEN STDDEV(price)::FLOAT / AVG(price)::FLOAT * 100 * 10
                    ELSE 0
                END
             FROM price_history ph
             WHERE ph.product_id = p.id
               AND ph.recorded_at >= NOW() - INTERVAL '7 days'
            ),
            0
        ),
        30
    )::INTEGER AS volatility_score,

    -- Availability score (0-20 points): available in more stores = more popular
    LEAST(
        COALESCE(
            (SELECT COUNT(DISTINCT store_id)
             FROM store_prices sp
             WHERE sp.product_id = p.id AND sp.available = true),
            0
        ) * 2,
        20
    )::INTEGER AS availability_score,

    -- Arbitrage score (0-10 points): price spread between stores
    LEAST(
        COALESCE(
            (SELECT
                CASE
                    WHEN MIN(price) > 0 THEN (MAX(price) - MIN(price))::FLOAT / MIN(price)::FLOAT * 100
                    ELSE 0
                END
             FROM store_prices sp
             WHERE sp.product_id = p.id AND sp.available = true
            ),
            0
        ),
        10
    )::INTEGER AS arbitrage_score,

    -- Tracking count for quick access
    COALESCE((SELECT COUNT(*) FROM trackings t WHERE t.product_id = p.id), 0) AS tracking_count,

    -- Price data
    (SELECT MIN(price) FROM store_prices sp WHERE sp.product_id = p.id AND sp.available = true) AS min_price,
    (SELECT MAX(price) FROM store_prices sp WHERE sp.product_id = p.id AND sp.available = true) AS max_price,
    (SELECT COUNT(DISTINCT store_id) FROM store_prices sp WHERE sp.product_id = p.id AND sp.available = true) AS store_count,

    -- Timestamp
    NOW() AS calculated_at

FROM products p
WHERE EXISTS (
    SELECT 1 FROM store_prices sp
    WHERE sp.product_id = p.id
      AND sp.price >= 100000    -- 1,000 RUB in kopecks
      AND sp.price <= 1500000   -- 15,000 RUB in kopecks
);

-- Unique index for concurrent refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_popularity_product ON mv_product_popularity(product_id);
CREATE INDEX IF NOT EXISTS idx_mv_popularity_score_calc ON mv_product_popularity(
    (tracking_score + volatility_score + availability_score + arbitrage_score) DESC
);

-- ============================================================================
-- TOP 100 PRODUCTS VIEW
-- ============================================================================
-- Combines scores and orders by total popularity

CREATE OR REPLACE VIEW v_top_100_products AS
SELECT
    product_id,
    name,
    category,
    (tracking_score + volatility_score + availability_score + arbitrage_score) AS popularity_score,
    tracking_score,
    volatility_score,
    availability_score,
    arbitrage_score,
    tracking_count,
    min_price / 100 AS min_price_rub,
    max_price / 100 AS max_price_rub,
    store_count,
    calculated_at
FROM mv_product_popularity
ORDER BY (tracking_score + volatility_score + availability_score + arbitrage_score) DESC
LIMIT 100;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to refresh popularity metrics
CREATE OR REPLACE FUNCTION refresh_product_popularity()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_product_popularity;
END;
$$ LANGUAGE plpgsql;

-- Function to record or update search query
CREATE OR REPLACE FUNCTION upsert_search_query(
    p_query TEXT,
    p_source TEXT,
    p_category TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO search_queries (query, source, category, search_count, last_searched_at)
    VALUES (p_query, p_source, p_category, 1, NOW())
    ON CONFLICT (LOWER(query), source)
    DO UPDATE SET
        search_count = search_queries.search_count + 1,
        last_searched_at = NOW(),
        category = COALESCE(EXCLUDED.category, search_queries.category)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE search_queries IS 'Tracks search queries from users and discovery processes for market research';
COMMENT ON TABLE discovery_jobs IS 'Queue for product discovery tasks from various sources';
COMMENT ON MATERIALIZED VIEW mv_product_popularity IS 'Product popularity scores, refreshed hourly';
COMMENT ON VIEW v_top_100_products IS 'Top 100 most popular products by combined score';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Market Research Migration Complete!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'New tables:';
    RAISE NOTICE '  - search_queries: Track user search patterns';
    RAISE NOTICE '  - discovery_jobs: Discovery task queue';
    RAISE NOTICE '';
    RAISE NOTICE 'New views:';
    RAISE NOTICE '  - mv_product_popularity: Popularity metrics (MATERIALIZED)';
    RAISE NOTICE '  - v_top_100_products: Top 100 ranked products';
    RAISE NOTICE '';
    RAISE NOTICE 'Popularity Score Formula (0-100):';
    RAISE NOTICE '  - Tracking (40%%): trackings_count * 4';
    RAISE NOTICE '  - Volatility (30%%): price_stddev_percent * 10';
    RAISE NOTICE '  - Availability (20%%): store_count * 2';
    RAISE NOTICE '  - Arbitrage (10%%): price_spread_percent';
    RAISE NOTICE '';
    RAISE NOTICE 'Price range: 1,000 - 15,000 RUB';
    RAISE NOTICE '========================================';
END $$;
