-- ============================================================
-- EPIC-6.4.1 — Prediction Persistence Extensions
-- Safe, idempotent, backward-compatible
-- ============================================================

BEGIN TRANSACTION;

-- ------------------------------------------------------------
-- 1. Prevent duplicate monthly predictions
-- ------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS uq_monthly_prediction
ON monthly_predictions (
    base_chart_id,
    year,
    month,
    engine_version
);

-- ------------------------------------------------------------
-- 2. Normalized prediction artifacts table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prediction_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    prediction_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
        -- envelope | synthesis | interpretation | future

    payload TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,

    FOREIGN KEY (prediction_id)
        REFERENCES monthly_predictions(id)
        ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 3. Helpful index for artifact retrieval
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_prediction_artifacts_lookup
ON prediction_artifacts (prediction_id, artifact_type);

COMMIT;
