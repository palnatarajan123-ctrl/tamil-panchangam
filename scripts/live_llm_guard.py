"""
Spend guard for live Anthropic API batches run from local scripts
(A/B tests, backfills, one-off checks). Added 2026-10-03.

Why: production and local scripts share ONE API key / billing account. On
2026-10-02/03 ~1,700 unguarded test calls (~9M tokens) drained the balance
and production chat failed until it was topped up. Script calls bypass the
app's own ledgers (llm_calls / llm_token_usage), so nothing in the app sees
them coming. This module is the only sanctioned way to fire a batch.

What it enforces:
  1. estimate()  -- input tokens via the free count_tokens endpoint (one
     call per distinct prompt), output costed at max_tokens (upper bound).
  2. approve()   -- prints the estimate; a batch over APPROVAL_CALLS calls
     or APPROVAL_USD dollars REFUSES (SpendNotApproved) unless the env var
     LIVE_LLM_APPROVAL equals that estimate's code, e.g. "120:452" (calls:
     cents). The code is tied to the estimate, so a bigger batch needs a
     new go-ahead. CLAUDE.md rule: the code is only set after the USER
     approves the printed estimate.
  3. preflight() -- a 1-token probe. Anthropic has NO API that returns the
     remaining prepaid balance (the Usage & Cost Admin API is historical
     only, needs an sk-ant-admin key, and isn't available to individual
     accounts), so this proves the account can be billed right now, not
     how much is left. Check the Console balance against the estimate.
  4. run()       -- per-request failures are recorded, not raised; every
     finished reply is appended to a JSONL file as it arrives; the first
     billing error (or actual spend passing OVERRUN_FACTOR x the approved
     estimate; for an under-threshold batch, passing APPROVAL_USD) stops ALL
     further requests -- requests not yet sent are
     marked "skipped", in-flight ones finish.

Usage:
    from live_llm_guard import SpendGuard
    g = SpendGuard(model="claude-sonnet-4-6", label="chat A/B r17")
    reqs = [dict(system=sp, messages=msgs, max_tokens=1024, meta={"arm": "A", "i": i}) ...]
    g.estimate(reqs); g.approve(); g.preflight()
    out = g.run(reqs, out_path=".../r17.jsonl", workers=4)
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

APPROVAL_CALLS = 20      # more than this many calls needs approval
APPROVAL_USD = 0.50      # or an estimated cost above this
OVERRUN_FACTOR = 1.5     # stop if actual spend passes 1.5x the approved estimate

# USD per million tokens (input, output). Unknown model -> refuse; add a
# verified price before using a new model.
PRICES = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}


class SpendNotApproved(RuntimeError):
    pass


class BillingUnavailable(RuntimeError):
    pass


def is_billing_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "credit balance" in text or "billing" in text or "purchase credits" in text


@dataclass
class Estimate:
    calls: int
    input_tokens: int
    max_output_tokens: int
    usd: float

    @property
    def code(self) -> str:
        return f"{self.calls}:{round(self.usd * 100)}"

    @property
    def needs_approval(self) -> bool:
        return self.calls > APPROVAL_CALLS or self.usd > APPROVAL_USD


@dataclass
class BatchResult:
    ok: List[Dict[str, Any]] = field(default_factory=list)
    failed: List[Dict[str, Any]] = field(default_factory=list)
    skipped: List[Dict[str, Any]] = field(default_factory=list)
    stop_reason: Optional[str] = None
    actual_usd: float = 0.0


class SpendGuard:
    def __init__(self, model: str, label: str, client: Any = None, env: Optional[Dict[str, str]] = None,
                 log: Callable[[str], None] = print):
        if model not in PRICES:
            raise SpendNotApproved(f"no price on file for model {model!r}; add it to PRICES first")
        if client is None:
            import anthropic
            client = anthropic.Anthropic(max_retries=4)  # 429/5xx backoff is the SDK's
        self.model, self.label, self.client, self.log = model, label, client, log
        self.env = os.environ if env is None else env
        self.estimate_: Optional[Estimate] = None
        self.approved = False
        self.preflighted = False

    # ── 1. estimate ──────────────────────────────────────────────────────
    def estimate(self, requests: List[Dict[str, Any]]) -> Estimate:
        cache: Dict[str, int] = {}
        total_in = total_out = 0
        for r in requests:
            key = hashlib.sha256(json.dumps([r.get("system"), r["messages"]], sort_keys=True).encode()).hexdigest()
            if key not in cache:
                kw = {"model": self.model, "messages": r["messages"]}
                if r.get("system"):
                    kw["system"] = r["system"]
                cache[key] = self.client.messages.count_tokens(**kw).input_tokens
            total_in += cache[key]
            total_out += r["max_tokens"]
        pin, pout = PRICES[self.model]
        est = Estimate(len(requests), total_in, total_out, total_in * pin / 1e6 + total_out * pout / 1e6)
        self.estimate_, self.approved = est, False
        self.log(f"[spend-guard] {self.label}: {est.calls} calls to {self.model}, "
                 f"{est.input_tokens:,} input + up to {est.max_output_tokens:,} output tokens "
                 f"= up to ${est.usd:.2f}  (approval code {est.code})")
        return est

    # ── 2. approve ───────────────────────────────────────────────────────
    def approve(self) -> None:
        est = self.estimate_
        if est is None:
            raise SpendNotApproved("call estimate() before approve()")
        if not est.needs_approval:
            self.log(f"[spend-guard] under the approval threshold "
                     f"(<= {APPROVAL_CALLS} calls and <= ${APPROVAL_USD:.2f}); proceeding")
            self.approved = True
            return
        given = self.env.get("LIVE_LLM_APPROVAL", "")
        if given != est.code:
            raise SpendNotApproved(
                f"REFUSING: {est.calls} calls / up to ${est.usd:.2f} is over the approval threshold "
                f"(> {APPROVAL_CALLS} calls or > ${APPROVAL_USD:.2f}). Show this estimate to the user; "
                f"only after they approve, re-run with LIVE_LLM_APPROVAL={est.code}"
                + (f" (got {given!r}, which is for a different estimate)" if given else "")
            )
        self.log(f"[spend-guard] approved by code {est.code}")
        self.approved = True

    # ── 3. preflight ─────────────────────────────────────────────────────
    def preflight(self) -> None:
        self.log("[spend-guard] note: the remaining credit balance can't be read via the API "
                 "(no balance endpoint); check the Console. Probing that the account can be billed...")
        try:
            self.client.messages.create(model=self.model, max_tokens=1,
                                        messages=[{"role": "user", "content": "ok"}])
        except Exception as e:
            if is_billing_error(e):
                raise BillingUnavailable(f"account cannot be billed right now: {e}") from e
            raise
        self.preflighted = True

    # ── 4. run ───────────────────────────────────────────────────────────
    def run(self, requests: List[Dict[str, Any]], out_path: str, workers: int = 4) -> BatchResult:
        if not (self.approved and self.preflighted and self.estimate_):
            raise SpendNotApproved("run() needs estimate(), approve() and preflight() first")
        if len(requests) != self.estimate_.calls:
            raise SpendNotApproved(f"batch has {len(requests)} requests but {self.estimate_.calls} were approved")
        pin, pout = PRICES[self.model]
        # Approved batch: 1.5x its approved estimate. Under-threshold batch: the
        # threshold itself, so it can never quietly become an unapproved big spend.
        cap = self.estimate_.usd * OVERRUN_FACTOR if self.estimate_.needs_approval else APPROVAL_USD
        res, lock, stop = BatchResult(), threading.Lock(), threading.Event()

        def record(kind: str, entry: Dict[str, Any]) -> None:
            with lock:
                getattr(res, kind).append(entry)
                with open(out_path, "a") as f:
                    f.write(json.dumps({"status": kind, **entry}) + "\n")

        def one(idx: int) -> None:
            r = requests[idx]
            meta = {"idx": idx, **(r.get("meta") or {})}
            if stop.is_set():
                record("skipped", meta)
                return
            kw = {"model": self.model, "max_tokens": r["max_tokens"], "messages": r["messages"]}
            if r.get("system"):
                kw["system"] = r["system"]
            try:
                msg = self.client.messages.create(**kw)
            except Exception as e:
                record("failed", {**meta, "error": str(e)[:300]})
                if is_billing_error(e):
                    with lock:
                        res.stop_reason = res.stop_reason or f"billing error: {str(e)[:200]}"
                    stop.set()
                return
            cost = msg.usage.input_tokens * pin / 1e6 + msg.usage.output_tokens * pout / 1e6
            text = "".join(getattr(b, "text", "") for b in msg.content)
            record("ok", {**meta, "text": text, "input_tokens": msg.usage.input_tokens,
                          "output_tokens": msg.usage.output_tokens})
            with lock:
                res.actual_usd += cost
                if res.actual_usd > cap and not stop.is_set():
                    res.stop_reason = (f"actual spend ${res.actual_usd:.2f} passed the ${cap:.2f} cap "
                                       f"(estimate ${self.estimate_.usd:.2f})")
                    stop.set()

        started = time.time()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(one, range(len(requests))))
        self.approved = self.preflighted = False  # one approval per batch
        self.log(f"[spend-guard] {self.label}: {len(res.ok)} ok, {len(res.failed)} failed, "
                 f"{len(res.skipped)} skipped, ${res.actual_usd:.2f} actual, {time.time() - started:.0f}s; "
                 f"results in {out_path}")
        if res.stop_reason:
            self.log(f"[spend-guard] !!! STOPPED EARLY: {res.stop_reason}")
        return res
