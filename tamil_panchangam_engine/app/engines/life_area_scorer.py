# app/engines/life_area_scorer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.engines.life_area_config import LIFE_AREA_WEIGHTS, LIFE_AREAS

print("DEBUG: LifeAreaScorer module LOADED")  # 🔴 proves correct file is running


@dataclass(frozen=True)
class LifeAreaSignalContribution:
    key: str
    contrib: float
    weight_breakdown: Dict[str, Any]
    strength: float
    confidence: float
    rationale: str
    interpretive_hint: str = ""


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


class LifeAreaScorer:
    """
    Deterministic scoring over existing synthesized signals.
    """

    def __init__(self, weights: Optional[Dict[str, Any]] = None):
        self.weights = weights or LIFE_AREA_WEIGHTS
        print("DEBUG: LifeAreaScorer __init__ called")

    def score_all(
        self,
        base_score_0_100: float,
        base_confidence_0_1: float,
        signals: List[Dict[str, Any]],
        top_k: int = 6,
    ) -> Dict[str, Any]:
        print("DEBUG: score_all called, signals count =", len(signals))

        out: Dict[str, Any] = {}
        for area in LIFE_AREAS:
            out[area] = self.score_one(
                area=area,
                base_score_0_100=base_score_0_100,
                base_confidence_0_1=base_confidence_0_1,
                signals=signals,
                top_k=top_k,
            )
        return out

    def score_one(
        self,
        area: str,
        base_score_0_100: float,
        base_confidence_0_1: float,
        signals: List[Dict[str, Any]],
        top_k: int = 6,
    ) -> Dict[str, Any]:
        cfg = self.weights[area]

        raw_sum = 0.0
        raw_abs = 0.0
        contributions: List[LifeAreaSignalContribution] = []

        print(f"\nDEBUG: Scoring area = {area}")
        for s in signals:
            print(
                "DEBUG: Signal:",
                s.get("key"),
                "house=", s.get("house"),
                "planet=", s.get("planet"),
                "source=", s.get("source"),
            )

            strength = _clamp(_safe_float(s.get("strength"), 0.0), 0.0, 1.0)
            conf = _clamp(_safe_float(s.get("confidence"), 0.5), 0.0, 1.0)

            valence = (s.get("valence") or "mix").lower()
            if valence not in ("pos", "neg", "mix"):
                valence = "mix"

            house = s.get("house")
            planet = s.get("planet")
            source = (s.get("source") or "derived").lower()

            house_w = cfg["houses"].get(house, 0.0) if isinstance(house, int) else 0.0
            ben_w = cfg["benefics"].get(planet, 0.0) if isinstance(planet, str) else 0.0
            mal_w = cfg["malefics"].get(planet, 0.0) if isinstance(planet, str) else 0.0
            planet_w = ben_w + mal_w

            # Some signals (yogas, Tara Bala, Ashtakavarga validation,
            # Chandra Gati rhythm, Navamsa dignity, aspect-balance
            # summaries, event-window confluence, some divisional-chart
            # refinements) are structurally chart-wide: they carry
            # NEITHER a house NOR a planet, so house_w/planet_w are both
            # always 0.0 for them regardless of the signal's own
            # "strength" -- previously this silently excluded every such
            # signal from top_signals/scoring no matter how significant.
            # Distinguish this from a signal that DOES have a house/
            # planet but legitimately scores 0 for THIS specific area
            # (e.g. a Sun-related signal in an area that doesn't weight
            # Sun) -- that case must stay untouched, it's a real "not
            # relevant here", not a structural gap.
            has_house_or_planet = isinstance(house, int) or isinstance(planet, str)

            # signal_key_weights: exact-key overrides for structurally
            # house/planet-less signals whose classical relevance
            # genuinely differs by area (e.g. a wealth yoga matters far
            # more to "finance" than to "health"). Declared per area in
            # life_area_config.py, same declarative home as every other
            # weight here.
            key_w = cfg.get("signal_key_weights", {}).get(s.get("key"), 0.0)

            # signal_source_weights: a per-source fallback base weight,
            # used ONLY when a signal has no house/planet AND no
            # exact-key override -- covers dynamically-suffixed keys
            # (e.g. "TARA_BALA_SAMPAT", "ASHTAKAVARGA_STRONG_SUPPORT")
            # without having to enumerate every possible suffix.
            if not has_house_or_planet and key_w == 0.0:
                key_w = cfg.get("signal_source_weights", {}).get(source, 0.0)

            src_bias = cfg["source_bias"].get(source, 0.95)
            val_mult = cfg["valence_multiplier"][valence]

            raw = (house_w + planet_w + key_w) * strength * src_bias * val_mult

            print(
                f"DEBUG: weights → house_w={house_w}, planet_w={planet_w}, "
                f"key_w={key_w}, src_bias={src_bias}, val_mult={val_mult}, raw={raw}"
            )

            cap = cfg.get("max_abs_contrib_per_signal", 1.5)
            raw = _clamp(raw, -cap, cap)

            if abs(raw) > 0:
                raw_sum += raw
                raw_abs += abs(raw)

                contributions.append(
                    LifeAreaSignalContribution(
                        key=s.get("key", "UNKNOWN"),
                        contrib=raw,
                        weight_breakdown={
                            "house_w": house_w,
                            "planet_w": planet_w,
                            "key_w": key_w,
                            "src_bias": src_bias,
                            "valence": valence,
                        },
                        strength=strength,
                        confidence=conf,
                        rationale=str(s.get("rationale") or ""),
                        interpretive_hint=str(s.get("interpretive_hint") or ""),
                    )
                )

        print(f"DEBUG: {area} raw_sum={raw_sum}, raw_abs={raw_abs}")

        evidence = _clamp(raw_abs / 6.0, 0.0, 1.0)
        delta = _clamp(raw_sum, -1.0, 1.0) * 18.0 * evidence
        score = _clamp(base_score_0_100 + delta, 0.0, 100.0)

        confidence = _clamp(
            (0.65 * base_confidence_0_1) + (0.20 * evidence) + 0.15,
            0.0,
            1.0,
        )

        # Sort by |contrib| before truncating -- previously took the
        # first top_k signals in iteration/insertion order, which could
        # hide a genuinely significant contributor (e.g. a strong yoga)
        # behind several weaker ones simply because it was appended
        # later in the signal-generation sequence. "top_signals" should
        # mean the biggest contributors, not the first ones encountered.
        ranked_contributions = sorted(contributions, key=lambda c: abs(c.contrib), reverse=True)

        return {
            "score": int(round(score)),
            "confidence": round(confidence, 3),
            "evidence": round(evidence, 3),
            "delta": round(delta, 2),
            "top_signals": [
                {
                    "key": c.key,
                    "contrib": round(c.contrib, 3),
                    "weights": c.weight_breakdown,
                    "rationale": c.rationale,
                    "interpretive_hint": c.interpretive_hint,
                }
                for c in ranked_contributions[:top_k]
            ],
        }
