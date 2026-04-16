"""
SQLite database schema for PineTime step tracking.
"""

SCHEMA_SQL = """
-- Daily statistics table
-- Stores aggregated step and heart rate data per day
CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,           -- YYYY-MM-DD format
    steps INTEGER DEFAULT 0,
    heart_rate_avg REAL DEFAULT 0,
    heart_rate_min INTEGER DEFAULT 0,
    heart_rate_max INTEGER DEFAULT 0,
    heart_rate_samples INTEGER DEFAULT 0, -- Number of readings for average
    synced_at TEXT,                       -- ISO timestamp of last sync
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Sync log table
-- Records all sync attempts for debugging and monitoring
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at TEXT NOT NULL,             -- ISO timestamp
    success INTEGER NOT NULL DEFAULT 0,   -- 1 = success, 0 = failure
    steps_read INTEGER DEFAULT 0,         -- Steps value at sync time
    heart_rate_read INTEGER DEFAULT 0,    -- Heart rate at sync time
    battery_level INTEGER DEFAULT -1,    -- Battery level (-1 = not read)
    error_message TEXT,                   -- Error description if failed
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
-- Stores application settings including paired device info
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster date-based queries
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);

-- Index for sync log queries
CREATE INDEX IF NOT EXISTS idx_sync_log_synced_at ON sync_log(synced_at);
"""

UPGRADE_SCRIPTS = {
    2: [
        """ALTER TABLE daily_stats ADD COLUMN heart_rate_samples INTEGER DEFAULT 0;"""
    ]
}

SETTINGS_KEYS = {
    'paired_device_address': 'MAC address of paired PineTime',
    'paired_device_name': 'Name of paired PineTime',
    'step_goal': 'Daily step goal (default: 10000)',
}
