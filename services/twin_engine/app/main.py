from __future__ import annotations

import uuid
import hashlib
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from sima_shared.db import get_db
from sima_shared import models
from sima_shared.storage import put_bytes, get_bytes


app = FastAPI(title="twin-engine", version="1.6")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@app.post("/assets/upload")
async def upload_asset(
    project_version_id: str,
    kind: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    kind = (kind or "").strip().lower()
    if kind not in {"tileset", "gltf", "pointcloud", "photogrammetry", "other"}:
        raise HTTPException(400, "invalid kind")
    pv = db.query(models.ProjectVersion).filter(models.ProjectVersion.id == project_version_id).first()
    if not pv:
        raise HTTPException(404, "project_version not found")

    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")

    h = _sha256(data)
    storage_key = f"twin/{project_version_id}/{h}_{file.filename}"
    put_bytes(storage_key, data, content_type=file.content_type or "application/octet-stream")

    asset = models.TwinAsset(
        id=str(uuid.uuid4()),
        project_version_id=project_version_id,
        kind=kind,
        storage_key=storage_key,
        sha256=h,
        meta={"filename": file.filename, "content_type": file.content_type},
    )
    db.add(asset)
    db.commit()
    return {"ok": True, "asset_id": asset.id, "sha256": h, "storage_key": storage_key}


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    a = db.query(models.TwinAsset).filter(models.TwinAsset.id == asset_id).first()
    if not a:
        raise HTTPException(404, "asset not found")
    return {
        "id": a.id,
        "project_version_id": a.project_version_id,
        "kind": a.kind,
        "sha256": a.sha256,
        "storage_key": a.storage_key,
        "meta": a.meta or {},
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@app.get("/assets/{asset_id}/download")
def download_asset(asset_id: str, db: Session = Depends(get_db)):
    a = db.query(models.TwinAsset).filter(models.TwinAsset.id == asset_id).first()
    if not a:
        raise HTTPException(404, "asset not found")
    blob = get_bytes(a.storage_key)
    ct = (a.meta or {}).get("content_type") or "application/octet-stream"
    return Response(content=blob, media_type=ct)


@app.get("/health")
def health():
    return {"ok": True}
