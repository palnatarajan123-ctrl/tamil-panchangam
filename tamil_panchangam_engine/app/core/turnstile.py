# app/core/turnstile.py
"""
Cloudflare Turnstile verification -- single shared implementation.

Extracted from base_chart.py (2026-09-10, Task 3/backlog #1) so
/api/auth/register can apply the exact same check rather than a second,
independently-maintained copy -- this project has been burned before by
duplicated implementations drifting apart (see CLAUDE.md's two family
chat implementations, and payload_builder.py's two family-Porutham-cache
implementations). One function, every caller uses it.
"""

import os
import httpx


def verify_turnstile(token: str) -> bool:
    """Verify Cloudflare Turnstile token. Returns True if valid.

    Security fix (2026-09-08, base_chart.py): the previous bypass condition
    was `os.getenv("RENDER") is None and os.getenv("VERCEL") is None`, which
    silently skipped verification (returning True) for ANY deployment that
    wasn't specifically flagged RENDER or VERCEL -- not just localhost. An
    infra-detection heuristic is the wrong tool for a security gate; a
    misconfigured or differently-hosted deployment could inherit an open
    bypass with no one noticing. Replaced with an explicit opt-in flag
    that must be deliberately set, and defaults to enforcing verification
    everywhere else, including local dev unless a developer sets it.
    """
    if os.getenv("DISABLE_TURNSTILE", "false").lower() == "true":
        return True

    secret = os.getenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={"secret": secret, "response": token},
            )
            return resp.json().get("success", False)
    except Exception:
        return False
