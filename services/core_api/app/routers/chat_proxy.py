import requests
from fastapi import APIRouter, Depends
from ..deps import current_user

router = APIRouter()

@router.post("/ask")
def ask(payload: dict, user=Depends(current_user)):
    r = requests.post("http://llm-governor:8040/ask", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()
