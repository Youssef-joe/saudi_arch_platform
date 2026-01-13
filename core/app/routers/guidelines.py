from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from ..engines.guidelines_ingest import extract_pdf_text_pages, suggest_rules_from_guidelines, write_suggestions_json
from ..engines.url_fetch import fetch_to_file


router = APIRouter(prefix="/v1/guidelines", tags=["guidelines"])


class IngestUrlRequest(BaseModel):
    urls: List[str]
    max_pages: Optional[int] = None


@router.post("/ingest")
async def ingest_guidelines_pdf(pdf: UploadFile = File(...), max_pages: Optional[int] = None):
    """Upload a guidelines PDF and get conservative rule suggestions.

    Why: our web environment may not always fetch large PDFs directly.
    This endpoint turns user-supplied PDFs into evidence-backed candidate
    constraints that can be reviewed and then encoded into the G2C Rule DSL.
    """

    if not (pdf.filename or "").lower().endswith(".pdf"):
        return {"ok": False, "error": "File must be a PDF"}

    uploads_dir = Path(__file__).resolve().parent.parent / "data" / "guidelines_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    out_path = uploads_dir / (pdf.filename or "guidelines.pdf")

    content = await pdf.read()
    out_path.write_bytes(content)

    pages = extract_pdf_text_pages(out_path, max_pages=max_pages)
    suggestions = suggest_rules_from_guidelines(pages)
    return {
        "ok": True,
        "file": out_path.name,
        "pages_extracted": len(pages),
        "suggestions": write_suggestions_json(suggestions),
    }


@router.post("/ingest-url")
def ingest_guidelines_from_urls(req: IngestUrlRequest):
    """Fetch guideline PDFs from allowlisted URLs, extract pages, and suggest rules.

    This is the production path when you have stable public URLs (e.g. architsaudi).
    In some restricted environments, server-side outbound access may be blocked;
    in that case, download the PDFs locally and use /ingest instead.
    """

    uploads_dir = Path(__file__).resolve().parent.parent / "data" / "guidelines_uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    files = []
    all_pages = []
    for url in req.urls:
        fetched = fetch_to_file(url, uploads_dir)
        files.append({"url": fetched.url, "file": fetched.path.name, "bytes": fetched.size_bytes, "content_type": fetched.content_type})
        pages = extract_pdf_text_pages(fetched.path, max_pages=req.max_pages)
        all_pages.extend(pages)

    suggestions = suggest_rules_from_guidelines(all_pages)
    return {
        "ok": True,
        "sources": files,
        "pages_extracted": len(all_pages),
        "suggestions": write_suggestions_json(suggestions),
    }


@router.get("/templates/east-coast")
def east_coast_template_rules():
    """Return a starter rule template for East Coast architecture.

    NOTE: This is a starter template derived from the public overview text
    on the official Saudi Architecture platform. It is intentionally non-numeric
    until we ingest the official PDF guidelines.
    """

    return {
        "style_code": "east_coast",
        "rules": [
            {
                "id": "east.materials.coral_or_plaster",
                "severity": "warn",
                "when": {"any": [{"feature": "materials.contains", "op": "in", "value": ["coral_stone", "white_plaster"]}]},
                "message": "يُفضّل استخدام جدران متينة من الصخور المرجانية أو تشطيب بالجص الأبيض بما يتوافق مع عمارة الساحل الشرقي.",
                "fix": "راجع تشطيبات الواجهات: دمج الجص الأبيض/الحجر المرجاني في الطبقات الظاهرة أو بدائل مكافئة ضمن نفس اللغة.",
            },
            {
                "id": "east.openings.recessed_large_with_screens",
                "severity": "warn",
                "when": {"any": [{"feature": "openings.has_recessed", "op": "eq", "value": True}]},
                "message": "فتحات الواجهات في الساحل الشرقي غالبًا كبيرة وغائرة مع سواتر/شاشات خشبية لتحسين المناخ والخصوصية.",
                "fix": "أضف عمق (recess) للفتحات واستخدم شاشات خشبية/مشربيات عند الواجهات الأكثر تعرضًا للشمس.",
            },
            {
                "id": "east.elements.mashrabiya_or_screens",
                "severity": "warn",
                "when": {"any": [{"feature": "elements.mashrabiya", "op": "gte", "value": 1}, {"feature": "elements.wood_screens", "op": "gte", "value": 1}]},
                "message": "المشربيات/السواتر الخشبية عنصر مميّز في عمارة الساحل الشرقي لمقاومة الحرارة والرطوبة.",
                "fix": "أدرج شاشة خشبية أو مشربية ضمن نقاط الواجهة (خصوصًا الجنوبية/الغربية) مع نسب تظليل منطقية.",
            },
            {
                "id": "east.decor.gypsum_and_triple_arch",
                "severity": "info",
                "when": {"any": [{"feature": "elements.gypsum_decor", "op": "gte", "value": 1}, {"feature": "elements.triple_arch", "op": "gte", "value": 1}]},
                "message": "الزخارف الجصية الدقيقة والأقواس الثلاثية من السمات المتكررة في الطراز التقليدي للساحل الشرقي.",
                "fix": "إن كان المشروع يسمح: أضف زخارف جصية دقيقة/قوس ثلاثي في مدخل أو رواق، دون إفراط.",
            },
            {
                "id": "east.mass.courtyard_arcades",
                "severity": "info",
                "when": {"any": [{"feature": "massing.has_courtyard", "op": "eq", "value": True}]},
                "message": "تتمحور البيوت التقليدية حول أفنية مظللة بالأروقة لتعزيز الخصوصية والتكيف المناخي.",
                "fix": "فعّل فناء داخلي أو ارتداد مظلل مع أروقة عند الإمكان، خصوصًا في الفلل.",
            },
        ],
    }
