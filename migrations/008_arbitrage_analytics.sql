-- Migration 008: Enhanced Arbitrage Analytics
-- Part of PS-46 Phase 3: Arbitrage Analytics System
--
-- Adds tables and functions for advanced arbitrage analysis:
-- - Historical arbitrage tracking
-- - User alert configuration
-- - Trend analysis functions

-- ============================================================================
-- ARBITRAGE HISTORY TABLE
-- ============================================================================
-- Stores snapshots of arbitrage opportunities for trend analysis

CREATE TABLE IF NOT EXISTS arbitrage_history (
    id BIGSERIAL PRIMARY KEY,

    -- Product info
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Buy side
    buy_store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    buy_price INTEGER NOT NULL,

    -- Sell side
    sell_store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    sell_price INTEGER NOT NULL,

    -- Profit metrics
    profit_kopecks INTEGER NOT NULL,
    profit_percent FLOAT NOT NULL,

    -- Timestamps
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CHECK (sell_price > buy_price),
    CHECK (profit_percent > 0)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_arb_history_product ON arbitrage_history(product_id);
CREATE INDEX IF NOT EXISTS idx_arb_history_detected ON arbitrage_history(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_arb_history_profit ON arbitrage_history(profit_percent DESC);
CREATE INDEX IF NOT EXISTS idx_arb_history_stores ON arbitrage_history(buy_store_id, sell_store_id);

-- ============================================================================
-- ARBITRAGE ALERTS TABLE
-- ============================================================================
-- User-configured alerts for arbitrage opportunities

CREATE TABLE IF NOT EXISTS arbitrage_alerts (
    id BIGSERIAL PRIMARY KEY,

    -- User who created the alert
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Alert configuration
    min_profit_percent FLOAT NOT NULL DEFAULT 10.0,

    -- Optional filters
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,  -- NULL = all products
    category TEXT,  -- NULL = all categories

    -- Alert status
    enabled BOOLEAN NOT NULL DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CHECK (min_profit_percent > 0),
    UNIQUE(user_id, product_id)  -- One alert per product per user
);

CREATE INDEX IF NOT EXISTS idx_arb_alerts_user ON arbitrage_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_arb_alerts_enabled ON arbitrage_alerts(enabled) WHERE enabled = true;

-- ============================================================================
-- ARBITRAGE WATCH LIST
-- ============================================================================
-- Products being watched for arbitrage by users

CREATE TABLE IF NOT EXISTS arbitrage_watchlist (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Watch configuration
    min_profit_percent FLOAT NOT NULL DEFAULT 5.0,
    notify_on_opportunity BOOLEAN NOT NULL DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One entry per user/product
    UNIQUE(user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_arb_watch_user ON arbitrage_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_arb_watch_product ON arbitrage_watchlist(product_id);

-- ============================================================================
-- FUNCTION: Record Arbitrage Snapshot
-- ============================================================================
-- Called periodically to snapshot current arbitrage opportunities

CREATE OR REPLACE FUNCTION record_arbitrage_snapshot(p_min_profit_percent FLOAT DEFAULT 5.0)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    INSERT INTO arbitrage_history (
        product_id, buy_store_id, buy_price, sell_store_id, sell_price,
        profit_kopecks, profit_percent
    )
    SELECT
        sp1.product_id,
        sp1.store_id as buy_store_id,
        sp1.price as buy_price,
        sp2.store_id as sell_store_id,
        sp2.price as sell_price,
        (sp2.price - sp1.price) as profit_kopecks,
        ((sp2.price - sp1.price)::float / sp1.price::float * 100) as profit_percent
    FROM store_prices sp1
    JOIN store_prices sp2 ON sp1.product_id = sp2.product_id
    WHERE sp1.available = true
      AND sp2.available = true
      AND sp1.store_id != sp2.store_id
      AND sp2.price > sp1.price
      AND ((sp2.price - sp1.price)::float / sp1.price::float * 100) >= p_min_profit_percent;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Get Arbitrage History for Product
-- ============================================================================

CREATE OR REPLACE FUNCTION get_arbitrage_history(
    p_product_id BIGINT,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    detected_date DATE,
    avg_profit_percent FLOAT,
    max_profit_percent FLOAT,
    min_profit_percent FLOAT,
    opportunity_count BIGINT,
    best_buy_store TEXT,
    best_sell_store TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(ah.detected_at) as detected_date,
        AVG(ah.profit_percent)::float as avg_profit_percent,
        MAX(ah.profit_percent)::float as max_profit_percent,
        MIN(ah.profit_percent)::float as min_profit_percent,
        COUNT(*) as opportunity_count,
        (
            SELECT s.name FROM stores s
            WHERE s.id = (
                SELECT ah2.buy_store_id FROM arbitrage_history ah2
                WHERE ah2.product_id = p_product_id
                  AND DATE(ah2.detected_at) = DATE(ah.detected_at)
                ORDER BY ah2.profit_percent DESC LIMIT 1
            )
        ) as best_buy_store,
        (
            SELECT s.name FROM stores s
            WHERE s.id = (
                SELECT ah2.sell_store_id FROM arbitrage_history ah2
                WHERE ah2.product_id = p_product_id
                  AND DATE(ah2.detected_at) = DATE(ah.detected_at)
                ORDER BY ah2.profit_percent DESC LIMIT 1
            )
        ) as best_sell_store
    FROM arbitrage_history ah
    WHERE ah.product_id = p_product_id
      AND ah.detected_at >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY DATE(ah.detected_at)
    ORDER BY detected_date DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Get Arbitrage Trends (Market-wide)
-- ============================================================================

CREATE OR REPLACE FUNCTION get_arbitrage_trends(p_days INTEGER DEFAULT 7)
RETURNS TABLE (
    trend_date DATE,
    total_opportunities BIGINT,
    avg_profit_percent FLOAT,
    max_profit_percent FLOAT,
    unique_products BIGINT,
    total_profit_potential BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(ah.detected_at) as trend_date,
        COUNT(*) as total_opportunities,
        AVG(ah.profit_percent)::float as avg_profit_percent,
        MAX(ah.profit_percent)::float as max_profit_percent,
        COUNT(DISTINCT ah.product_id) as unique_products,
        SUM(ah.profit_kopecks) as total_profit_potential
    FROM arbitrage_history ah
    WHERE ah.detected_at >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY DATE(ah.detected_at)
    ORDER BY trend_date DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Get Best Arbitrage Products
-- ============================================================================

CREATE OR REPLACE FUNCTION get_best_arbitrage_products(
    p_days INTEGER DEFAULT 7,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    product_id BIGINT,
    product_name TEXT,
    category TEXT,
    opportunity_count BIGINT,
    avg_profit_percent FLOAT,
    max_profit_percent FLOAT,
    last_opportunity_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ah.product_id,
        p.name as product_name,
        p.category,
        COUNT(*) as opportunity_count,
        AVG(ah.profit_percent)::float as avg_profit_percent,
        MAX(ah.profit_percent)::float as max_profit_percent,
        MAX(ah.detected_at) as last_opportunity_at
    FROM arbitrage_history ah
    JOIN products p ON ah.product_id = p.id
    WHERE ah.detected_at >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY ah.product_id, p.name, p.category
    ORDER BY opportunity_count DESC, avg_profit_percent DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEW: Current High-Margin Alerts (>20%)
-- ============================================================================

CREATE OR REPLACE VIEW v_arbitrage_alerts AS
SELECT
    p.id as product_id,
    p.name as product_name,
    p.category,
    s1.name as buy_store,
    sp1.price as buy_price,
    s2.name as sell_store,
    sp2.price as sell_price,
    (sp2.price - sp1.price) as profit_kopecks,
    ((sp2.price - sp1.price)::float / sp1.price::float * 100) as profit_percent,
    sp1.scraped_at as last_updated
FROM products p
JOIN store_prices sp1 ON p.id = sp1.product_id
JOIN store_prices sp2 ON p.id = sp2.product_id
JOIN stores s1 ON sp1.store_id = s1.id
JOIN stores s2 ON sp2.store_id = s2.id
WHERE sp1.available = true
  AND sp2.available = true
  AND sp1.store_id != sp2.store_id
  AND sp2.price > sp1.price
  AND ((sp2.price - sp1.price)::float / sp1.price::float * 100) >= 20
ORDER BY profit_percent DESC;

-- ============================================================================
-- VIEW: Store Pair Performance
-- ============================================================================
-- Shows which store pairs have the best arbitrage potential

CREATE OR REPLACE VIEW v_store_pair_arbitrage AS
SELECT
    s1.name as buy_store,
    s2.name as sell_store,
    COUNT(*) as opportunity_count,
    AVG(ah.profit_percent)::float as avg_profit_percent,
    SUM(ah.profit_kopecks) as total_profit_potential
FROM arbitrage_history ah
JOIN stores s1 ON ah.buy_store_id = s1.id
JOIN stores s2 ON ah.sell_store_id = s2.id
WHERE ah.detected_at >= NOW() - INTERVAL '7 days'
GROUP BY s1.name, s2.name
HAVING COUNT(*) >= 3
ORDER BY avg_profit_percent DESC;

-- ============================================================================
-- GRANT PERMISSIONS (if needed)
-- ============================================================================

-- Ensure functions are executable
GRANT EXECUTE ON FUNCTION record_arbitrage_snapshot(FLOAT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_arbitrage_history(BIGINT, INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_arbitrage_trends(INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_best_arbitrage_products(INTEGER, INTEGER) TO PUBLIC;
