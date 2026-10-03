"""Tests for scripts/live_llm_guard.py. Fake client, no network.

Run: tamil_panchangam_engine/.venv/bin/python -m pytest scripts/tests -q
"""
import json
import os
import sys
import threading
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from live_llm_guard import BillingUnavailable, SpendGuard, SpendNotApproved  # noqa: E402

BILLING = ("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
           "'message': 'Your credit balance is too low to access the Anthropic API. Please go to "
           "Plans & Billing to upgrade or purchase credits.'}}")


class FakeClient:
    """count_tokens: 1 token per char of the last message. create(): obeys
    `fail_on` {call_index: exception}; after `billing_after` successful
    calls, every call raises the billing error."""

    def __init__(self, billing_after=None, fail_on=None, out_tokens=100):
        self.calls = 0
        self.billing_after = billing_after
        self.fail_on = fail_on or {}
        self.out_tokens = out_tokens
        self.lock = threading.Lock()
        self.messages = SimpleNamespace(count_tokens=self._count, create=self._create)

    def _count(self, **kw):
        return SimpleNamespace(input_tokens=len(kw["messages"][-1]["content"]))

    def _create(self, **kw):
        with self.lock:
            n = self.calls
            self.calls += 1
        if kw["max_tokens"] == 1:  # preflight probe
            if self.billing_after == 0:
                raise RuntimeError(BILLING)
            return SimpleNamespace(usage=SimpleNamespace(input_tokens=8, output_tokens=1), content=[])
        if n in self.fail_on:
            raise self.fail_on[n]
        if self.billing_after is not None and n > self.billing_after:
            raise RuntimeError(BILLING)
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=1000, output_tokens=self.out_tokens),
                               content=[SimpleNamespace(text=f"reply {n}")])


def reqs(n, chars=7500, max_tokens=1024):
    return [dict(messages=[{"role": "user", "content": "x" * chars}], max_tokens=max_tokens, meta={"i": i})
            for i in range(n)]


def guard(client, env=None):
    return SpendGuard("claude-sonnet-4-6", "test", client=client, env=env or {}, log=lambda s: None)


def test_tonights_batch_size_is_refused_without_approval():
    """A 120-call arm sweep like 2026-10-02's r16 run: stops before any call."""
    c = FakeClient()
    g = guard(c)
    est = g.estimate(reqs(120))
    assert est.calls == 120 and est.needs_approval
    assert round(est.usd, 2) == round(120 * (7500 * 3 + 1024 * 15) / 1e6, 2)
    with pytest.raises(SpendNotApproved, match="LIVE_LLM_APPROVAL=120:"):
        g.approve()
    with pytest.raises(SpendNotApproved):
        g.run(reqs(120), out_path=os.devnull)
    assert c.calls == 0


def test_approval_code_is_tied_to_the_estimate():
    c = FakeClient()
    est = guard(c).estimate(reqs(30))
    g = guard(c, env={"LIVE_LLM_APPROVAL": est.code})
    g.estimate(reqs(30)); g.approve()  # same estimate -> accepted
    g2 = guard(c, env={"LIVE_LLM_APPROVAL": est.code})
    g2.estimate(reqs(60))
    with pytest.raises(SpendNotApproved, match="different estimate"):
        g2.approve()


def test_cost_threshold_alone_triggers_approval():
    g = guard(FakeClient())
    est = g.estimate(reqs(10, chars=20000, max_tokens=2000))  # 10 calls, ~$0.90
    assert est.calls <= 20 and est.usd > 0.50 and est.needs_approval
    with pytest.raises(SpendNotApproved):
        g.approve()


def test_small_batch_runs_without_code(tmp_path):
    c = FakeClient()
    g = guard(c)
    g.estimate(reqs(3, chars=100, max_tokens=50)); g.approve(); g.preflight()
    res = g.run(reqs(3, chars=100, max_tokens=50), out_path=str(tmp_path / "o.jsonl"))
    assert len(res.ok) == 3 and not res.stop_reason


def test_preflight_refuses_when_account_cannot_be_billed():
    g = guard(FakeClient(billing_after=0))
    g.estimate(reqs(2, chars=10, max_tokens=10)); g.approve()
    with pytest.raises(BillingUnavailable):
        g.preflight()


def test_billing_error_stops_the_rest_and_keeps_finished_replies(tmp_path):
    c = FakeClient(billing_after=5)  # probe is call 0; calls 1..5 succeed
    batch = reqs(40)
    est = guard(c).estimate(batch)
    g = guard(c, env={"LIVE_LLM_APPROVAL": est.code})
    g.estimate(batch); g.approve(); g.preflight()
    out = tmp_path / "o.jsonl"
    res = g.run(batch, out_path=str(out), workers=1)
    assert len(res.ok) == 5 and len(res.failed) == 1 and len(res.skipped) == 34
    assert res.stop_reason.startswith("billing error")
    assert c.calls == 1 + 5 + 1  # probe + 5 ok + the one that hit the wall; nothing after
    lines = [json.loads(l) for l in out.read_text().splitlines()]
    assert sum(l["status"] == "ok" for l in lines) == 5 and all("text" in l for l in lines if l["status"] == "ok")


def test_one_ordinary_failure_does_not_abort_the_batch(tmp_path):
    c = FakeClient(fail_on={3: RuntimeError("Error code: 500 - overloaded")})
    batch = reqs(25)
    est = guard(c).estimate(batch)
    g = guard(c, env={"LIVE_LLM_APPROVAL": est.code})
    g.estimate(batch); g.approve(); g.preflight()
    res = g.run(batch, out_path=str(tmp_path / "o.jsonl"), workers=4)
    assert len(res.ok) == 24 and len(res.failed) == 1 and not res.skipped and not res.stop_reason


def test_overrun_past_the_approved_estimate_stops(tmp_path):
    c = FakeClient(out_tokens=50000)  # replies far longer than estimated
    batch = reqs(30, chars=100, max_tokens=50)
    est = guard(c).estimate(batch)
    g = guard(c, env={"LIVE_LLM_APPROVAL": est.code})
    g.estimate(batch); g.approve(); g.preflight()
    res = g.run(batch, out_path=str(tmp_path / "o.jsonl"), workers=1)
    assert res.stop_reason and "cap" in res.stop_reason and res.skipped


def test_approval_is_single_use_and_batch_size_must_match(tmp_path):
    c = FakeClient()
    g = guard(c)
    g.estimate(reqs(2, chars=10, max_tokens=10)); g.approve(); g.preflight()
    with pytest.raises(SpendNotApproved, match="were approved"):
        g.run(reqs(3, chars=10, max_tokens=10), out_path=str(tmp_path / "o.jsonl"))
    g.run(reqs(2, chars=10, max_tokens=10), out_path=str(tmp_path / "o.jsonl"))
    with pytest.raises(SpendNotApproved):
        g.run(reqs(2, chars=10, max_tokens=10), out_path=str(tmp_path / "o.jsonl"))


def test_under_threshold_batch_is_capped_at_the_threshold(tmp_path):
    c = FakeClient(out_tokens=20000)  # each reply ~$0.30, far over its tiny estimate
    g = guard(c)
    g.estimate(reqs(5, chars=10, max_tokens=10)); g.approve(); g.preflight()
    res = g.run(reqs(5, chars=10, max_tokens=10), out_path=str(tmp_path / "o.jsonl"), workers=1)
    assert len(res.ok) == 2 and len(res.skipped) == 3 and "$0.50 cap" in res.stop_reason


def test_unknown_model_refused():
    with pytest.raises(SpendNotApproved, match="no price"):
        SpendGuard("claude-mystery", "t", client=FakeClient(), env={}, log=lambda s: None)
