import requests
from fastapi import APIRouter, Depends
from ..deps import current_user

router = APIRouter()

@router.get("/health")
def health(user=Depends(current_user)):
    return {"ok": True}
