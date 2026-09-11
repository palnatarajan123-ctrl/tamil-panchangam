// client/src/lib/turnstile.ts
// Shared Cloudflare Turnstile site key -- was duplicated as a literal in
// chart-form.tsx; extracted here (2026-09-10, Task 3/backlog #1) so
// register.tsx uses the exact same value with no risk of the two drifting
// if it's ever rotated.
export const TURNSTILE_SITE_KEY = "0x4AAAAAACuBMk9QffkMSOPv"; // Cloudflare test key (always passes)
