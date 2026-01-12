-- Migration 011: Wishlist (Delayed Purchases) Feature
-- Part of PS-50: User Wishlist System
--
-- Adds tables for tracking user wishlist items with:
-- - Priority levels (high/medium/low)
-- - Target price for notifications
-- - Purchase history tracking
-- - Integration with price alerts

-- ============================================================================
-- UPDATE SOURCE CHECK CONSTRAINT
-- ============================================================================
-- Add 'wishlist' as valid source for price alerts

ALTER TABLE user_price_alerts DROP CONSTRAINT IF EXISTS user_price_alerts_source_check;
ALTER TABLE user_price_alerts ADD CONSTRAINT user_price_alerts_source_check
    CHECK (source IN ('search', 'price', 'trends', 'compare', 'manual', 'wishlist'));

-- ============================================================================
-- USER WISHLIST TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_wishlist (
    id BIGSERIAL PRIMARY KEY,

    -- User and product
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Priority for sorting (1=high, 2=medium, 3=low)
    priority SMALLINT NOT NULL DEFAULT 2,

    -- Target price for notifications (in kopecks, optional)
    target_price INTEGER,

    -- User notes (optional)
    notes TEXT,

    -- Purchase tracking
    purchased BOOLEAN NOT NULL DEFAULT false,
    purchased_at TIMESTAMPTZ,
    purchased_price INTEGER,        -- Actual purchase price in kopecks
    purchased_store TEXT,           -- Store name where bought

    -- Associated price alert (auto-created when target_price is set)
    alert_id BIGINT REFERENCES user_price_alerts(id) ON DELETE SET NULL,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE(user_id, product_id),
    CHECK (priority BETWEEN 1 AND 3),
    CHECK (target_price IS NULL OR target_price > 0),
    CHECK (purchased_price IS NULL OR purchased_price > 0)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_wishlist_user ON user_wishlist(user_id);
CREATE INDEX IF NOT EXISTS idx_wishlist_product ON user_wishlist(product_id);
CREATE INDEX IF NOT EXISTS idx_wishlist_priority ON user_wishlist(priority);
CREATE INDEX IF NOT EXISTS idx_wishlist_active ON user_wishlist(user_id, purchased)
    WHERE purchased = false;
CREATE INDEX IF NOT EXISTS idx_wishlist_purchased ON user_wishlist(user_id, purchased_at DESC)
    WHERE purchased = true;

-- ============================================================================
-- VIEW: Wishlist with product and price info
-- ============================================================================

CREATE OR REPLACE VIEW v_user_wishlist AS
SELECT
    w.id as wishlist_id,
    w.user_id,
    w.product_id,
    p.name as product_name,
    p.category,
    w.priority,
    w.target_price,
    w.notes,
    w.purchased,
    w.purchased_at,
    w.purchased_price,
    w.purchased_store,
    get_product_min_price(w.product_id) as current_price,
    w.alert_id,
    w.created_at,
    w.updated_at
FROM user_wishlist w
JOIN products p ON w.product_id = p.id;

-- ============================================================================
-- FUNCTION: Add to wishlist with optional auto-alert
-- ============================================================================

CREATE OR REPLACE FUNCTION add_to_wishlist(
    p_user_id BIGINT,
    p_product_id BIGINT,
    p_priority SMALLINT DEFAULT 2,
    p_target_price INTEGER DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_wishlist_id BIGINT;
    v_alert_id BIGINT := NULL;
BEGIN
    -- If target_price is set, create/update price alert
    IF p_target_price IS NOT NULL THEN
        BEGIN
            v_alert_id := subscribe_to_price_alert(
                p_user_id,
                p_product_id,
                'wishlist',
                'target_price',
                p_target_price,
                5.0  -- min_drop_percent
            );
        EXCEPTION WHEN OTHERS THEN
            -- If subscribe fails (no price data), continue without alert
            v_alert_id := NULL;
        END;
    END IF;

    -- Upsert wishlist entry
    INSERT INTO user_wishlist (
        user_id, product_id, priority, target_price, notes, alert_id
    )
    VALUES (
        p_user_id, p_product_id, p_priority, p_target_price, p_notes, v_alert_id
    )
    ON CONFLICT (user_id, product_id) DO UPDATE SET
        priority = EXCLUDED.priority,
        target_price = EXCLUDED.target_price,
        notes = COALESCE(EXCLUDED.notes, user_wishlist.notes),
        alert_id = COALESCE(EXCLUDED.alert_id, user_wishlist.alert_id),
        purchased = false,  -- Re-add if was purchased
        purchased_at = NULL,
        purchased_price = NULL,
        purchased_store = NULL,
        updated_at = NOW()
    RETURNING id INTO v_wishlist_id;

    RETURN v_wishlist_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Mark wishlist item as purchased
-- ============================================================================

CREATE OR REPLACE FUNCTION mark_wishlist_purchased(
    p_wishlist_id BIGINT,
    p_price INTEGER,
    p_store TEXT
)
RETURNS VOID AS $$
DECLARE
    v_alert_id BIGINT;
BEGIN
    -- Get alert_id before update
    SELECT alert_id INTO v_alert_id
    FROM user_wishlist
    WHERE id = p_wishlist_id;

    -- Update wishlist item
    UPDATE user_wishlist
    SET purchased = true,
        purchased_at = NOW(),
        purchased_price = p_price,
        purchased_store = p_store,
        updated_at = NOW()
    WHERE id = p_wishlist_id;

    -- Disable associated alert if exists
    IF v_alert_id IS NOT NULL THEN
        UPDATE user_price_alerts
        SET enabled = false, updated_at = NOW()
        WHERE id = v_alert_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Update wishlist target price with alert sync
-- ============================================================================

CREATE OR REPLACE FUNCTION set_wishlist_target_price(
    p_user_id BIGINT,
    p_wishlist_id BIGINT,
    p_target_price INTEGER
)
RETURNS VOID AS $$
DECLARE
    v_product_id BIGINT;
    v_old_alert_id BIGINT;
    v_new_alert_id BIGINT := NULL;
BEGIN
    -- Get product_id and current alert_id
    SELECT product_id, alert_id INTO v_product_id, v_old_alert_id
    FROM user_wishlist
    WHERE id = p_wishlist_id AND user_id = p_user_id;

    IF v_product_id IS NULL THEN
        RAISE EXCEPTION 'Wishlist item not found';
    END IF;

    -- Disable old alert if exists
    IF v_old_alert_id IS NOT NULL THEN
        UPDATE user_price_alerts
        SET enabled = false, updated_at = NOW()
        WHERE id = v_old_alert_id;
    END IF;

    -- Create new alert if target_price is set
    IF p_target_price IS NOT NULL AND p_target_price > 0 THEN
        BEGIN
            v_new_alert_id := subscribe_to_price_alert(
                p_user_id,
                v_product_id,
                'wishlist',
                'target_price',
                p_target_price,
                5.0
            );
        EXCEPTION WHEN OTHERS THEN
            v_new_alert_id := NULL;
        END;
    END IF;

    -- Update wishlist item
    UPDATE user_wishlist
    SET target_price = p_target_price,
        alert_id = v_new_alert_id,
        updated_at = NOW()
    WHERE id = p_wishlist_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Get wishlist statistics for user
-- ============================================================================

CREATE OR REPLACE FUNCTION get_wishlist_stats(p_user_id BIGINT)
RETURNS TABLE (
    total_items BIGINT,
    active_items BIGINT,
    purchased_items BIGINT,
    high_priority BIGINT,
    medium_priority BIGINT,
    low_priority BIGINT,
    total_spent BIGINT,
    total_saved BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_items,
        COUNT(*) FILTER (WHERE NOT w.purchased)::BIGINT as active_items,
        COUNT(*) FILTER (WHERE w.purchased)::BIGINT as purchased_items,
        COUNT(*) FILTER (WHERE w.priority = 1 AND NOT w.purchased)::BIGINT as high_priority,
        COUNT(*) FILTER (WHERE w.priority = 2 AND NOT w.purchased)::BIGINT as medium_priority,
        COUNT(*) FILTER (WHERE w.priority = 3 AND NOT w.purchased)::BIGINT as low_priority,
        COALESCE(SUM(w.purchased_price) FILTER (WHERE w.purchased), 0)::BIGINT as total_spent,
        COALESCE(SUM(w.target_price - w.purchased_price) FILTER (
            WHERE w.purchased AND w.target_price IS NOT NULL AND w.purchased_price < w.target_price
        ), 0)::BIGINT as total_saved
    FROM user_wishlist w
    WHERE w.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION add_to_wishlist(BIGINT, BIGINT, SMALLINT, INTEGER, TEXT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION mark_wishlist_purchased(BIGINT, INTEGER, TEXT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION set_wishlist_target_price(BIGINT, BIGINT, INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_wishlist_stats(BIGINT) TO PUBLIC;
