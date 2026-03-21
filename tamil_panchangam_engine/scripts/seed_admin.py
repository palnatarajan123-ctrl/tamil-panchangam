#!/usr/bin/env python
"""
Create the first admin user from environment variables.

Usage:
    ADMIN_EMAIL=admin@example.com \
    ADMIN_PASSWORD=secret \
    ADMIN_NAME="Site Admin" \
    python scripts/seed_admin.py
"""

import os
import sys
import uuid

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.db.bootstrap import bootstrap
from app.db.duckdb import get_conn
from app.core.auth import hash_password


def seed():
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "").strip()
    name = os.environ.get("ADMIN_NAME", "Admin").strip()

    if not email or not password:
        print("❌ ADMIN_EMAIL and ADMIN_PASSWORD env vars are required.")
        sys.exit(1)

    bootstrap()

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, role FROM users WHERE email = ?", [email]
        ).fetchone()

        if existing:
            user_id, role = existing
            if role == "admin":
                print(f"ℹ️  Admin already exists: {email} (id={user_id})")
            else:
                conn.execute(
                    "UPDATE users SET role = 'admin', password_hash = ? WHERE id = ?",
                    [hash_password(password), user_id],
                )
                print(f"✅ Promoted existing user to admin: {email}")
        else:
            user_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO users (id, email, name, password_hash, role, is_active, created_at)
                   VALUES (?, ?, ?, ?, 'admin', TRUE, CURRENT_TIMESTAMP)""",
                [user_id, email, name, hash_password(password)],
            )
            print(f"✅ Admin user created: {email} (id={user_id})")


if __name__ == "__main__":
    seed()
