from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Body

from ..engines.feature_extract import analyze_image_features, wwr_from_dxf_b64, wwr_from_ifc_b64

router = APIRouter(prefix="/v1/vision", tags=["vision"])


@router.post("/analyze")
def analyze(payload: Dict[str, Any] = Body(...)):
    # DXF / IFC
    if payload.get("dxf_base64"):
        res = wwr_from_dxf_b64(payload["dxf_base64"])
        if "error" in res:
            return res
        return {"mode": "dxf", "features": {"wwr_pct": res.get("wwr_pct", 0.0)}, "wwr": res}

    if payload.get("ifc_base64"):
        res = wwr_from_ifc_b64(payload["ifc_base64"])
        if "error" in res:
            return res
        return {"mode": "ifc", "features": {"wwr_pct": res.get("wwr_pct", 0.0)}, "wwr": res}

    # Image
    if payload.get("image_base64"):
        feats = analyze_image_features(
            payload["image_base64"],
            style_candidates=payload.get("style_candidates"),
        )
        return {"mode": "image", "features": feats}

    return {"error": "Provide image_base64 or dxf_base64 or ifc_base64"}
