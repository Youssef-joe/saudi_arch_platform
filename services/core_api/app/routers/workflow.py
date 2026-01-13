from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from ..deps import current_user
from ..audit import log

router = APIRouter()

ALLOWED = {
  "DRAFT": {"SUBMIT":"SUBMITTED"},
  "SUBMITTED": {"START_REVIEW":"UNDER_REVIEW"},
  "UNDER_REVIEW": {"REQUEST_CLARIFICATION":"CLARIFICATION","APPROVE":"APPROVED","REJECT":"REJECTED"},
  "CLARIFICATION": {"RESUBMIT":"SUBMITTED"}
}

@router.post("/transition")
def transition(payload: dict, db: Session = Depends(get_db), user=Depends(current_user)):
    project_id = payload.get("project_id")
    action = payload.get("action")
    p = db.get(models.Project, project_id)
    if not p: raise HTTPException(404,"project not found")
    nxt = ALLOWED.get(p.status, {}).get(action)
    if not nxt: raise HTTPException(400, f"invalid transition from {p.status} via {action}")
    p.status = nxt
    db.commit()
    log(db, user["sub"], "workflow.transition", "project", project_id, {"from": p.status, "to": nxt, "action": action})
    return {"status": p.status}
