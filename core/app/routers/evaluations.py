from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..utils.db import get_evaluation_by_id

router = APIRouter(prefix="/v1/evaluations", tags=["evaluations"])

@router.get("/{evaluation_id}")
def get_evaluation(evaluation_id: int):
    obj = get_evaluation_by_id(evaluation_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return obj
