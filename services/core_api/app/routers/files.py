import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from sima_shared.security import sha256_bytes
from sima_shared.storage import put_bytes
from ..deps import current_user
from ..audit import log

router = APIRouter()

@router.post("/upload")
async def upload(project_version_id: str, kind: str, f: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(current_user)):
    pv = db.get(models.ProjectVersion, project_version_id)
    if not pv: raise HTTPException(404,"project_version not found")
    data = await f.read()
    h = sha256_bytes(data)
    fid = str(uuid.uuid4())
    key = f"{project_version_id}/{fid}/{f.filename}"
    put_bytes(key, data, f.content_type or "application/octet-stream")
    fo = models.FileObject(
        id=fid, project_version_id=project_version_id, kind=kind, filename=f.filename, sha256=h, storage_key=key, meta={}
    )
    db.add(fo); db.commit()
    log(db, user["sub"], "file.upload", "file", fid, {"kind": kind, "sha256": h})
    return {"id": fid, "sha256": h, "storage_key": key}
