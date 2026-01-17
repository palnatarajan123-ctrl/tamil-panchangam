-- ============================================================
-- EPIC-6 — Tamil Panchangam Persistence Schema
-- SQLite
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. BASE CHARTS (IMMUTABLE ASTROLOGICAL TRUTH)
-- ============================================================

CREATE TABLE IF NOT EXISTS base_charts (
    id TEXT PRIMARY KEY,                 -- UUID
    checksum TEXT NOT NULL,               -- hash of payload
    locked BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL,
    payload TEXT NOT NULL,                -- JSON (stored as TEXT)
    engine_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_base_charts_checksum
    ON base_charts(checksum);

CREATE INDEX IF NOT EXISTS idx_base_charts_created_at
    ON base_charts(created_at);

-- ============================================================
-- 2. CHART ARTIFACTS (RENDER-READY CHARTS)
-- ============================================================

CREATE TABLE IF NOT EXISTS chart_artifacts (
    id TEXT PRIMARY KEY,                  -- UUID
    base_chart_id TEXT NOT NULL,
    chart_type TEXT NOT NULL,              -- panchangam, D1, D9, D10, etc.
    chart_name TEXT,
    payload TEXT NOT NULL,                 -- JSON (stored as TEXT)
    engine_version TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,

    FOREIGN KEY (base_chart_id)
        REFERENCES base_charts(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chart_artifacts_base_chart
    ON chart_artifacts(base_chart_id);

CREATE INDEX IF NOT EXISTS idx_chart_artifacts_type
    ON chart_artifacts(chart_type);

-- ============================================================
-- 3. MONTHLY PREDICTIONS (DETERMINISTIC DERIVED OUTPUT)
-- ============================================================

CREATE TABLE IF NOT EXISTS monthly_predictions (
    id TEXT PRIMARY KEY,                   -- base_chart_id:year:month
    base_chart_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    status TEXT NOT NULL,                  -- ok | stub | error
    created_at TIMESTAMP NOT NULL,

    envelope TEXT NOT NULL,                -- JSON
    synthesis TEXT NOT NULL,               -- JSON
    interpretation TEXT,                   -- JSON (nullable)

    engine_version TEXT NOT NULL,

    FOREIGN KEY (base_chart_id)
        REFERENCES base_charts(id)
        ON DELETE CASCADE,

    UNIQUE (base_chart_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_predictions_base_chart
    ON monthly_predictions(base_chart_id);

CREATE INDEX IF NOT EXISTS idx_monthly_predictions_year_month
    ON monthly_predictions(year, month);

-- ============================================================
-- 4. ENGINE RUN METADATA (OPTIONAL BUT RECOMMENDED)
-- ============================================================

CREATE TABLE IF NOT EXISTS engine_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engine TEXT NOT NULL,
    version TEXT NOT NULL,
    run_at TIMESTAMP NOT NULL,
    notes TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_monthly_prediction
ON monthly_predictions (base_chart_id, year, month, engine_version);

CREATE TABLE IF NOT EXISTS prediction_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,      -- envelope | synthesis | interpretation
    payload TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,

    FOREIGN KEY (prediction_id)
        REFERENCES monthly_predictions(id)
        ON DELETE CASCADE
);

-- ============================================================
-- END OF SCHEMA
-- ============================================================
