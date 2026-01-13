from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sima_shared.db import get_db
from sima_shared.security import decode_jwt

def db() -> Session:
    return next(get_db())

def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return decode_jwt(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
