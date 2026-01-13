import requests
from fastapi import APIRouter, Depends, UploadFile, File
from ..deps import current_user

router = APIRouter()


@router.post("/assets/upload")
async def upload_asset(project_version_id: str, kind: str, file: UploadFile = File(...), user=Depends(current_user)):
    data = await file.read()
    files = {"file": (file.filename, data, file.content_type or "application/octet-stream")}
    r = requests.post(
        "http://twin-engine:8070/assets/upload",
        params={"project_version_id": project_version_id, "kind": kind},
        files=files,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, user=Depends(current_user)):
    r = requests.get(f"http://twin-engine:8070/assets/{asset_id}", timeout=30)
    r.raise_for_status()
    return r.json()


@router.get("/assets/{asset_id}/download")
def download_asset(asset_id: str, user=Depends(current_user)):
    # pass-through bytes
    r = requests.get(f"http://twin-engine:8070/assets/{asset_id}/download", timeout=120)
    r.raise_for_status()
    return {
        "ok": True,
        "content_type": r.headers.get("content-type"),
        "bytes_base64": __import__("base64").b64encode(r.content).decode("ascii"),
    }
