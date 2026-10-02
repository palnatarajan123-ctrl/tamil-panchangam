#!/usr/bin/env python3
"""
Targeted rewrite of cached "transit backing" sentences (2026-10-02).

Before 2026-10-02 the monthly/yearly LLM was given BAV scores for each
planet's NATAL sign as if they were transit scores, so many cached reports'
why_this_period.bav_qualifier (and occasionally a life_areas[*].astrological_basis)
claims a Saturn/Jupiter transit is well/weakly supported when the corrected
value (bhinnashtakavarga_engine.bav_transit_strength, 4-bindu threshold)
says the opposite.

This rewrites ONLY those sentences, with a small LLM call per report, and
leaves everything else untouched. Each report has two stored copies -- the
latest prediction_llm_interpretation.content_json (PDF, yearly view) and
{monthly,yearly}_predictions.interpretation.llm_interpretation (monthly web
view) -- and both are updated.

A sentence "contradicts" when it calls a transit well-supported/strong at
<4/8, weak/friction-bound at >=4/8, or "moderate" at <=2/8. The classifier is
keyword-based; review the dry-run list by eye before --apply.

Usage (dry run lists targets; --apply rewrites, after backing up):
    cd tamil_panchangam_engine
    python ../scripts/rewrite_transit_backing_sentences.py [--apply]
"""

import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tamil_panchangam_engine", ".env"))

from app.db.postgres import get_conn
from app.engines.bhinnashtakavarga_engine import (
    bav_for_payload, bav_transit_strength, format_bav_transit_line, gochara_transit_longitudes,
)

MODEL = "claude-sonnet-4-6"
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backfill_backups")

# ── Classifier ────────────────────────────────────────────────────────────────

_STRONG = (r"well[- ]?(backed|supported)|good classical|strong(ly)? (classical )?(backing|backed|support)"
           r"|strongly backed|classically (strong|supported|backed|robust)|exceptionally")
_WEAK = r"\bweak(ly)?\b|\bfriction\b|thin classical|limited classical|little classical|poorly"
_MOD = r"\bmoderate|\bmixed\b|\bpartial\b"
_SPLIT = r";|\.\s|—| – |\bwhile\b|\bbut\b|\bby contrast\b|\bthough\b"
_BASIS = (r"(strong|moderate|weak|good|solid|thin|limited) classical (backing|support)"
          r"|classically (well[- ]?)?(backed|supported|strong)|well[- ]backed")


def _claim(segment: str):
    s = segment.lower().replace("friction-free", "")
    if re.search(_STRONG, s):
        return "strong"
    if re.search(_WEAK, s):
        return "weak"
    if re.search(_MOD, s):
        return "moderate"
    return None


def planet_claims(sentence: str) -> dict:
    """{"jupiter": "strong"|"weak"|"moderate", "saturn": ...} for the planets
    the sentence makes a backing claim about. Clauses split on ; . — while
    but though, so one planet's words don't leak into the other's."""
    out = {}
    segs = [x for x in re.split(_SPLIT, sentence or "", flags=re.I) if x.strip()]
    if re.search(r"\bboth (saturn|jupiter)('s)? and (saturn|jupiter)", sentence or "", re.I) and segs:
        c = _claim(segs[0])
        if c:
            out = {"saturn": c, "jupiter": c}
    for planet in ("jupiter", "saturn"):
        if planet in out:
            continue
        for i, seg in enumerate(segs):
            if re.search(planet, seg, re.I):
                c = _claim(seg)
                if not c and i + 1 < len(segs) and not re.search("jupiter|saturn", segs[i + 1], re.I):
                    c = _claim(segs[i + 1])
                if c:
                    out[planet] = c
                break
    return out


def contradicts(claim: str, bindus: int) -> bool:
    return (claim == "strong" and bindus < 4) or (claim == "weak" and bindus >= 4) or (claim == "moderate" and bindus <= 2)


def find_problems(text: str, truth: dict, basis: bool = False) -> dict:
    """{planet: (claim, bindus)} for every contradicting claim in `text`."""
    if basis:
        found = {}
        for planet in ("jupiter", "saturn"):
            m = (re.search(r"[^.]*" + planet + r"[^.]*(" + _BASIS + r")[^.]*", text or "", re.I)
                 or re.search(r"[^.]*(" + _BASIS + r")[^.]*" + planet + r"[^.]*", text or "", re.I))
            c = _claim(m.group(0)) if m else None
            if c and planet in truth and contradicts(c, truth[planet]["bindus"]):
                found[planet] = (c, truth[planet]["bindus"])
        return found
    return {p: (c, truth[p]["bindus"]) for p, c in planet_claims(text).items()
            if p in truth and contradicts(c, truth[p]["bindus"])}


# ── Targets ───────────────────────────────────────────────────────────────────

def _j(x):
    return x if isinstance(x, dict) else json.loads(x or "{}")


def load_targets():
    with get_conn() as conn:
        payloads = {str(r[0]): _j(r[1]) for r in conn.execute("SELECT id, payload FROM base_charts").fetchall()}
        rows = [("monthly",) + tuple(r) for r in conn.execute(
            "SELECT base_chart_id, year, month, envelope, interpretation FROM monthly_predictions").fetchall()]
        rows += [("yearly",) + tuple(r) for r in conn.execute(
            "SELECT base_chart_id, year, NULL::int AS m, envelope, interpretation FROM yearly_predictions").fetchall()]
    targets = []
    for kind, chart_id, year, month, env, interp in rows:
        li = _j(interp).get("llm_interpretation") or {}
        sentence = (li.get("why_this_period") or {}).get("bav_qualifier")
        if not sentence or str(chart_id) not in payloads:
            continue
        truth = bav_transit_strength(bav_for_payload(payloads[str(chart_id)]),
                                     gochara_transit_longitudes(_j(env).get("gochara", {})))
        fields = {}
        if find_problems(sentence, truth):
            fields["why_this_period.bav_qualifier"] = sentence
        for area, v in (li.get("life_areas") or {}).items():
            b = (v or {}).get("astrological_basis") or ""
            if find_problems(b, truth, basis=True):
                fields[f"life_areas.{area}.astrological_basis"] = b
        if fields:
            targets.append({
                "chart_id": str(chart_id), "kind": kind, "year": year, "month": month,
                "period_key": f"{year}-{month:02d}" if kind == "monthly" else str(year),
                "truth": truth, "fields": fields,
                "context": (li.get("why_this_period") or {}).get("transit_plain") or "",
            })
    return targets


# ── Rewrite ───────────────────────────────────────────────────────────────────

SYSTEM = (
    "You correct sentences in an existing astrology report. Rewrite ONLY the sentences given, so that every claim "
    "about how classically supported a Saturn or Jupiter transit is matches the corrected values: 4/8 or more is "
    "above the classical threshold (say it is well-supported / has solid classical backing); below 4 is weakly "
    "supported (expect more friction than usual); 0-2 is clearly weak, never 'moderate'. Keep each sentence's "
    "length, tone, life-area meaning and every other claim. Plain English: never say 'Ashtakavarga', 'bindus' or "
    "numbers out of 8. Return ONLY JSON mapping each given key to its rewritten sentence."
)


def rewrite(client, target, feedback: str = ""):
    user = json.dumps({
        "corrected_transit_strength": [format_bav_transit_line(e) for e in target["truth"].values()],
        "period": f"{target['kind']} {target['period_key']}",
        "nearby_context_do_not_rewrite": target["context"],
        "sentences_to_rewrite": target["fields"],
        **({"previous_attempt_problem": feedback} if feedback else {}),
    }, ensure_ascii=False)
    resp = client.messages.create(model=MODEL, max_tokens=600, system=SYSTEM,
                                  messages=[{"role": "user", "content": user}])
    text = resp.content[0].text.strip()
    text = re.sub(r"^```(json)?|```$", "", text).strip()
    return json.loads(text), resp.usage.input_tokens, resp.usage.output_tokens


def _set_path(doc: dict, path: str, value: str) -> None:
    keys = path.split(".")
    node = doc
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value


def _get_path(doc: dict, path: str):
    node = doc
    for k in path.split("."):
        node = (node or {}).get(k)
    return node


def apply(targets):
    import anthropic
    client = anthropic.Anthropic()
    backup, totals, second_pass, failed = [], [0, 0], [], []

    for t in targets:
        result, feedback = None, ""
        for attempt in (1, 2):
            out, i_tok, o_tok = rewrite(client, t, feedback)
            totals[0] += i_tok
            totals[1] += o_tok
            _log_tokens(t, i_tok, o_tok)
            missing = [k for k in t["fields"] if not isinstance(out.get(k), str) or not out[k].strip()]
            still = {k: find_problems(out.get(k, ""), t["truth"], basis=not k.endswith("bav_qualifier"))
                     for k in t["fields"] if k not in missing}
            still = {k: v for k, v in still.items() if v}
            if not missing and not still:
                result = out
                if attempt == 2:
                    second_pass.append(t)
                break
            feedback = f"missing keys {missing}; still contradicting {still}"
        if result is None:
            failed.append((t, feedback))
            print(f"FAILED {t['chart_id'][:8]} {t['period_key']}: {feedback}")
            continue
        _write(t, result, backup)
        print(f"ok {t['chart_id'][:8]} {t['kind']} {t['period_key']}")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, f"transit_backing_rewrite_{uuid.uuid4().hex[:8]}.json")
    with open(path, "w") as f:
        json.dump(backup, f, ensure_ascii=False, indent=1)
    cost = totals[0] * 3 / 1e6 + totals[1] * 15 / 1e6
    print(f"\nrewritten {len(targets) - len(failed)}/{len(targets)}; second pass needed: "
          f"{[(t['chart_id'][:8], t['period_key']) for t in second_pass]}; failed: {len(failed)}")
    print(f"tokens in {totals[0]} out {totals[1]} total {sum(totals)} (~${cost:.2f}); backup {path}")


def _log_tokens(t, i_tok, o_tok):
    from app.engines.budget_guard import log_llm_call
    with get_conn() as conn:
        # log_llm_call() writes both the $ ledger and the token ledger.
        log_llm_call(conn, t["chart_id"], "transit_backing_rewrite", f"{t['kind']}/{t['period_key']}", i_tok, o_tok,
                     prompt_version="rewrite_v1")


def _write(t, new_text: dict, backup: list):
    """Update both stored copies; record the old values for rollback."""
    with get_conn() as conn:
        llm_row = conn.execute(
            "SELECT id, content_json FROM prediction_llm_interpretation WHERE base_chart_id = %s AND period_type = %s "
            "AND period_key = %s AND feature_name = 'prediction' ORDER BY created_at DESC LIMIT 1",
            (t["chart_id"], t["kind"], t["period_key"]),
        ).fetchone()
        table = f"{t['kind']}_predictions"
        where = "base_chart_id = %s AND year = %s" + (" AND month = %s" if t["kind"] == "monthly" else "")
        args = (t["chart_id"], t["year"]) + ((t["month"],) if t["kind"] == "monthly" else ())
        pred_row = conn.execute(f"SELECT interpretation FROM {table} WHERE {where}", args).fetchone()

        content = _j(llm_row[1]) if llm_row else None
        interp = _j(pred_row[0])
        entry = {"target": {k: t[k] for k in ("chart_id", "kind", "period_key")}, "old": {}, "new": new_text}
        for path, new in new_text.items():
            if path not in t["fields"]:
                continue
            entry["old"][path] = {"merged": _get_path(interp["llm_interpretation"], path),
                                  "llm_row": _get_path(content, path) if content else None}
            _set_path(interp["llm_interpretation"], path, new)
            if content and _get_path(content, path) is not None:
                _set_path(content, path, new)
        conn.execute(f"UPDATE {table} SET interpretation = %s::jsonb WHERE {where}", (json.dumps(interp),) + args)
        if content:
            conn.execute("UPDATE prediction_llm_interpretation SET content_json = %s::jsonb WHERE id = %s",
                         (json.dumps(content), llm_row[0]))
        backup.append(entry)


def main():
    targets = load_targets()
    for t in targets:
        truth = "; ".join(format_bav_transit_line(e) for e in t["truth"].values())
        print(f"{t['chart_id'][:8]} {t['kind']:7s} {t['period_key']:7s} | {truth}")
        for k, v in t["fields"].items():
            print(f"    {k}: {v}")
    n_fields = sum(len(t["fields"]) for t in targets)
    print(f"\n{len(targets)} reports, {n_fields} sentences contradict the corrected value")
    if "--apply" not in sys.argv:
        print("dry run -- review by eye, then pass --apply")
        return
    apply(targets)


if __name__ == "__main__":
    main()
