import time, hashlib
from typing import Any, Dict, Optional
from jose import jwt
from passlib.context import CryptContext
from .settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def verify_password(p: str, h: str) -> bool:
    return pwd_context.verify(p, h)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def issue_jwt(sub: str, role: str, institution_id: str) -> str:
    payload = {"sub": sub, "role": role, "institution_id": institution_id, "iat": int(time.time())}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
