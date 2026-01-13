import requests
from fastapi import APIRouter, Depends
from ..deps import current_user

router = APIRouter()


@router.get("/Things")
def list_things(top: int = 100, user=Depends(current_user)):
    r = requests.get("http://iot-engine:8060/v1.1/Things", params={"top": top}, timeout=30)
    r.raise_for_status()
    return r.json()


@router.post("/Things")
def create_thing(payload: dict, user=Depends(current_user)):
    r = requests.post("http://iot-engine:8060/v1.1/Things", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


@router.get("/Datastreams")
def list_datastreams(top: int = 200, thingId: str | None = None, user=Depends(current_user)):
    params = {"top": top}
    if thingId:
        params["thingId"] = thingId
    r = requests.get("http://iot-engine:8060/v1.1/Datastreams", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


@router.post("/Datastreams")
def create_datastream(payload: dict, user=Depends(current_user)):
    r = requests.post("http://iot-engine:8060/v1.1/Datastreams", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


@router.get("/Observations")
def list_observations(top: int = 500, datastreamId: str | None = None, user=Depends(current_user)):
    params = {"top": top}
    if datastreamId:
        params["datastreamId"] = datastreamId
    r = requests.get("http://iot-engine:8060/v1.1/Observations", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


@router.post("/Observations")
def create_observation(payload: dict, user=Depends(current_user)):
    r = requests.post("http://iot-engine:8060/v1.1/Observations", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
