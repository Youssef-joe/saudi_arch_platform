from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from .routers.vision import router as vision_router
from .routers.projects import router as projects_router
from .routers.scorecard import router as scorecard_router
from .routers.report import router as report_router
from .routers.evaluations import router as evaluations_router
from .routers.cert import router as cert_router
from .routers.flow import router as flow_router
from .routers.guidelines import router as guidelines_router

from .utils.db import init_db

app = FastAPI(title="منصة العمارة السعودية الذكية (MVP)", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes (BEFORE catch-all routes)
app.include_router(projects_router)
app.include_router(vision_router)
app.include_router(scorecard_router)
app.include_router(report_router)
app.include_router(evaluations_router)
app.include_router(cert_router)
app.include_router(flow_router)
app.include_router(guidelines_router)

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/health")
def health():
    return {"ok": True, "service": "sima-ai-mvp", "version": app.version}

# Serve static files - DO NOT mount "/"
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve index.html for root and all non-API routes (SPA routing)
# This MUST be last to avoid catching API routes
@app.get("/")
async def serve_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "Frontend not found"}

@app.get("/{path:path}")
async def serve_spa(path: str):
    # Don't intercept API calls or docs
    if path.startswith("v1/") or path.startswith("docs") or path.startswith("redoc") or path.startswith("openapi"):
        return {"error": "Not found"}, 404
    
    # Check if file exists in static
    file_path = os.path.join(static_dir, path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Return index.html for all other routes (SPA routing)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    return {"error": "Not found"}, 404
