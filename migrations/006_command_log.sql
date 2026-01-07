-- Command logging table for bot analytics
-- Tracks all user commands for usage analysis

CREATE TABLE IF NOT EXISTS command_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    command VARCHAR(50) NOT NULL,
    args TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_command_log_user ON command_log(user_id);
CREATE INDEX IF NOT EXISTS idx_command_log_time ON command_log(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_command_log_cmd ON command_log(command);

-- Composite index for command usage stats
CREATE INDEX IF NOT EXISTS idx_command_log_cmd_time ON command_log(command, executed_at DESC);

COMMENT ON TABLE command_log IS 'Log of all bot commands for analytics';
COMMENT ON COLUMN command_log.command IS 'Command name (e.g., search, price, stats)';
COMMENT ON COLUMN command_log.args IS 'Command arguments if any';
