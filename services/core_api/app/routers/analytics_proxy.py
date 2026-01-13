import requests
from fastapi import APIRouter, Depends
from ..deps import current_user

router = APIRouter()


@router.get("/overview")
def overview(user=Depends(current_user)):
    r = requests.get("http://analytics-engine:8080/dashboards/overview", timeout=30)
    r.raise_for_status()
    return r.json()
