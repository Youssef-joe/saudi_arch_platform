from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


def _wwr_bucket(wwr: float) -> str:
    if wwr < 18:
        return "low"
    if wwr < 35:
        return "medium"
    return "high"


def _hint_to_bucket(hint: str) -> str:
    h = (hint or "").strip()
    # Arabic heuristics
    if any(x in h for x in ["منخفض", "محدود", "صغيرة"]):
        return "low"
    if any(x in h for x in ["متوسط", "معتدل"]):
        return "medium"
    if any(x in h for x in ["مرتفع", "واسعة", "كبيرة"]):
        return "high"
    return "medium"


def predict_style(features: Dict[str, Any], kb_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Heuristic SMR v0: score styles by (WWR bucket match + palette presence + key element hints).

    This is NOT the final ML SMR, but it makes the pipeline real and debuggable.
    """

    wwr = float(features.get("wwr_pct") or 0.0)
    bucket = _wwr_bucket(wwr)

    # element signals (if any)
    elements = (features.get("vision") or {}).get("elements") or {}
    has_roshan = bool(elements.get("roshan") or elements.get("mashrabiya"))

    scores: List[Tuple[str, float]] = []
    for e in kb_entries:
        code = str(e.get("pattern_code"))
        hint = str(e.get("facade_opening_ratio_hint", ""))
        target_bucket = _hint_to_bucket(hint)

        s = 0.0
        if target_bucket == bucket:
            s += 1.0
        else:
            # partial
            if {target_bucket, bucket} == {"low", "medium"} or {target_bucket, bucket} == {"medium", "high"}:
                s += 0.5

        # Hijazi often roshan/mashrabiya; add small preference
        name_ar = str(e.get("name_ar", ""))
        if has_roshan and ("حجاز" in name_ar or "روشان" in name_ar):
            s += 0.5

        scores.append((code, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    top = scores[0][0] if scores else "najdi_central"
    return {
        "predicted_pattern_code": top,
        "signals": {"wwr_pct": wwr, "wwr_bucket": bucket, "has_roshan": has_roshan},
        "scores": [{"pattern_code": c, "score": float(v)} for c, v in scores[:8]],
    }
