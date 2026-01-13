from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pathlib import Path
import yaml

from .g2c_types import CheckResult, parse_range_from_hint


@dataclass
class Rule:
    rule_id: str
    title: str
    weight: float
    rule_type: str
    params: Dict[str, Any]
    refs: List[Dict[str, Any]]


def load_rules(path: Path) -> List[Rule]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return []
    rules: List[Rule] = []
    for r in (data.get("rules") or []):
        rules.append(
            Rule(
                rule_id=r.get("id") or "unknown",
                title=r.get("title") or r.get("title_ar") or r.get("id") or "Rule",
                weight=float(r.get("weight") or 0.1),
                rule_type=r.get("type") or "between",
                params=r.get("params") or {},
                refs=r.get("refs") or [],
            )
        )
    return rules


def _get_path(obj: Any, path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _palette_overlap(palette_hex: List[str], target_hex: List[str]) -> float:
    if not palette_hex or not target_hex:
        return 0.0
    p = {str(h).lower() for h in palette_hex}
    t = {str(h).lower() for h in target_hex}
    return len(p.intersection(t)) / max(1, len(t))


def eval_rules(project: Dict[str, Any], features: Dict[str, Any], pattern: Dict[str, Any], rules: List[Rule]) -> List[CheckResult]:
    checks: List[CheckResult] = []
    ctx = {"project": project, "features": features, "pattern": pattern}

    for r in rules:
        t = r.rule_type
        p = r.params

        status = "pass"
        score = 1.0
        evidence: Dict[str, Any] = {}
        reasoning = ""
        recommendation = ""

        if t == "hint_between":
            value = _get_path(features, p.get("feature") or "") if (p.get("feature","").startswith("project.") is False) else _get_path(project, p.get("feature").split("project.",1)[1])
            hint = _get_path(pattern, p.get("hint") or "")
            mn, mx = parse_range_from_hint(str(hint or ""))
            evidence = {"value": value, "range": {"min": mn, "max": mx}, "hint": hint}
            if value is None:
                status = "warn"
                score = 0.5
                reasoning = p.get("reason_missing") or "Missing required input."
                recommendation = p.get("recommend_missing") or "Provide required input for this check."
            else:
                if mn is not None and mx is not None and not (mn <= float(value) <= mx):
                    status = p.get("fail_status") or "fail"
                    score = 0.0
                    reasoning = p.get("reason_fail") or "Value is outside the suggested range."
                    recommendation = p.get("recommend_fail") or "Adjust to meet the guideline range."
                else:
                    reasoning = p.get("reason_pass") or "Within the suggested range."

        elif t == "max":
            feat = p.get("feature") or ""
            value = _get_path(features, feat) if not str(feat).startswith("project.") else _get_path(project, str(feat).split("project.", 1)[1])
            mx = p.get("max")
            evidence = {"value": value, "max": mx}
            if value is None or mx is None:
                status = "warn"
                score = 0.5
                reasoning = p.get("reason_missing") or "Missing required input."
                recommendation = p.get("recommend_missing") or "Provide required input for this check."
            else:
                if float(value) > float(mx):
                    status = p.get("fail_status") or "fail"
                    score = 0.0
                    reasoning = p.get("reason_fail") or "Exceeds maximum."
                    recommendation = p.get("recommend_fail") or "Reduce to meet the limit."
                else:
                    reasoning = p.get("reason_pass") or "Below the maximum."

        elif t == "contains_any":
            elements = _get_path(features, p.get("feature") or "") or {}
            keys = p.get("keys_any") or []
            found = sum(1 for k in keys if isinstance(elements, dict) and (elements.get(k, 0) or 0) > 0)
            min_total = int(p.get("min_total") or 1)
            evidence = {"found": found, "min_total": min_total, "keys_any": keys}
            if found < min_total:
                status = p.get("fail_status") or "warn"
                score = 0.25
                reasoning = p.get("reason_fail") or "Identity elements not detected."
                recommendation = p.get("recommend_fail") or "Add identity elements where appropriate."
            else:
                reasoning = p.get("reason_pass") or "Identity elements detected."

        elif t == "palette_overlap":
            palette = _get_path(features, p.get("feature") or "") or []
            target = _get_path(pattern, p.get("target") or "") or []
            ratio = _palette_overlap(palette, target)
            min_ratio = float(p.get("min_ratio") or 0.25)
            evidence = {"overlap_ratio": ratio, "min_ratio": min_ratio}
            if ratio < min_ratio:
                status = p.get("fail_status") or "warn"
                score = 0.3
                reasoning = p.get("reason_fail") or "Palette not aligned."
                recommendation = p.get("recommend_fail") or "Align palette with pattern."
            else:
                reasoning = p.get("reason_pass") or "Palette aligned."

        else:
            status = "warn"
            score = 0.5
            reasoning = f"Unknown rule type: {t}"
            recommendation = "Fix rule definitions."

        # Attach guideline references if provided in the rule definition.
        if r.refs:
            evidence = dict(evidence)
            evidence["guideline_refs"] = r.refs

        checks.append(
            CheckResult(
                check_id=r.rule_id,
                title=r.title,
                status=status,
                score=float(score),
                evidence=evidence,
                reasoning=reasoning,
                recommendation=recommendation,
                weight=float(r.weight),
            )
        )

    return checks
