-- Price Scout Currency Rates
-- Version: 003
-- Description: Currency exchange rates tracking (USD/EUR vs RUB)
-- Author: Price Scout Team
-- Created: 2026-01-05

-- ============================================================================
-- CURRENCY RATES TABLE
-- ============================================================================
-- Tracks exchange rates from multiple sources for correlation analysis

CREATE TABLE IF NOT EXISTS currency_rates (
    id BIGSERIAL PRIMARY KEY,
    currency_code TEXT NOT NULL CHECK (currency_code IN ('USD', 'EUR')),
    rate_to_rub NUMERIC(10, 4) NOT NULL CHECK (rate_to_rub > 0),
    source TEXT NOT NULL CHECK (source IN ('cbr_ru', 'open_er')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Query latest rate for specific currency (primary use case)
CREATE INDEX idx_currency_rates_time ON currency_rates(currency_code, recorded_at DESC);

-- Query by source + currency (for data quality checks)
CREATE INDEX idx_currency_rates_source ON currency_rates(source, currency_code);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE currency_rates IS 'Exchange rates tracking: USD/EUR -> RUB from dual sources';
COMMENT ON COLUMN currency_rates.currency_code IS 'Currency code: USD or EUR';
COMMENT ON COLUMN currency_rates.rate_to_rub IS 'Exchange rate to Russian Ruble (e.g. 95.5000 for 1 USD = 95.50 RUB)';
COMMENT ON COLUMN currency_rates.source IS 'Data source: cbr_ru (Central Bank of Russia) or open_er (open.er-api.com)';
COMMENT ON COLUMN currency_rates.recorded_at IS 'Timestamp when rate was recorded';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 003: Currency Rates Created!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Table: currency_rates';
    RAISE NOTICE 'Indexes: 2 (time, source)';
    RAISE NOTICE 'Constraints: currency_code IN (USD, EUR), source IN (cbr_ru, open_er)';
    RAISE NOTICE '';
    RAISE NOTICE 'Data sources:';
    RAISE NOTICE '  1. cbr_ru - Central Bank of Russia (official daily rates)';
    RAISE NOTICE '  2. open_er - open.er-api.com (free API, no key required)';
    RAISE NOTICE '========================================';
END $$;
