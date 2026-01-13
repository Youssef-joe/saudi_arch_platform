import io, uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from lxml import etree

app = FastAPI(title="bim-engine", version="1.4")

@app.post("/ifc/summary")
async def ifc_summary(ifc: UploadFile = File(...)):
    data = await ifc.read()
    try:
        import ifcopenshell
        m = ifcopenshell.file.from_string(data.decode("utf-8", errors="ignore"))
        counts={}
        for e in m:
            t = e.is_a()
            counts[t] = counts.get(t,0)+1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
        return {"entities_top": top, "total_entities": sum(counts.values())}
    except Exception as e:
        raise HTTPException(400, f"IFC parse failed: {e}")

@app.post("/ids/validate_lite")
async def ids_validate_lite(ifc: UploadFile = File(...), ids_xml: UploadFile = File(...)):
    # Lite: parse IDS XML and validate a subset of requirements (entity + property existence) using IfcOpenShell.
    ifc_bytes = await ifc.read()
    ids_bytes = await ids_xml.read()
    try:
        import ifcopenshell
        model = ifcopenshell.file.from_string(ifc_bytes.decode("utf-8", errors="ignore"))
    except Exception as e:
        raise HTTPException(400, f"IFC parse failed: {e}")
    try:
        root = etree.fromstring(ids_bytes)
    except Exception as e:
        raise HTTPException(400, f"IDS XML parse failed: {e}")

    # Heuristic parsing: look for IFC class names in <entity> tags and property names in <property> tags.
    entities=set([el.text.strip() for el in root.findall('.//entity') if el.text])
    props=set([el.text.strip() for el in root.findall('.//property') if el.text])

    results=[]
    for ent in sorted(list(entities))[:100]:
        elems = model.by_type(ent) if hasattr(model, "by_type") else []
        ok = len(elems)>0
        results.append({"check":"entity_present","entity":ent,"ok":ok,"count":len(elems)})
    # property existence (very lite): scan IfcPropertySingleValue names
    prop_names=set()
    try:
        for pset in model.by_type("IfcPropertySet"):
            for p in (pset.HasProperties or []):
                if getattr(p,"Name",None):
                    prop_names.add(str(p.Name))
    except Exception:
        pass
    for prop in sorted(list(props))[:200]:
        results.append({"check":"property_present","property":prop,"ok":prop in prop_names})
    summary={"total": len(results), "failed": sum(1 for r in results if not r["ok"])}
    return {"summary": summary, "results": results}
