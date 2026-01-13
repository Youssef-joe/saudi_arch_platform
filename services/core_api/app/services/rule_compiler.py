import uuid, re
from sqlalchemy.orm import Session
from sima_shared import models

# A pragmatic v1 compiler: extracts enforceable statements and maps to check types.
# Extension point: replace heuristics with an NLP classifier + a rule DSL.
def compile_ruleset(db: Session, guideline_version_id: str, ruleset_id: str):
    items = db.query(models.GuideItem).filter(models.GuideItem.guideline_version_id==guideline_version_id).all()
    out=[]
    for it in items:
        t = it.text.lower()
        severity = "INFO"
        check_type = "manual"
        params = {}
        # doc requirements
        if "must" in t or "يجب" in it.text:
            severity = "WARN"
        if "required" in t or "يجب" in it.text:
            # if it mentions drawings / elevations / material spec -> require documents
            if any(k in t for k in ["elevation","drawing","spec","ifc","material","palette","ral"]) or any(k in it.text for k in ["واجه","مخطط","مواصفات","مواد","الوان","ifc"]):
                check_type="doc_present"
                params={"kinds":["ifc","facade_image","materials_spec"]}
                severity="BLOCK"
        # opening ratios hints
        if any(k in t for k in ["ratio","width","height"]) or any(k in it.text for k in ["نسبة","عرض","ارتفاع"]):
            check_type="facade_opening_ratio"
            params={"min":0.5,"max":2.0}  # placeholder bounds; replaced by parsed values later
            severity="WARN"
        rid = str(uuid.uuid4())
        r = models.Rule(id=rid, ruleset_id=ruleset_id, ref=it.ref, severity=severity, check_type=check_type, params=params, tags=it.tags or {})
        db.add(r)
        out.append(r)
    db.commit()
    return out
