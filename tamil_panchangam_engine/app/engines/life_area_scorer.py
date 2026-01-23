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

            src_bias = cfg["source_bias"].get(source, 0.95)
            val_mult = cfg["valence_multiplier"][valence]

            raw = (house_w + planet_w) * strength * src_bias * val_mult

            print(
                f"DEBUG: weights → house_w={house_w}, planet_w={planet_w}, "
                f"src_bias={src_bias}, val_mult={val_mult}, raw={raw}"
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
                            "src_bias": src_bias,
                            "valence": valence,
                        },
                        strength=strength,
                        confidence=conf,
                        rationale=str(s.get("rationale") or ""),
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
                }
                for c in contributions[:top_k]
            ],
        }
