from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from sima_shared.migrate import run as migrate
from sima_shared.storage import ensure_bucket

from .routers import auth, projects, guidelines, rulesets, evaluations, decisions, gis_proxy, bim_proxy, chat_proxy, workflow, files, audits, iot_proxy, twin_proxy, analytics_proxy

app = FastAPI(title="core-api", version="1.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    migrate()
    ensure_bucket()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(guidelines.router, prefix="/guidelines", tags=["guidelines"])
app.include_router(rulesets.router, prefix="/rulesets", tags=["rulesets"])
app.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
app.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
app.include_router(audits.router, prefix="/audit", tags=["audit"])

# Proxy routers (separation of concerns) – calls engines
app.include_router(gis_proxy.router, prefix="/gis", tags=["gis"])
app.include_router(bim_proxy.router, prefix="/bim", tags=["bim"])
app.include_router(chat_proxy.router, prefix="/chat", tags=["chat"])
app.include_router(iot_proxy.router, prefix="/iot", tags=["iot"])
app.include_router(twin_proxy.router, prefix="/twin", tags=["twin"])
app.include_router(analytics_proxy.router, prefix="/analytics", tags=["analytics"])

app.mount("/metrics", make_asgi_app())
