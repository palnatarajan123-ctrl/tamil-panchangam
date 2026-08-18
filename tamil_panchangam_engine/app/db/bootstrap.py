"""
PostgreSQL schema bootstrap.
Creates all tables if they don't exist.
"""
import os
import uuid
import logging
from app.db.postgres import get_conn

logger = logging.getLogger(__name__)


def bootstrap():
    conn = get_conn()
    try:
        # base_charts
        conn.execute("""
        CREATE TABLE IF NOT EXISTS base_charts (
            id TEXT PRIMARY KEY,
            locked BOOLEAN,
            payload JSONB
        )
        """)

        # monthly_predictions
        conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_predictions (
            id TEXT PRIMARY KEY,
            base_chart_id TEXT,
            year INTEGER,
            month INTEGER,
            status TEXT,
            envelope JSONB,
            synthesis JSONB,
            interpretation JSONB,
            engine_version TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        # yearly_predictions
        conn.execute("""
        CREATE TABLE IF NOT EXISTS yearly_predictions (
            id TEXT PRIMARY KEY,
            base_chart_id TEXT,
            year INTEGER,
            status TEXT,
            envelope JSONB,
            synthesis JSONB,
            interpretation JSONB,
            engine_version TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """)

        # weekly_predictions
        conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_predictions (
            id TEXT PRIMARY KEY,
            base_chart_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            week INTEGER NOT NULL,
            status TEXT NOT NULL,
            envelope JSONB NOT NULL,
            synthesis JSONB NOT NULL,
            interpretation JSONB NOT NULL,
            engine_version TEXT NOT NULL,
            generated_at TIMESTAMP NOT NULL
        )
        """)

        # prediction_llm_interpretation
        conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_llm_interpretation (
            id TEXT PRIMARY KEY,
            base_chart_id TEXT NOT NULL,
            period_type TEXT NOT NULL,
            period_key TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            prompt_version TEXT NOT NULL,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            content_json JSONB,
            fallback_reason TEXT,
            reflection_text TEXT,
            explainability_mode TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """)

        # migration: add prompt_version to existing prediction_llm_interpretation tables
        try:
            conn.execute("ALTER TABLE prediction_llm_interpretation ADD COLUMN IF NOT EXISTS prompt_version TEXT DEFAULT 'v4'")
        except Exception:
            pass

        # llm_token_usage
        conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_token_usage (
            id TEXT PRIMARY KEY,
            feature_name TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            total_tokens INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """)

        # llm_config
        conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """)

        conn.execute("""
        INSERT INTO llm_config (key, value, updated_at)
        VALUES ('llm_enabled', 'false', NOW())
        ON CONFLICT (key) DO NOTHING
        """)

        # users
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            google_id TEXT UNIQUE,
            name TEXT NOT NULL,
            avatar_url TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_login_at TIMESTAMP
        )
        """)

        # user_sessions
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            refresh_token_hash TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMP
        )
        """)

        # user_charts
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_charts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            base_chart_id TEXT NOT NULL,
            nickname TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """)

        # audit_log
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            details JSONB,
            ip_address TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """)

        # chat_messages
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            base_chart_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        # chat_usage
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_usage (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            base_chart_id TEXT NOT NULL,
            month_key TEXT NOT NULL,
            question_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, base_chart_id, month_key)
        )
        """)

        # llm_calls — unified log for prediction + chat LLM calls
        conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_calls (
            id TEXT PRIMARY KEY,
            chart_id TEXT,
            call_type TEXT DEFAULT 'prediction',
            period TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            status TEXT DEFAULT 'success',
            fallback_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # llm_budget — singleton budget config row (id always = 1)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_budget (
            id INTEGER PRIMARY KEY,
            monthly_budget_usd REAL DEFAULT 50.0,
            auto_pause_enabled BOOLEAN DEFAULT TRUE,
            auto_pause_threshold_pct INTEGER DEFAULT 90,
            llm_enabled BOOLEAN DEFAULT TRUE,
            paused_reason TEXT,
            paused_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.execute("""
        INSERT INTO llm_budget (id) VALUES (1) ON CONFLICT DO NOTHING
        """)

        # family_groups
        conn.execute("""
        CREATE TABLE IF NOT EXISTS family_groups (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            primary_chart_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # migration: add column to existing tables
        try:
            conn.execute("ALTER TABLE family_groups ADD COLUMN IF NOT EXISTS primary_chart_id TEXT")
        except Exception:
            pass

        # family_members
        conn.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
            chart_id TEXT NOT NULL REFERENCES base_charts(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('husband', 'wife', 'child', 'other')),
            display_name TEXT,
            birth_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # family_predictions
        conn.execute("""
        CREATE TABLE IF NOT EXISTS family_predictions (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
            year INTEGER NOT NULL,
            raw_response TEXT,
            financial_peaks TEXT,
            caution_windows TEXT,
            child_milestones TEXT,
            executive_summary TEXT,
            llm_tokens_used INTEGER DEFAULT 0,
            prompt_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, year)
        )
        """)
        # migration: add column to existing tables (same pattern as
        # family_groups.primary_chart_id above) -- see
        # app/engines/family_prediction_engine.py PROMPT_VERSION for why
        # this exists: family_predictions had no version-gating mechanism,
        # so a prompt/context change would silently keep serving stale
        # cached rows for any group with an existing prediction that year.
        try:
            conn.execute("ALTER TABLE family_predictions ADD COLUMN IF NOT EXISTS prompt_version TEXT")
        except Exception:
            pass

        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_family_predictions_group
            ON family_predictions(group_id)
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS family_children_timing (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
            year_from INTEGER NOT NULL,
            year_to INTEGER NOT NULL,
            raw_response TEXT,
            has_children_already INTEGER DEFAULT 0,
            husband_5th_analysis TEXT,
            wife_5th_analysis TEXT,
            jupiter_transits TEXT,
            combined_windows TEXT,
            overall_outlook TEXT,
            llm_tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, year_from, year_to)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS family_timeline_cache (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
            from_year INTEGER NOT NULL,
            to_year INTEGER NOT NULL,
            timeline_data TEXT NOT NULL,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, from_year, to_year)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS family_child_predictions (
            id TEXT PRIMARY KEY,
            member_id TEXT NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
            year INTEGER NOT NULL,
            raw_response TEXT,
            education TEXT,
            career_aptitude TEXT,
            marriage_window TEXT,
            leaving_home TEXT,
            health_cautions TEXT,
            key_takeaways TEXT,
            overall_narrative TEXT,
            llm_tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(member_id, year)
        )
        """)

        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_family_children_timing_group
            ON family_children_timing(group_id)
        """)

        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_family_timeline_group
            ON family_timeline_cache(group_id)
        """)

        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_family_child_predictions_member
            ON family_child_predictions(member_id)
        """)

        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_family_groups_user_id ON family_groups(user_id)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_family_members_group_id ON family_members(group_id)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_family_members_chart_id ON family_members(chart_id)
        """)

        # family_porutham_cache
        conn.execute("""
        CREATE TABLE IF NOT EXISTS family_porutham_cache (
            id SERIAL PRIMARY KEY,
            group_id TEXT NOT NULL,
            member_id_1 TEXT NOT NULL,
            member_id_2 TEXT NOT NULL,
            result_json JSONB NOT NULL,
            computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(group_id, member_id_1, member_id_2)
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_porutham_cache_group
            ON family_porutham_cache(group_id)
        """)

        # porutham_prospects (Phase G1) -- chart-to-chart compatibility
        # links, independent of family_groups. A prospect link IS the
        # pairing entity (unlike family_porutham_cache, which caches
        # against a group's members that exist regardless of any specific
        # pairing), so its computed Porutham result lives directly on this
        # row (result_json) rather than in a separate cache table --
        # decided during G1 rather than mirroring family_porutham_cache's
        # separate-table shape, since here it would just duplicate this
        # table's own primary key.
        #
        # source_role records which chart is the "boy" input to
        # compute_porutham() (the other is "girl") -- required because
        # several Porutham categories (Dinam, Mahendra, Stree Deergha) are
        # direction-sensitive and chart payloads carry no reliable gender
        # field (checked: birth_details.gender exists in the schema but is
        # null on every chart in the DB today).
        conn.execute("""
        CREATE TABLE IF NOT EXISTS porutham_prospects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            source_chart_id TEXT NOT NULL REFERENCES base_charts(id) ON DELETE CASCADE,
            candidate_chart_id TEXT NOT NULL REFERENCES base_charts(id) ON DELETE CASCADE,
            source_role TEXT NOT NULL CHECK (source_role IN ('boy', 'girl')),
            result_json JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_porutham_prospects_user
            ON porutham_prospects(user_id)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_porutham_prospects_source
            ON porutham_prospects(source_chart_id)
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_porutham_prospects_candidate
            ON porutham_prospects(candidate_chart_id)
        """)

        conn.commit()
        logger.info("PostgreSQL schema bootstrapped successfully")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def seed_admin_from_env():
    """Auto-create admin from env vars if not exists."""
    import bcrypt

    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    name = os.environ.get("ADMIN_NAME", "Admin")

    if not email or not password:
        return

    try:
        conn = get_conn()
        try:
            conn.execute("SELECT id FROM users WHERE email = %s", [email.lower()])
            existing = conn.fetchone()
            if not existing:
                hashed = bcrypt.hashpw(
                    password.encode("utf-8"),
                    bcrypt.gensalt(),
                ).decode("utf-8")
                conn.execute(
                    """
                    INSERT INTO users (id, email, password_hash, name, role)
                    VALUES (%s, %s, %s, %s, 'admin')
                    """,
                    [str(uuid.uuid4()), email.lower(), hashed, name],
                )
                conn.commit()
                logger.info(f"Admin seeded: {email}")
            else:
                logger.info(f"Admin already exists: {email}")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Admin seed failed: {e}")


if __name__ == "__main__":
    bootstrap()
    seed_admin_from_env()
    print("PostgreSQL schema initialized")
