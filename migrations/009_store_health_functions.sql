-- Migration 009: Store Health Monitoring Functions
-- Part of PS-46 Phase 4: Store Auto-Cleanup
--
-- Adds functions for monitoring store health and cleanup operations

-- ============================================================================
-- FUNCTION: Get Store Health Summary
-- ============================================================================
-- Returns aggregated health statistics for all stores

CREATE OR REPLACE FUNCTION get_store_health_summary()
RETURNS TABLE (
    total_stores BIGINT,
    enabled_stores BIGINT,
    disabled_stores BIGINT,
    healthy_stores BIGINT,
    warning_stores BIGINT,
    critical_stores BIGINT,
    auto_import_stores BIGINT,
    avg_failure_count FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_stores,
        COUNT(*) FILTER (WHERE enabled = true)::BIGINT as enabled_stores,
        COUNT(*) FILTER (WHERE enabled = false)::BIGINT as disabled_stores,
        COUNT(*) FILTER (WHERE failure_count < 5)::BIGINT as healthy_stores,
        COUNT(*) FILTER (WHERE failure_count >= 5 AND failure_count < 10)::BIGINT as warning_stores,
        COUNT(*) FILTER (WHERE failure_count >= 10)::BIGINT as critical_stores,
        COUNT(*) FILTER (WHERE source = 'auto_import')::BIGINT as auto_import_stores,
        AVG(failure_count)::FLOAT as avg_failure_count
    FROM stores;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Get Stores Needing Cleanup
-- ============================================================================
-- Returns stores that match cleanup criteria (for dry-run preview)

CREATE OR REPLACE FUNCTION get_stores_needing_cleanup(
    p_failure_threshold INTEGER DEFAULT 10,
    p_no_success_days_short INTEGER DEFAULT 7,
    p_no_success_days_long INTEGER DEFAULT 30,
    p_auto_import_failure_threshold INTEGER DEFAULT 5
)
RETURNS TABLE (
    store_id INTEGER,
    store_name TEXT,
    source TEXT,
    failure_count INTEGER,
    last_success_at TIMESTAMPTZ,
    cleanup_action TEXT,
    cleanup_reason TEXT
) AS $$
BEGIN
    -- Rule 1: High failures with no recent success
    RETURN QUERY
    SELECT
        s.id as store_id,
        s.name as store_name,
        s.source,
        s.failure_count,
        s.last_success_at,
        'disable'::TEXT as cleanup_action,
        format('High failures (%s) with no success in %s days', s.failure_count, p_no_success_days_short)::TEXT as cleanup_reason
    FROM stores s
    WHERE s.enabled = true
      AND s.failure_count >= p_failure_threshold
      AND (s.last_success_at IS NULL OR s.last_success_at < NOW() - (p_no_success_days_short || ' days')::INTERVAL);

    -- Rule 2: No success in 30 days
    RETURN QUERY
    SELECT
        s.id as store_id,
        s.name as store_name,
        s.source,
        s.failure_count,
        s.last_success_at,
        'disable'::TEXT as cleanup_action,
        format('No success in %s days', p_no_success_days_long)::TEXT as cleanup_reason
    FROM stores s
    WHERE s.enabled = true
      AND s.last_success_at IS NOT NULL
      AND s.last_success_at < NOW() - (p_no_success_days_long || ' days')::INTERVAL
      AND s.failure_count < p_failure_threshold;  -- Not already caught by rule 1

    -- Rule 3: Auto-import stores with too many failures
    RETURN QUERY
    SELECT
        s.id as store_id,
        s.name as store_name,
        s.source,
        s.failure_count,
        s.last_success_at,
        'delete'::TEXT as cleanup_action,
        format('Auto-imported store with %s failures', s.failure_count)::TEXT as cleanup_reason
    FROM stores s
    WHERE s.source = 'auto_import'
      AND s.failure_count >= p_auto_import_failure_threshold;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Get Candidates Needing Rejection
-- ============================================================================
-- Returns store candidates with low success rate

CREATE OR REPLACE FUNCTION get_candidates_needing_rejection(
    p_min_extractions INTEGER DEFAULT 3,
    p_min_success_rate FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    candidate_id BIGINT,
    domain TEXT,
    price_extractions INTEGER,
    successful_extractions INTEGER,
    success_rate FLOAT,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sc.id as candidate_id,
        sc.domain,
        sc.price_extractions,
        sc.successful_extractions,
        CASE WHEN sc.price_extractions > 0
             THEN (sc.successful_extractions::FLOAT / sc.price_extractions::FLOAT)
             ELSE 0.0
        END as success_rate,
        sc.status
    FROM store_candidates sc
    WHERE sc.status = 'candidate'
      AND sc.price_extractions >= p_min_extractions
      AND (sc.successful_extractions::FLOAT / NULLIF(sc.price_extractions, 0)::FLOAT) < p_min_success_rate;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Execute Store Cleanup
-- ============================================================================
-- Performs actual cleanup and returns count of affected rows
-- WARNING: This function modifies data!

CREATE OR REPLACE FUNCTION execute_store_cleanup(
    p_failure_threshold INTEGER DEFAULT 10,
    p_no_success_days_short INTEGER DEFAULT 7,
    p_no_success_days_long INTEGER DEFAULT 30,
    p_auto_import_failure_threshold INTEGER DEFAULT 5,
    p_candidate_min_extractions INTEGER DEFAULT 3,
    p_candidate_min_success_rate FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    stores_disabled INTEGER,
    stores_deleted INTEGER,
    candidates_rejected INTEGER
) AS $$
DECLARE
    v_disabled INTEGER := 0;
    v_deleted INTEGER := 0;
    v_rejected INTEGER := 0;
BEGIN
    -- Disable stores matching rule 1 and 2
    WITH to_disable AS (
        SELECT id FROM stores
        WHERE enabled = true
          AND (
            -- Rule 1
            (failure_count >= p_failure_threshold
             AND (last_success_at IS NULL OR last_success_at < NOW() - (p_no_success_days_short || ' days')::INTERVAL))
            OR
            -- Rule 2
            (last_success_at IS NOT NULL
             AND last_success_at < NOW() - (p_no_success_days_long || ' days')::INTERVAL)
          )
    )
    UPDATE stores SET enabled = false, updated_at = NOW()
    WHERE id IN (SELECT id FROM to_disable);
    GET DIAGNOSTICS v_disabled = ROW_COUNT;

    -- Delete auto-import stores with too many failures (rule 3)
    DELETE FROM stores
    WHERE source = 'auto_import'
      AND failure_count >= p_auto_import_failure_threshold;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    -- Reject low-quality candidates (rule 4)
    UPDATE store_candidates SET status = 'rejected'
    WHERE status = 'candidate'
      AND price_extractions >= p_candidate_min_extractions
      AND (successful_extractions::FLOAT / NULLIF(price_extractions, 0)::FLOAT) < p_candidate_min_success_rate;
    GET DIAGNOSTICS v_rejected = ROW_COUNT;

    RETURN QUERY SELECT v_disabled, v_deleted, v_rejected;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEW: Store Health Dashboard
-- ============================================================================
-- Quick overview of store health status

CREATE OR REPLACE VIEW v_store_health AS
SELECT
    s.id,
    s.name,
    s.source,
    s.enabled,
    s.failure_count,
    s.last_success_at,
    s.last_failure_at,
    CASE
        WHEN s.enabled = false THEN 'disabled'
        WHEN s.failure_count >= 10 THEN 'critical'
        WHEN s.failure_count >= 5 THEN 'warning'
        ELSE 'healthy'
    END as health_status,
    CASE
        WHEN s.last_success_at IS NULL THEN NULL
        ELSE EXTRACT(DAY FROM (NOW() - s.last_success_at))
    END as days_since_success
FROM stores s
ORDER BY s.failure_count DESC, s.name;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION get_store_health_summary() TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_stores_needing_cleanup(INTEGER, INTEGER, INTEGER, INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_candidates_needing_rejection(INTEGER, FLOAT) TO PUBLIC;
GRANT EXECUTE ON FUNCTION execute_store_cleanup(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER, FLOAT) TO PUBLIC;
