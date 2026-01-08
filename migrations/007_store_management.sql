-- ============================================================================
-- MIGRATION 007: Store Management System
-- ============================================================================
-- Adds fields for dynamic store management, health tracking, and auto-import
-- Part of PS-46: Store Analytics System

-- ============================================================================
-- EXTEND STORES TABLE
-- ============================================================================

-- Source of store addition
ALTER TABLE stores ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'migration'
    CHECK (source IN ('migration', 'manual', 'auto_import'));

-- Health tracking
ALTER TABLE stores ADD COLUMN IF NOT EXISTS last_success_at TIMESTAMPTZ;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS failure_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS last_failure_at TIMESTAMPTZ;

-- Enable/disable without deletion
ALTER TABLE stores ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT true;

-- Priority for scraping order (1-100, higher = more important)
ALTER TABLE stores ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 50
    CHECK (priority BETWEEN 1 AND 100);

-- Last update timestamp
ALTER TABLE stores ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Relax method constraint for generic stores
ALTER TABLE stores DROP CONSTRAINT IF EXISTS stores_method_valid;
ALTER TABLE stores ADD CONSTRAINT stores_method_valid CHECK (method IN (
    'firefox', 'playwright_direct', 'playwright_stealth',
    'ozon_firefox', 'citilink_firefox', 'avito_firefox',
    'yandex_market_special', 'generic_http', 'generic_playwright'
));

-- ============================================================================
-- INDEXES FOR STORE MANAGEMENT
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_stores_enabled ON stores(enabled) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_stores_failure_count ON stores(failure_count DESC);
CREATE INDEX IF NOT EXISTS idx_stores_last_success ON stores(last_success_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_stores_source ON stores(source);
CREATE INDEX IF NOT EXISTS idx_stores_priority ON stores(priority DESC);

-- ============================================================================
-- STORE CANDIDATES TABLE (for auto-import)
-- ============================================================================

CREATE TABLE IF NOT EXISTS store_candidates (
    id BIGSERIAL PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,
    base_url TEXT NOT NULL,
    sample_urls TEXT[] NOT NULL DEFAULT '{}',

    -- Extraction statistics
    price_extractions INTEGER NOT NULL DEFAULT 0,
    successful_extractions INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',    -- Initial state, collecting data
        'testing',      -- Running stability tests
        'promoted',     -- Promoted to full store
        'rejected'      -- Failed tests, rejected
    )),

    -- Link to promoted store (if any)
    promoted_to_store_id INTEGER REFERENCES stores(id)
);

CREATE INDEX IF NOT EXISTS idx_store_candidates_domain ON store_candidates(domain);
CREATE INDEX IF NOT EXISTS idx_store_candidates_status ON store_candidates(status);
CREATE INDEX IF NOT EXISTS idx_store_candidates_success_rate ON store_candidates(
    (CASE WHEN price_extractions > 0
     THEN successful_extractions::float / price_extractions
     ELSE 0 END) DESC
);

COMMENT ON TABLE store_candidates IS 'Candidate stores discovered from web search, pending promotion';
COMMENT ON COLUMN store_candidates.sample_urls IS 'Sample product URLs where prices were extracted';
COMMENT ON COLUMN store_candidates.status IS 'candidate -> testing -> promoted/rejected';

-- ============================================================================
-- STORE HEALTH VIEW
-- ============================================================================

CREATE OR REPLACE VIEW v_store_health AS
SELECT
    id,
    name,
    base_url,
    method,
    enabled,
    unstable,
    source,
    priority,
    failure_count,
    last_success_at,
    last_failure_at,
    created_at,
    updated_at,
    CASE
        WHEN NOT enabled THEN 'disabled'
        WHEN failure_count >= 10 THEN 'critical'
        WHEN failure_count >= 5 THEN 'unhealthy'
        WHEN last_success_at IS NULL THEN 'unknown'
        WHEN last_success_at < NOW() - INTERVAL '7 days' THEN 'stale'
        ELSE 'healthy'
    END AS health_status,
    CASE
        WHEN last_success_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (NOW() - last_success_at)) / 3600
        ELSE NULL
    END AS hours_since_success
FROM stores;

COMMENT ON VIEW v_store_health IS 'Store health status based on failure count and last success';

-- ============================================================================
-- STORE HEALTH STATISTICS FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION get_store_health_stats()
RETURNS TABLE (
    total_stores BIGINT,
    enabled_stores BIGINT,
    healthy_stores BIGINT,
    unhealthy_stores BIGINT,
    critical_stores BIGINT,
    disabled_stores BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_stores,
        COUNT(*) FILTER (WHERE enabled)::BIGINT as enabled_stores,
        COUNT(*) FILTER (WHERE enabled AND failure_count < 5 AND (last_success_at IS NULL OR last_success_at >= NOW() - INTERVAL '7 days'))::BIGINT as healthy_stores,
        COUNT(*) FILTER (WHERE enabled AND failure_count >= 5 AND failure_count < 10)::BIGINT as unhealthy_stores,
        COUNT(*) FILTER (WHERE enabled AND failure_count >= 10)::BIGINT as critical_stores,
        COUNT(*) FILTER (WHERE NOT enabled)::BIGINT as disabled_stores
    FROM stores;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- AUTO-CLEANUP FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION auto_cleanup_stores()
RETURNS INTEGER AS $$
DECLARE
    disabled_count INTEGER := 0;
BEGIN
    -- Disable stores with too many failures and no recent success
    UPDATE stores
    SET enabled = false, updated_at = NOW()
    WHERE failure_count >= 10
      AND (last_success_at IS NULL OR last_success_at < NOW() - INTERVAL '7 days')
      AND enabled = true
      AND source != 'migration';  -- Don't auto-disable original stores

    GET DIAGNOSTICS disabled_count = ROW_COUNT;
    RETURN disabled_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION auto_cleanup_stores IS 'Automatically disable unhealthy stores';

-- ============================================================================
-- UPDATE EXISTING STORES
-- ============================================================================

-- Set source='migration' for existing stores
UPDATE stores SET source = 'migration' WHERE source IS NULL;
UPDATE stores SET updated_at = created_at WHERE updated_at IS NULL;
