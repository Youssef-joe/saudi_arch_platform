import requests
from fastapi import APIRouter, Depends
from ..deps import current_user

router = APIRouter()

@router.get("/layers")
def layers(user=Depends(current_user)):
    r = requests.get("http://gis-engine:8030/layers", timeout=20)
    r.raise_for_status()
    return r.json()
