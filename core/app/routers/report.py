from __future__ import annotations

import datetime
import io
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

from ..utils.db import get_evaluation_by_id

router = APIRouter(prefix="/v1/report", tags=["report"])


def _draw_qr(c: canvas.Canvas, value: str, x: float, y: float, size: float = 120.0) -> None:
    widget = qr.QrCodeWidget(value)
    bounds = widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, x, y)


def build_assessment_pdf(
    *,
    project: Dict[str, Any],
    evaluation: Dict[str, Any],
    pattern_code: Optional[str] = None,
    certificate_token: Optional[str] = None,
    verify_url: Optional[str] = None,
    created_at: Optional[str] = None,
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Cover
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 70, "Sima AI — Saudi Architecture Smart Assessment")
    c.setFont("Helvetica", 11)
    ts = created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.drawString(50, height - 95, f"Generated: {ts}")
    if pattern_code:
        c.drawString(50, height - 112, f"Pattern: {pattern_code}")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 145, "Project")
    c.setFont("Helvetica", 11)
    c.drawString(70, height - 165, f"Name: {project.get('name','-')}")
    c.drawString(70, height - 182, f"City: {project.get('city','-')}")
    if project.get("height_m") is not None:
        c.drawString(70, height - 199, f"Height (m): {project.get('height_m')}")

    # Summary
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 235, "Summary")
    c.setFont("Helvetica", 11)
    c.drawString(70, height - 255, f"Overall score: {evaluation.get('overall_score','-')}")
    c.drawString(70, height - 272, f"Status: {evaluation.get('status','-')}")

    # Ruleset meta (Evidence Pack pointer)
    ruleset_meta = evaluation.get("ruleset") or {}
    rs = ruleset_meta.get("ruleset") or {}
    if ruleset_meta.get("sha256"):
        c.setFont("Helvetica", 10)
        c.drawString(70, height - 289, f"Ruleset: {rs.get('id','-')}@{rs.get('version','-')} | sha256: {ruleset_meta.get('sha256')[:16]}…")

    # Certificate QR
    if verify_url:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 310, "Certificate / Verification")
        c.setFont("Helvetica", 10)
        c.drawString(70, height - 328, f"Verify URL: {verify_url}")
        if certificate_token:
            c.drawString(70, height - 342, f"Token: {certificate_token}")
        _draw_qr(c, verify_url, x=width - 170, y=height - 370, size=120)

    # Checks
    y = height - 400
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Checks")
    y -= 20

    c.setFont("Helvetica", 10)
    for chk in evaluation.get("checks", []):
        if y < 80:
            c.showPage()
            y = height - 70
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, "Checks (cont.)")
            y -= 20
            c.setFont("Helvetica", 10)

        title = chk.get("title") or chk.get("check_id")
        status = chk.get("status")
        score = chk.get("score")
        c.drawString(60, y, f"- [{status}] {title} (score: {score})")
        y -= 13
        reasoning = (chk.get("reasoning") or "").strip()
        recommendation = (chk.get("recommendation") or "").strip()
        if reasoning:
            c.drawString(75, y, f"Reason: {reasoning[:110]}")
            y -= 12
        if recommendation:
            c.drawString(75, y, f"Fix: {recommendation[:110]}")
            y -= 14

        # Evidence Pack: optional guideline references attached to the rule
        ev = chk.get("evidence") or {}
        refs = ev.get("guideline_refs") or []
        if refs:
            for ref in refs[:2]:
                if y < 80:
                    c.showPage()
                    y = height - 70
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(50, y, "Checks (cont.)")
                    y -= 20
                    c.setFont("Helvetica", 10)
                doc = ref.get("doc") or ref.get("source") or "guideline"
                page = ref.get("page")
                note = ref.get("note") or ref.get("snippet") or ""
                line = f"Evidence: {doc}" + (f" p.{page}" if page else "")
                c.drawString(75, y, line[:110])
                y -= 12
                if note:
                    c.drawString(90, y, (str(note)[:105]))
                    y -= 14

    c.showPage()
    c.save()
    return buffer.getvalue()


@router.post("/assessment")
def assessment(payload: Dict[str, Any] = Body(...)):
    """Generate a PDF assessment report.

    You can pass the response from /v1/scorecard/evaluate directly.
    Optionally include:
      - certificate_token
      - urls.verify
      - created_at
    """
    project = payload.get("project") or {}
    evaluation = payload.get("evaluation") or {}
    pattern_code = payload.get("pattern_code")

    verify_url = None
    token = payload.get("certificate_token")
    urls = payload.get("urls") or {}
    if urls.get("verify"):
        verify_url = urls["verify"]

    pdf_bytes = build_assessment_pdf(
        project=project,
        evaluation=evaluation,
        pattern_code=pattern_code,
        certificate_token=token,
        verify_url=verify_url,
        created_at=payload.get("created_at"),
    )

    return Response(content=pdf_bytes, media_type="application/pdf")


@router.get("/evaluation/{evaluation_id}.pdf")
def evaluation_pdf(evaluation_id: int):
    obj = get_evaluation_by_id(evaluation_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    token = obj.get("token")
    verify_url = f"/v1/cert/verify/{token}" if token else None

    pdf_bytes = build_assessment_pdf(
        project=obj.get("project") or {},
        evaluation=obj.get("evaluation") or {},
        pattern_code=obj.get("pattern_code"),
        certificate_token=token,
        verify_url=verify_url,
        created_at=obj.get("created_at"),
    )
    return Response(content=pdf_bytes, media_type="application/pdf")
