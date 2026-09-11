from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user, require_admin

# Routes that are DELIBERATELY public. Anything not on this list must
# require auth — adding to this list requires a one-line justification
# in the PR/commit message, not just a code change.
EXPECTED_PUBLIC = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register"),
    # Actual path is "/health", not "/api/health" -- see main.py:151. The
    # "/api/health" path only exists in the legacy, unused Express stub
    # (server/routes.ts), not in this FastAPI app.
    ("GET", "/health"),
    # Same category as /health -- a deploy-verification endpoint (git SHA
    # + status), no user data, meant to be hit by uptime/deploy tooling
    # without auth. See main.py:156.
    ("GET", "/api/version"),
    # Not gated by get_current_user by design -- the refresh_token in the
    # request body *is* the credential, verified manually inside the
    # handler (decode_refresh_token + revoked/expiry check against
    # user_sessions). A bare request 422s (missing body field); an invalid
    # token 401s from inside the handler. See auth.py's refresh_token().
    ("POST", "/api/auth/refresh"),
    # Same category as /api/auth/login -- an entrypoint into the auth
    # system itself, not a protected resource. The Google id_token in the
    # body is verified against Google's tokeninfo endpoint inside the
    # handler; a bare request 422s (missing body field).
    ("POST", "/api/auth/google"),
    # Static SPA shell (index.html / assets) -- serves the same HTML/JS
    # bundle to everyone; the actual protected data lives behind /api/*
    # calls that bundle makes, gated separately. See main.py's serve_root
    # / spa_fallback.
    ("GET", "/"),
    ("GET", "/{path:path}"),
    # FastAPI-generated schema/docs routes, not app data -- safe to expose.
    ("GET", "/openapi.json"),
    ("HEAD", "/openapi.json"),
    ("GET", "/docs"),
    ("HEAD", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("HEAD", "/docs/oauth2-redirect"),
    ("GET", "/redoc"),
    ("HEAD", "/redoc"),
}


def _requires_auth(route) -> bool:
    dependant = getattr(route, "dependant", None)
    if not dependant:
        return False
    deps = [d.call for d in dependant.dependencies]
    return get_current_user in deps or require_admin in deps


def test_every_non_public_route_rejects_missing_auth():
    client = TestClient(app)
    checked = 0
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue
        methods = [m for m in route.methods if m in ("GET", "POST", "PUT", "DELETE", "PATCH")]
        if not methods:
            continue
        keys = {(m, route.path) for m in methods}
        if keys & EXPECTED_PUBLIC:
            continue
        assert _requires_auth(route), (
            f"Route {route.path} has no auth dependency and is not in "
            f"EXPECTED_PUBLIC — is this intentional? If so, add it to the "
            f"allowlist with a reason."
        )
        for method in methods:
            resp = getattr(client, method.lower())(route.path)
            assert resp.status_code in (401, 403, 422), (
                f"{method} {route.path} should reject unauthenticated "
                f"requests, got {resp.status_code}"
            )
            checked += 1
    assert checked > 0, "Sweep matched zero routes — check route introspection logic"
