import uuid, requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from ..deps import current_user
from ..audit import log

router = APIRouter()

@router.post("/run")
def run_eval(payload: dict, db: Session = Depends(get_db), user=Depends(current_user)):
    project_version_id = payload.get("project_version_id")
    pv = db.get(models.ProjectVersion, project_version_id)
    if not pv: raise HTTPException(404,"project_version not found")
    ruleset_id = pv.ruleset_id or payload.get("ruleset_id")
    if not ruleset_id: raise HTTPException(400,"ruleset_id missing (attach to project version)")
    eid = str(uuid.uuid4())
    ev = models.Evaluation(id=eid, project_version_id=project_version_id, ruleset_id=ruleset_id, status="RUNNING", summary={})
    db.add(ev); db.commit()
    # Call rules-engine to evaluate
    r = requests.post("http://rules-engine:8010/evaluate", json={"project_version_id": project_version_id, "ruleset_id": ruleset_id}, timeout=60)
    r.raise_for_status()
    summary = r.json()
    ev.status="DONE"
    ev.summary=summary
    db.commit()
    log(db, user["sub"], "evaluation.run", "evaluation", eid, {"ruleset_id": ruleset_id})
    return {"evaluation_id": eid, "summary": summary}
