-- Migration 010: Smart Price Alerts with Currency Analysis
-- Part of PS-47: User Price Alerts System
--
-- Adds tables for automatic price drop notifications with
-- currency correlation analysis to distinguish market vs currency changes.

-- ============================================================================
-- USER PRICE ALERTS TABLE
-- ============================================================================
-- Stores user subscriptions to price alerts for specific products

CREATE TABLE IF NOT EXISTS user_price_alerts (
    id BIGSERIAL PRIMARY KEY,

    -- User and product
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Alert type configuration
    alert_type TEXT NOT NULL DEFAULT 'any_drop',
    target_price INTEGER,              -- For 'target_price' type
    min_drop_percent FLOAT DEFAULT 5.0, -- Minimum % drop to trigger

    -- Baseline for comparison (captured at subscription time)
    baseline_price INTEGER NOT NULL,
    baseline_currency_usd FLOAT,
    baseline_currency_eur FLOAT,

    -- Alert status
    enabled BOOLEAN NOT NULL DEFAULT true,
    last_alert_at TIMESTAMPTZ,
    alert_count INTEGER NOT NULL DEFAULT 0,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL,  -- 'search', 'price', 'trends', 'compare', 'manual'

    -- Constraints
    UNIQUE(user_id, product_id),
    CHECK (alert_type IN ('any_drop', 'target_price', 'percent_drop')),
    CHECK (source IN ('search', 'price', 'trends', 'compare', 'manual'))
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_price_alerts_user ON user_price_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_price_alerts_product ON user_price_alerts(product_id);
CREATE INDEX IF NOT EXISTS idx_price_alerts_enabled ON user_price_alerts(enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_price_alerts_check ON user_price_alerts(enabled, last_alert_at)
    WHERE enabled = true;

-- ============================================================================
-- PRICE ALERT LOG TABLE
-- ============================================================================
-- History of sent alerts with analysis results

CREATE TABLE IF NOT EXISTS price_alert_log (
    id BIGSERIAL PRIMARY KEY,

    -- References
    alert_id BIGINT REFERENCES user_price_alerts(id) ON DELETE SET NULL,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,

    -- Price change details
    old_price INTEGER NOT NULL,
    new_price INTEGER NOT NULL,
    change_percent FLOAT NOT NULL,

    -- Currency analysis
    old_currency_usd FLOAT,
    new_currency_usd FLOAT,
    old_currency_eur FLOAT,
    new_currency_eur FLOAT,
    currency_change_usd FLOAT,
    currency_change_eur FLOAT,

    -- Cause analysis
    correlation_score FLOAT,           -- -1 to 1
    likely_cause TEXT NOT NULL,        -- 'currency', 'market', 'mixed', 'unknown'

    -- Delivery status
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    -- Constraints
    CHECK (likely_cause IN ('currency', 'market', 'mixed', 'unknown'))
);

CREATE INDEX IF NOT EXISTS idx_alert_log_user ON price_alert_log(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_log_product ON price_alert_log(product_id);
CREATE INDEX IF NOT EXISTS idx_alert_log_sent ON price_alert_log(sent_at DESC);

-- ============================================================================
-- FUNCTION: Get minimum price for product across all stores
-- ============================================================================

CREATE OR REPLACE FUNCTION get_product_min_price(p_product_id BIGINT)
RETURNS INTEGER AS $$
    SELECT MIN(price)
    FROM store_prices
    WHERE product_id = p_product_id
      AND available = true
      AND price > 0;
$$ LANGUAGE sql STABLE;

-- ============================================================================
-- FUNCTION: Analyze price change cause
-- ============================================================================
-- Compares price change with currency changes to determine likely cause

CREATE OR REPLACE FUNCTION analyze_price_change_cause(
    p_old_price INTEGER,
    p_new_price INTEGER,
    p_old_usd FLOAT,
    p_new_usd FLOAT,
    p_old_eur FLOAT,
    p_new_eur FLOAT
)
RETURNS TEXT AS $$
DECLARE
    v_price_change FLOAT;
    v_usd_change FLOAT;
    v_eur_change FLOAT;
BEGIN
    -- Calculate percentage changes
    v_price_change := (p_new_price::FLOAT - p_old_price::FLOAT) / NULLIF(p_old_price::FLOAT, 0);
    v_usd_change := (p_new_usd - p_old_usd) / NULLIF(p_old_usd, 0);
    v_eur_change := (p_new_eur - p_old_eur) / NULLIF(p_old_eur, 0);

    -- Handle NULL cases
    IF v_price_change IS NULL THEN
        RETURN 'unknown';
    END IF;

    IF v_usd_change IS NULL AND v_eur_change IS NULL THEN
        RETURN 'market';  -- No currency data, assume market
    END IF;

    -- Use USD as primary currency indicator
    IF v_usd_change IS NOT NULL THEN
        -- Both moving in same direction with similar magnitude
        IF SIGN(v_price_change) = SIGN(v_usd_change)
           AND ABS(v_usd_change) > 0.02 THEN  -- Currency moved >2%
            IF ABS(v_price_change - v_usd_change) < 0.03 THEN
                RETURN 'currency';  -- Price follows currency closely
            ELSE
                RETURN 'mixed';     -- Partially currency-driven
            END IF;
        END IF;
    END IF;

    -- EUR fallback
    IF v_eur_change IS NOT NULL THEN
        IF SIGN(v_price_change) = SIGN(v_eur_change)
           AND ABS(v_eur_change) > 0.02 THEN
            IF ABS(v_price_change - v_eur_change) < 0.03 THEN
                RETURN 'currency';
            ELSE
                RETURN 'mixed';
            END IF;
        END IF;
    END IF;

    RETURN 'market';  -- Price moved independently of currency
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- FUNCTION: Subscribe user to price alert
-- ============================================================================

CREATE OR REPLACE FUNCTION subscribe_to_price_alert(
    p_user_id BIGINT,
    p_product_id BIGINT,
    p_source TEXT,
    p_alert_type TEXT DEFAULT 'any_drop',
    p_target_price INTEGER DEFAULT NULL,
    p_min_drop_percent FLOAT DEFAULT 5.0
)
RETURNS BIGINT AS $$
DECLARE
    v_baseline_price INTEGER;
    v_usd_rate FLOAT;
    v_eur_rate FLOAT;
    v_alert_id BIGINT;
BEGIN
    -- Get current minimum price
    v_baseline_price := get_product_min_price(p_product_id);

    IF v_baseline_price IS NULL THEN
        RAISE EXCEPTION 'No price data for product %', p_product_id;
    END IF;

    -- Get current currency rates
    SELECT rate_to_rub INTO v_usd_rate
    FROM currency_rates
    WHERE currency_code = 'USD'
    ORDER BY recorded_at DESC
    LIMIT 1;

    SELECT rate_to_rub INTO v_eur_rate
    FROM currency_rates
    WHERE currency_code = 'EUR'
    ORDER BY recorded_at DESC
    LIMIT 1;

    -- Upsert alert subscription
    INSERT INTO user_price_alerts (
        user_id, product_id, alert_type, target_price, min_drop_percent,
        baseline_price, baseline_currency_usd, baseline_currency_eur, source
    )
    VALUES (
        p_user_id, p_product_id, p_alert_type, p_target_price, p_min_drop_percent,
        v_baseline_price, v_usd_rate, v_eur_rate, p_source
    )
    ON CONFLICT (user_id, product_id) DO UPDATE SET
        -- Re-enable if was disabled
        enabled = true,
        updated_at = NOW(),
        -- Update baseline if price is lower
        baseline_price = LEAST(user_price_alerts.baseline_price, EXCLUDED.baseline_price),
        baseline_currency_usd = COALESCE(EXCLUDED.baseline_currency_usd, user_price_alerts.baseline_currency_usd),
        baseline_currency_eur = COALESCE(EXCLUDED.baseline_currency_eur, user_price_alerts.baseline_currency_eur)
    RETURNING id INTO v_alert_id;

    RETURN v_alert_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Get alerts to check
-- ============================================================================
-- Returns alerts that need checking (enabled, not alerted recently)

CREATE OR REPLACE FUNCTION get_alerts_to_check(p_min_interval_hours INTEGER DEFAULT 6)
RETURNS TABLE (
    alert_id BIGINT,
    user_id BIGINT,
    product_id BIGINT,
    alert_type TEXT,
    target_price INTEGER,
    min_drop_percent FLOAT,
    baseline_price INTEGER,
    baseline_currency_usd FLOAT,
    baseline_currency_eur FLOAT,
    chat_id BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id as alert_id,
        a.user_id,
        a.product_id,
        a.alert_type,
        a.target_price,
        a.min_drop_percent,
        a.baseline_price,
        a.baseline_currency_usd,
        a.baseline_currency_eur,
        u.chat_id
    FROM user_price_alerts a
    JOIN users u ON a.user_id = u.id
    WHERE a.enabled = true
      AND u.chat_id IS NOT NULL
      AND u.notifications_enabled = true
      AND (a.last_alert_at IS NULL
           OR a.last_alert_at < NOW() - (p_min_interval_hours || ' hours')::INTERVAL);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Record sent alert
-- ============================================================================

CREATE OR REPLACE FUNCTION record_price_alert_sent(
    p_alert_id BIGINT,
    p_old_price INTEGER,
    p_new_price INTEGER,
    p_likely_cause TEXT
)
RETURNS VOID AS $$
BEGIN
    -- Update alert record
    UPDATE user_price_alerts
    SET last_alert_at = NOW(),
        alert_count = alert_count + 1,
        baseline_price = p_new_price,  -- Update baseline to new price
        updated_at = NOW()
    WHERE id = p_alert_id;

    -- Log the alert
    INSERT INTO price_alert_log (
        alert_id, user_id, product_id,
        old_price, new_price, change_percent,
        likely_cause
    )
    SELECT
        p_alert_id, user_id, product_id,
        p_old_price, p_new_price,
        ((p_new_price - p_old_price)::FLOAT / NULLIF(p_old_price::FLOAT, 0) * 100),
        p_likely_cause
    FROM user_price_alerts
    WHERE id = p_alert_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEW: User alert subscriptions with product info
-- ============================================================================

CREATE OR REPLACE VIEW v_user_alerts AS
SELECT
    a.id as alert_id,
    a.user_id,
    u.chat_id,
    a.product_id,
    p.name as product_name,
    a.alert_type,
    a.target_price,
    a.min_drop_percent,
    a.baseline_price,
    get_product_min_price(a.product_id) as current_price,
    a.enabled,
    a.alert_count,
    a.last_alert_at,
    a.created_at,
    a.source
FROM user_price_alerts a
JOIN users u ON a.user_id = u.id
JOIN products p ON a.product_id = p.id;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION get_product_min_price(BIGINT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION analyze_price_change_cause(INTEGER, INTEGER, FLOAT, FLOAT, FLOAT, FLOAT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION subscribe_to_price_alert(BIGINT, BIGINT, TEXT, TEXT, INTEGER, FLOAT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_alerts_to_check(INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION record_price_alert_sent(BIGINT, INTEGER, INTEGER, TEXT) TO PUBLIC;
