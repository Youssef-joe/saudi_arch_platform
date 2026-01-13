from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: str  # pass|warn|fail
    score: float
    evidence: Dict[str, Any]
    reasoning: str
    recommendation: str
    weight: float


def parse_range_from_hint(hint: str) -> Tuple[Optional[float], Optional[float]]:
    """Parse a (min,max) numeric range from a hint string.

    This is heuristic and meant to be replaced by official guideline numeric constraints when available.
    """
    if not hint:
        return (None, None)

    h = str(hint)
    # Common Arabic cues
    if any(x in h for x in ["منخفض", "محدود", "صغيرة"]):
        return (10.0, 22.0)
    if any(x in h for x in ["متوسط", "معتدل"]):
        return (18.0, 35.0)
    if any(x in h for x in ["مرتفع", "واسعة", "كبيرة"]):
        return (28.0, 50.0)
    return (18.0, 35.0)
