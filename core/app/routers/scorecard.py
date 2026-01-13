from __future__ import annotations

import datetime
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body

from ..engines.kb import load_kb, kb_by_pattern
from ..engines.smr import predict_style
from ..engines.g2c import evaluate
from ..utils.db import insert_evaluation

router = APIRouter(prefix="/v1/scorecard", tags=["scorecard"])

KB_PATH = Path(__file__).resolve().parents[1] / "data" / "saudi_arch_kb.json"
KB = load_kb(KB_PATH)
KB_MAP = kb_by_pattern(KB)


@router.post("/evaluate")
def evaluate_scorecard(payload: Dict[str, Any] = Body(...), save: bool = False):
    """Explainable scorecard evaluation (G2C v0) + optional persistence.

    Expected payload:
    {
      "project": {"name":..., "city":..., "height_m": ...},
      "features": { ... from /v1/vision/analyze ... },
      "pattern_code": "najdi_central" (optional)
    }

    Query param:
      save=true -> persist evaluation and return evaluation_id + certificate_token
    """

    project = payload.get("project") or {}
    features = payload.get("features") or {}
    pattern_code: Optional[str] = payload.get("pattern_code")

    # 1) determine pattern
    if not pattern_code:
        style = predict_style(features, candidates=payload.get("style_candidates"))
        pattern_code = style.get("pattern_code")

    pattern = KB_MAP.get(pattern_code or "") or KB_MAP.get("najdi_central") or {}
    if not pattern:
        pattern = KB.get("entries", [])[0] if KB.get("entries") else {"pattern_code": "unknown", "name_ar": "غير معروف"}

    # 2) evaluate
    g2c = evaluate(project, features, pattern)

    resp: Dict[str, Any] = {
        "status": "evaluated",
        "project": project,
        "features": features,
        "pattern_code": pattern.get("pattern_code"),
        "evaluation": g2c,
    }

    if save:
        token = uuid.uuid4().hex
        created_at = datetime.datetime.utcnow().isoformat() + "Z"
        evaluation_id = insert_evaluation(
            token=token,
            created_at=created_at,
            project=project,
            pattern_code=pattern.get("pattern_code"),
            features=features,
            evaluation=g2c,
        )
        resp["evaluation_id"] = evaluation_id
        resp["certificate_token"] = token
        resp["created_at"] = created_at
        resp["urls"] = {
            "evaluation": f"/v1/evaluations/{evaluation_id}",
            "verify": f"/v1/cert/verify/{token}",
            "report_pdf": f"/v1/report/evaluation/{evaluation_id}.pdf",
        }

    return resp
