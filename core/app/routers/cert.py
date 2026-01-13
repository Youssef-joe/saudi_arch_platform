from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..utils.db import get_evaluation_by_token

router = APIRouter(prefix="/v1/cert", tags=["certificate"])

@router.get("/verify/{token}")
def verify(token: str):
    obj = get_evaluation_by_token(token)
    if not obj:
        raise HTTPException(status_code=404, detail="Certificate not found")

    # return a compact, verifiable payload (no raw features unless needed)
    ev = obj.get("evaluation", {})
    return {
        "ok": True,
        "certificate": {
            "token": obj["token"],
            "evaluation_id": obj["id"],
            "created_at": obj["created_at"],
        },
        "project": obj.get("project", {}),
        "pattern_code": obj.get("pattern_code"),
        "summary": {
            "overall_score": ev.get("overall_score"),
            "status": ev.get("status"),
            "checks_total": len(ev.get("checks", [])),
            "fails": sum(1 for c in ev.get("checks", []) if c.get("status") == "fail"),
            "warnings": sum(1 for c in ev.get("checks", []) if c.get("status") == "warn"),
        },
    }
