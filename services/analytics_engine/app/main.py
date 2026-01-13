from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from sima_shared.db import get_db
from sima_shared import models


app = FastAPI(title="analytics-engine", version="1.6")

REQ_COUNT = Counter("http_requests_total", "HTTP requests", ["path", "method", "status"])
REQ_LAT = Histogram("http_request_duration_seconds", "HTTP request duration", ["path", "method"])


@app.middleware("http")
async def prom_mw(request: Request, call_next):
    with REQ_LAT.labels(request.url.path, request.method).time():
        resp = await call_next(request)
    REQ_COUNT.labels(request.url.path, request.method, str(resp.status_code)).inc()
    return resp


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _count_recent(q, col, days: int = 7) -> int:
    since = datetime.utcnow() - timedelta(days=days)
    try:
        return int(q.filter(col >= since).count())
    except Exception:
        return int(q.count())


@app.get("/dashboards/overview")
def overview(db: Session = Depends(get_db)):
    audits_total = db.query(models.AuditLog).count()
    eval_total = db.query(models.Evaluation).count()
    dec_total = db.query(models.Decision).count()
    iot_obs_total = db.query(models.IoTObservation).count()
    twin_assets_total = db.query(models.TwinAsset).count()

    return {
        "ok": True,
        "totals": {
            "audit_log": audits_total,
            "evaluations": eval_total,
            "decisions": dec_total,
            "iot_observations": iot_obs_total,
            "twin_assets": twin_assets_total,
        },
        "notes": {
            "kpi": "هذه واجهة Workbench للمؤشرات. توسّعها لاحقًا بإحصاءات حسب الهيئة/الاستديو/الطراز/المرحلة.",
        },
    }


@app.get("/health")
def health():
    return {"ok": True}
