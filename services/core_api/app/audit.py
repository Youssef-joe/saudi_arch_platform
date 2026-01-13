import uuid
from sqlalchemy.orm import Session
from sima_shared import models

def log(db: Session, actor_user_id: str, action: str, entity_type: str|None=None, entity_id: str|None=None, detail: dict|None=None):
    ev = models.AuditLog(
        id=str(uuid.uuid4()),
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or {},
    )
    db.add(ev); db.commit()
