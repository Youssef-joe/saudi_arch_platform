import uuid, time, hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from ..deps import current_user
from ..audit import log

router = APIRouter()

def _hash(prev: str, payload: dict) -> str:
    s = prev + "|" + str(sorted(payload.items()))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@router.post("")
def decide(payload: dict, db: Session = Depends(get_db), user=Depends(current_user)):
    evaluation_id = payload.get("evaluation_id")
    verdict = payload.get("verdict")
    ev = db.get(models.Evaluation, evaluation_id)
    if not ev: raise HTTPException(404,"evaluation not found")
    did = str(uuid.uuid4())
    base = {"evaluation_id": evaluation_id, "verdict": verdict, "by": user["sub"], "ts": int(time.time())}
    h0 = _hash("GENESIS", base)
    trace = {"genesis": "GENESIS", "head": h0, "events":[{"hash": h0, "payload": base}]}
    d = models.Decision(id=did, evaluation_id=evaluation_id, verdict=verdict, rationale=payload.get("rationale"), trace=trace)
    db.add(d); db.commit()
    log(db, user["sub"], "decision.create", "decision", did, {"verdict": verdict})
    return {"decision_id": did, "trace_head": h0}

@router.get("/{decision_id}")
def get_decision(decision_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    d = db.get(models.Decision, decision_id)
    if not d: raise HTTPException(404,"decision not found")
    return {"id": d.id, "verdict": d.verdict, "rationale": d.rationale, "trace": d.trace}
