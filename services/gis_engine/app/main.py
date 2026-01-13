import uuid, json
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sima_shared.db import get_db
from sima_shared import models
from sima_shared.security import sha256_bytes

app = FastAPI(title="gis-engine", version="1.4")

# Minimal GIS layer registry (metadata stored via generic table using GuideItem? keep simple in v1.4: store as GuideItem-like rows in separate future table)
# For now: accept, hash, and return bbox via quick scan (GeoJSON only)

def bbox_from_geojson(obj):
    coords=[]
    def walk(x):
        if isinstance(x, list):
            if len(x)==2 and all(isinstance(v,(int,float)) for v in x):
                coords.append(x)
            else:
                for v in x: walk(v)
    walk(obj.get("coordinates", []))
    if not coords: return None
    xs=[c[0] for c in coords]; ys=[c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]

_layers = {}

@app.post("/layers")
async def upload_layer(code: str, f: UploadFile = File(...)):
    data = await f.read()
    h = sha256_bytes(data)
    obj = json.loads(data.decode("utf-8"))
    bbox = bbox_from_geojson(obj) or [0,0,0,0]
    _layers[code] = {"code": code, "sha256": h, "bbox": bbox}
    return _layers[code]

@app.get("/layers")
def list_layers():
    return list(_layers.values())

@app.get("/layers/{code}/bbox")
def get_bbox(code: str):
    if code not in _layers: raise HTTPException(404,"layer not found")
    return {"code": code, "bbox": _layers[code]["bbox"]}
