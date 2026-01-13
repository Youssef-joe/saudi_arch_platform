import uuid, requests
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sima_shared import models
from sima_shared.db import get_db
from sima_shared.security import sha256_bytes
from sima_shared.storage import put_bytes
from ..deps import current_user
from ..audit import log
from ..services.guidelines_pdf import pdf_to_items

router = APIRouter()

@router.post("/import/pdf")
async def import_pdf(region: str, pdf: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(current_user)):
    data = await pdf.read()
    h = sha256_bytes(data)
    gvid = str(uuid.uuid4())
    key = f"guidelines/{gvid}/{pdf.filename}"
    put_bytes(key, data, "application/pdf")
    gv = models.GuidelineVersion(id=gvid, source="architsaudi", region=region, pdf_url=None, sha256=h)
    db.add(gv); db.commit()
    items = pdf_to_items(data, ref_prefix=f"pdf:{pdf.filename}")
    for it in items:
        gi = models.GuideItem(
            id=str(uuid.uuid4()),
            guideline_version_id=gvid,
            ref=it["ref"],
            title=it.get("title"),
            text=it["text"],
            tags=it.get("tags",{}),
        )
        db.add(gi)
    db.commit()
    log(db, user["sub"], "guidelines.import.pdf", "guideline_version", gvid, {"region": region, "sha256": h, "items": len(items)})
    return {"guideline_version_id": gvid, "items": len(items)}

@router.post("/import/page")
def import_page(url: str, region: str|None=None, db: Session = Depends(get_db), user=Depends(current_user)):
    # Minimal: store page HTML as guideline_version + one guideitem per paragraph
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    html = r.text
    h = sha256_bytes(html.encode("utf-8"))
    gvid = str(uuid.uuid4())
    gv = models.GuidelineVersion(id=gvid, source="architsaudi", region=region, url=url, sha256=h)
    db.add(gv); db.commit()
    paras = [p.strip() for p in html.split("</p>") if "<p" in p]
    n=0
    for i,p in enumerate(paras[:500]):
        text = p.split(">")[-1].strip()
        if len(text) < 30: continue
        gi = models.GuideItem(id=str(uuid.uuid4()), guideline_version_id=gvid, ref=f"{url}#p{i}", title=None, text=text, tags={"enforceable": False})
        db.add(gi); n+=1
    db.commit()
    log(db, user["sub"], "guidelines.import.page", "guideline_version", gvid, {"url": url, "items": n})
    return {"guideline_version_id": gvid, "items": n}

@router.get("/versions")
def list_versions(db: Session = Depends(get_db), user=Depends(current_user)):
    vs = db.query(models.GuidelineVersion).order_by(models.GuidelineVersion.created_at.desc()).limit(50).all()
    return [{"id":v.id,"source":v.source,"region":v.region,"url":v.url,"sha256":v.sha256,"created_at":str(v.created_at)} for v in vs]
