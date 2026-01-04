-- Price Scout Store Seed Data
-- Version: 002
-- Description: Initial store/marketplace data
-- Author: Price Scout Team
-- Created: 2026-01-04

-- ============================================================================
-- STORES DATA
-- ============================================================================
-- Populate stores table with current marketplace configurations

-- Delete existing data (for re-running migration)
DELETE FROM stores;

-- Reset sequence
ALTER SEQUENCE stores_id_seq RESTART WITH 1;

-- Insert stable stores (unstable=false)
INSERT INTO stores (name, base_url, method, parser, unstable) VALUES
('dns', 'https://www.dns-shop.ru', 'firefox', 'dns_json', false),
('ozon', 'https://www.ozon.ru', 'ozon_firefox', 'generic', false),
('i-ray', 'https://i-ray.ru', 'playwright_direct', 'generic', false),
('nix', 'https://www.nix.ru', 'playwright_direct', 'generic', false),
('regard', 'https://www.regard.ru', 'playwright_stealth', 'generic', false),
('kns', 'https://www.kns.ru', 'playwright_direct', 'generic', false),
('yandex_market', 'https://market.yandex.ru', 'yandex_market_special', 'yandex_json', false),
('avito', 'https://www.avito.ru', 'avito_firefox', 'generic', false);

-- Insert unstable stores (unstable=true)
INSERT INTO stores (name, base_url, method, parser, unstable) VALUES
('citilink', 'https://www.citilink.ru', 'citilink_firefox', 'citilink_json', true);

-- ============================================================================
-- STORE DETAILS
-- ============================================================================

COMMENT ON TABLE stores IS 'Updated: 2026-01-04 - 9 stores total (8 stable + 1 unstable)';

-- Verification query
DO $$
DECLARE
    stable_count INTEGER;
    unstable_count INTEGER;
    total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO stable_count FROM stores WHERE unstable = false;
    SELECT COUNT(*) INTO unstable_count FROM stores WHERE unstable = true;
    SELECT COUNT(*) INTO total_count FROM stores;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Store Seed Data Loaded Successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total stores: %', total_count;
    RAISE NOTICE 'Stable stores: %', stable_count;
    RAISE NOTICE 'Unstable stores: %', unstable_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Stable stores:';
    RAISE NOTICE '  1. dns (Firefox + xdotool, 38.2s)';
    RAISE NOTICE '  2. ozon (Firefox + xdotool, 52.4s)';
    RAISE NOTICE '  3. i-ray (Playwright Direct, 4.1s)';
    RAISE NOTICE '  4. nix (Playwright Direct, 3.6s)';
    RAISE NOTICE '  5. regard (Playwright Stealth, 7.9s)';
    RAISE NOTICE '  6. kns (Playwright Direct, 3.5s)';
    RAISE NOTICE '  7. yandex_market (Playwright Stealth, 15.4s)';
    RAISE NOTICE '  8. avito (Firefox + xdotool, 46.6s)';
    RAISE NOTICE '';
    RAISE NOTICE 'Unstable stores:';
    RAISE NOTICE '  9. citilink (Rate limiting, manual testing only)';
    RAISE NOTICE '========================================';
END $$;

-- Show all stores
SELECT
    id,
    name,
    method,
    parser,
    CASE WHEN unstable THEN '[UNSTABLE]' ELSE '[STABLE]' END AS status
FROM stores
ORDER BY unstable, id;
