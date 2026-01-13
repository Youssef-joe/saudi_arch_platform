from __future__ import annotations

import datetime
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body

from ..engines.kb import load_kb, kb_by_pattern
from ..engines.g2c import evaluate as g2c_evaluate
from ..engines.smr import predict_style
from .vision import analyze as vision_analyze
from ..utils.db import insert_evaluation

router = APIRouter(prefix="/v1/flow", tags=["flow"])

KB_PATH = Path(__file__).resolve().parents[1] / "data" / "saudi_arch_kb.json"
KB = load_kb(KB_PATH)
KB_MAP = kb_by_pattern(KB)


@router.post("/assess")
def assess(payload: Dict[str, Any] = Body(...)):
    """One-shot flow: attach (image/DXF/IFC) -> analyze -> evaluate -> save."""
    project = payload.get("project") or {}
    pattern_code: Optional[str] = payload.get("pattern_code")

    # 1) analyze
    analyze_payload: Dict[str, Any] = {}
    for k in ["image_base64", "dxf_base64", "ifc_base64", "style_candidates"]:
        if payload.get(k) is not None:
            analyze_payload[k] = payload.get(k)

    analyzed = vision_analyze(analyze_payload)  # same-process call
    if "error" in analyzed:
        return analyzed
    features = analyzed.get("features") or {}

    # 2) choose pattern
    if not pattern_code:
        style = predict_style(features, candidates=payload.get("style_candidates"))
        pattern_code = style.get("pattern_code")
    pattern = KB_MAP.get(pattern_code or "") or KB_MAP.get("najdi_central") or {}

    # 3) evaluate
    evaluation = g2c_evaluate(project, features, pattern)

    # 4) persist
    token = uuid.uuid4().hex
    created_at = datetime.datetime.utcnow().isoformat() + "Z"
    evaluation_id = insert_evaluation(
        token=token,
        created_at=created_at,
        project=project,
        pattern_code=pattern_code,
        features=features,
        evaluation=evaluation,
    )

    base = "/v1"
    return {
        "mode": analyzed.get("mode"),
        "evaluation_id": evaluation_id,
        "certificate_token": token,
        "created_at": created_at,
        "urls": {
            "evaluation": f"{base}/evaluations/{evaluation_id}",
            "verify": f"{base}/cert/verify/{token}",
            "report_pdf": f"{base}/report/evaluation/{evaluation_id}.pdf",
        },
        "project": project,
        "pattern_code": pattern_code,
        "features": features,
        "evaluation": evaluation,
    }
