import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from ..deps import current_user
from ..audit import log
from ..services.rule_compiler import compile_ruleset

router = APIRouter()

@router.post("/compile")
def compile(payload: dict, db: Session = Depends(get_db), user=Depends(current_user)):
    guideline_version_id = payload.get("guideline_version_id")
    if not guideline_version_id:
        raise HTTPException(400,"guideline_version_id required")
    rsid = str(uuid.uuid4())
    rs = models.Ruleset(id=rsid, guideline_version_id=guideline_version_id, name=payload.get("name","Ruleset"))
    db.add(rs); db.commit()
    rules = compile_ruleset(db, guideline_version_id, rsid)
    log(db, user["sub"], "ruleset.compile", "ruleset", rsid, {"rules": len(rules)})
    return {"ruleset_id": rsid, "rules": len(rules)}

@router.get("/{ruleset_id}/rules")
def list_rules(ruleset_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    rules = db.query(models.Rule).filter(models.Rule.ruleset_id==ruleset_id).all()
    return [{"id":r.id,"ref":r.ref,"severity":r.severity,"check_type":r.check_type,"params":r.params,"tags":r.tags} for r in rules]
