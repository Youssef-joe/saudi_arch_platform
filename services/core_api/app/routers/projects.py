import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from ..deps import current_user
from ..audit import log

router = APIRouter()

@router.post("")
def create_project(payload: dict, db: Session = Depends(get_db), user=Depends(current_user)):
    pid = str(uuid.uuid4())
    p = models.Project(
        id=pid,
        institution_id=user["institution_id"],
        name=payload.get("name","Untitled"),
        location_wkt=payload.get("location_wkt"),
        region=payload.get("region"),
        style=payload.get("style"),
        status="DRAFT",
    )
    db.add(p); db.commit()
    log(db, user["sub"], "project.create", "project", pid, {"name": p.name})
    return {"id": pid}

@router.get("")
def list_projects(db: Session = Depends(get_db), user=Depends(current_user)):
    qs = db.query(models.Project).filter(models.Project.institution_id==user["institution_id"]).all()
    return [{"id":p.id,"name":p.name,"status":p.status,"region":p.region,"style":p.style} for p in qs]

@router.post("/{project_id}/versions")
def create_version(project_id: str, payload: dict, db: Session = Depends(get_db), user=Depends(current_user)):
    p = db.get(models.Project, project_id)
    if not p: raise HTTPException(404,"project not found")
    latest = db.query(models.ProjectVersion).filter(models.ProjectVersion.project_id==project_id).order_by(models.ProjectVersion.version_no.desc()).first()
    vn = 1 if not latest else latest.version_no + 1
    vid = str(uuid.uuid4())
    v = models.ProjectVersion(
        id=vid, project_id=project_id, version_no=vn,
        guidelines_version_id=payload.get("guidelines_version_id"),
        ruleset_id=payload.get("ruleset_id"),
    )
    db.add(v); db.commit()
    log(db, user["sub"], "project.version.create", "project_version", vid, {"version_no": vn})
    return {"id": vid, "version_no": vn}
