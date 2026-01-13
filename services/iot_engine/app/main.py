from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from sima_shared.db import get_db
from sima_shared import models


app = FastAPI(title="iot-engine", version="1.6")


# NOTE: This is a SensorThings-LIKE API surface (minimal subset). It is intentionally
# designed so the platform can evolve toward full OGC SensorThings conformance.


@app.get("/v1.1/Things")
def list_things(db: Session = Depends(get_db), top: int = 100):
    things = db.query(models.IoTThing).order_by(models.IoTThing.created_at.desc()).limit(min(1000, top)).all()
    return {"value": [
        {
            "@iot.id": t.id,
            "name": t.name,
            "description": t.description,
            "location_wkt": t.location_wkt,
            "properties": t.meta or {},
        }
        for t in things
    ]}


@app.post("/v1.1/Things")
def create_thing(payload: dict, db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name required")
    t = models.IoTThing(
        id=str(uuid.uuid4()),
        name=name,
        description=(payload.get("description") or None),
        location_wkt=(payload.get("location_wkt") or None),
        meta=payload.get("properties") or {},
    )
    db.add(t)
    db.commit()
    return {"@iot.id": t.id}


@app.get("/v1.1/Datastreams")
def list_datastreams(db: Session = Depends(get_db), top: int = 200, thingId: Optional[str] = None):
    q = db.query(models.IoTDatastream)
    if thingId:
        q = q.filter(models.IoTDatastream.thing_id == thingId)
    ds = q.order_by(models.IoTDatastream.created_at.desc()).limit(min(2000, top)).all()
    return {"value": [
        {
            "@iot.id": d.id,
            "thingId": d.thing_id,
            "name": d.name,
            "unitOfMeasurement": d.unit,
            "observedProperty": d.observed_property,
            "properties": d.meta or {},
        }
        for d in ds
    ]}


@app.post("/v1.1/Datastreams")
def create_datastream(payload: dict, db: Session = Depends(get_db)):
    thing_id = (payload.get("thingId") or "").strip()
    name = (payload.get("name") or "").strip()
    if not thing_id or not name:
        raise HTTPException(400, "thingId and name required")
    if not db.query(models.IoTThing).filter(models.IoTThing.id == thing_id).first():
        raise HTTPException(404, "thing not found")
    d = models.IoTDatastream(
        id=str(uuid.uuid4()),
        thing_id=thing_id,
        name=name,
        unit=(payload.get("unitOfMeasurement") or None),
        observed_property=(payload.get("observedProperty") or None),
        meta=payload.get("properties") or {},
    )
    db.add(d)
    db.commit()
    return {"@iot.id": d.id}


@app.get("/v1.1/Observations")
def list_observations(db: Session = Depends(get_db), top: int = 500, datastreamId: Optional[str] = None):
    q = db.query(models.IoTObservation)
    if datastreamId:
        q = q.filter(models.IoTObservation.datastream_id == datastreamId)
    obs = q.order_by(models.IoTObservation.result_time.desc()).limit(min(5000, top)).all()
    return {"value": [
        {
            "@iot.id": o.id,
            "datastreamId": o.datastream_id,
            "resultTime": o.result_time.isoformat(),
            "result": o.result,
            "properties": o.meta or {},
        }
        for o in obs
    ]}


@app.post("/v1.1/Observations")
def create_observation(payload: dict, db: Session = Depends(get_db)):
    datastream_id = (payload.get("datastreamId") or "").strip()
    if not datastream_id:
        raise HTTPException(400, "datastreamId required")
    if not db.query(models.IoTDatastream).filter(models.IoTDatastream.id == datastream_id).first():
        raise HTTPException(404, "datastream not found")
    rt = payload.get("resultTime") or datetime.utcnow().isoformat()
    try:
        dt = datetime.fromisoformat(rt.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(400, "invalid resultTime")
    o = models.IoTObservation(
        id=str(uuid.uuid4()),
        datastream_id=datastream_id,
        result_time=dt,
        result=payload.get("result") or {},
        meta=payload.get("properties") or {},
    )
    db.add(o)
    db.commit()
    return {"@iot.id": o.id}


@app.get("/health")
def health():
    return {"ok": True}
