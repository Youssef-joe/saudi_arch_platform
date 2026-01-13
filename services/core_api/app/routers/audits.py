from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from ..deps import current_user

router = APIRouter()

@router.get("")
def list_audit(limit: int = 50, db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(limit).all()
    return [{"id":r.id,"actor":r.actor_user_id,"action":r.action,"entity_type":r.entity_type,"entity_id":r.entity_id,"detail":r.detail,"created_at":str(r.created_at)} for r in rows]
