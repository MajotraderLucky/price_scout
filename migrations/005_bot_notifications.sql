-- Migration: Bot Notifications
-- Adds support for automatic analytics notifications

-- Add chat_id and notifications settings to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS chat_id BIGINT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT true;

-- Index for quick lookup of notification recipients
CREATE INDEX IF NOT EXISTS idx_users_notifications
    ON users(notifications_enabled)
    WHERE notifications_enabled = true AND chat_id IS NOT NULL;

-- Scraping batches table for tracking batch statistics
CREATE TABLE IF NOT EXISTS scraping_batches (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    jobs_total INTEGER NOT NULL DEFAULT 0,
    jobs_success INTEGER NOT NULL DEFAULT 0,
    jobs_failed INTEGER NOT NULL DEFAULT 0,
    price_changes INTEGER NOT NULL DEFAULT 0,
    notification_sent BOOLEAN NOT NULL DEFAULT false
);

-- Index for finding unnotified batches
CREATE INDEX IF NOT EXISTS idx_scraping_batches_unnotified
    ON scraping_batches(notification_sent)
    WHERE notification_sent = false AND completed_at IS NOT NULL;

-- Notification log for history and deduplication
CREATE TABLE IF NOT EXISTS notification_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    batch_id BIGINT REFERENCES scraping_batches(id) ON DELETE SET NULL,
    notification_type TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT notification_type_check CHECK (
        notification_type IN ('batch_complete', 'price_alert', 'arbitrage')
    )
);

CREATE INDEX IF NOT EXISTS idx_notification_log_user ON notification_log(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log(sent_at DESC);

-- Price change events for detailed tracking
CREATE TABLE IF NOT EXISTS price_change_events (
    id BIGSERIAL PRIMARY KEY,
    batch_id BIGINT REFERENCES scraping_batches(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    old_price INTEGER NOT NULL,
    new_price INTEGER NOT NULL,
    change_percent DOUBLE PRECISION NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_change_events_batch ON price_change_events(batch_id);
CREATE INDEX IF NOT EXISTS idx_price_change_events_product ON price_change_events(product_id);
CREATE INDEX IF NOT EXISTS idx_price_change_events_detected ON price_change_events(detected_at DESC);

-- Comment for documentation
COMMENT ON TABLE scraping_batches IS 'Tracks scraping batch statistics for notifications';
COMMENT ON TABLE notification_log IS 'History of sent notifications';
COMMENT ON TABLE price_change_events IS 'Detected price changes per batch for notification content';
