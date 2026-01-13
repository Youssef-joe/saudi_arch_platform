from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sima_shared.db import get_db
from sima_shared import models
import numpy as np

app = FastAPI(title="rules-engine", version="1.4")

@app.post("/evaluate")
def evaluate(payload: dict, db: Session = Depends(get_db)):
    project_version_id = payload.get("project_version_id")
    ruleset_id = payload.get("ruleset_id")
    rules = db.query(models.Rule).filter(models.Rule.ruleset_id==ruleset_id).all()
    files = db.query(models.FileObject).filter(models.FileObject.project_version_id==project_version_id).all()
    kinds = set([f.kind for f in files])
    results=[]
    pass_count=0
    for r in rules:
        ok=True
        detail={}
        if r.check_type=="doc_present":
            required = set(r.params.get("kinds",[]))
            missing = sorted(list(required - kinds))
            ok = len(missing)==0
            detail={"missing": missing}
        # placeholder: facade_opening_ratio would call ml-engine in next iteration
        if r.check_type=="facade_opening_ratio":
            ok = True
            detail={"note":"computed in ml-engine (planned)"}
        results.append({"rule_id": r.id, "ref": r.ref, "severity": r.severity, "ok": ok, "detail": detail})
        if ok: pass_count += 1
    summary={"total": len(results), "passed": pass_count, "failed": len(results)-pass_count, "results": results}
    return summary
