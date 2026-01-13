from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import hashlib
import yaml

from .g2c_types import CheckResult
from .rule_dsl import load_rules, eval_rules


RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "g2c_rules.yaml"


def _ruleset_meta(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"file": path.name, "sha256": None, "ruleset": None}
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    try:
        data = yaml.safe_load(raw.decode("utf-8")) or {}
    except Exception:
        data = {}
    return {
        "file": path.name,
        "sha256": sha,
        "ruleset": data.get("ruleset"),
    }


def _overall_status(checks: List[CheckResult]) -> str:
    if any(c.status == "fail" for c in checks):
        return "fail"
    if any(c.status == "warn" for c in checks):
        return "warn"
    return "pass"


def _weighted_score(checks: List[CheckResult]) -> float:
    denom = sum(max(0.0, float(c.weight)) for c in checks) or 1.0
    numer = sum(max(0.0, float(c.weight)) * max(0.0, min(1.0, float(c.score))) for c in checks)
    return numer / denom


def evaluate(project: Dict[str, Any], features: Dict[str, Any], pattern: Dict[str, Any]) -> Dict[str, Any]:
    """G2C v0.2: Rule-DSL driven, explainable checks.

    - Loads rules from app/data/g2c_rules.yaml (editable without code changes)
    - Each rule emits a CheckResult with reasoning + recommendation
    """
    rules = load_rules(RULES_PATH)
    checks = eval_rules(project, features, pattern, rules)

    overall = _weighted_score(checks)
    overall_pct = round(overall * 100.0, 2)

    return {
        "pattern": {
            "pattern_code": pattern.get("pattern_code"),
            "name_ar": pattern.get("name_ar"),
            "name_en": pattern.get("name_en"),
        },
        "overall_score": overall_pct,
        "status": _overall_status(checks),
        "checks": [c.__dict__ for c in checks],
        "ruleset": _ruleset_meta(RULES_PATH),
        "notes": {
            "engine": "G2C v0.2 (Rule DSL over KB hints)",
            "rules_file": str(RULES_PATH.name),
            "disclaimer": "النسخة الحالية تعتمد على تلميحات قاعدة المعرفة (KB) وقواعد تشغيلية. للاعتماد الرسمي: اربطها بإصدارات الموجهات/الكود وتحقق هندسي أدق من IFC/DWG.",
        },
    }
