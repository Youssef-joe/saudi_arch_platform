import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.security import hash_password, verify_password, issue_jwt
from sima_shared.db import get_db
from sima_shared.settings import settings

router = APIRouter()

@router.on_event("startup")
def seed():
    db = next(get_db())
    inst = db.get(models.Institution, "national")
    if not inst:
        inst = models.Institution(id="national", name="National", region=None)
        db.add(inst); db.commit()
    admin = db.query(models.User).filter(models.User.email==settings.ADMIN_EMAIL).first()
    if not admin:
        admin = models.User(
            id=str(uuid.uuid4()),
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
            institution_id="national",
            is_active=True,
        )
        db.add(admin); db.commit()

@router.post("/login")
def login(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email","").lower().strip()
    password = payload.get("password","")
    u = db.query(models.User).filter(models.User.email==email).first()
    if not u or not verify_password(password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = issue_jwt(sub=u.id, role=u.role, institution_id=u.institution_id)
    return {"access_token": token, "token_type":"bearer", "role": u.role}
