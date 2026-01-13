from __future__ import annotations

import base64
import tempfile
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

try:
    from skimage.color import rgb2lab, deltaE_ciede2000  # type: ignore
except Exception:
    rgb2lab = None
    deltaE_ciede2000 = None


STYLE_PALETTES: Dict[str, List[str]] = {
    "coastal_hejazi": ["#FFFFFF", "#2E6F6A", "#5A3E2B", "#E8DCC7"],
    "central_najdi": ["#EFE6DD", "#A56B3F", "#6E4B3A", "#2F2A26"],
    "eastern_coast": ["#F7F4EE", "#2F6F73", "#6D4B3A", "#E2D5C3"],
    "asiri": ["#F4EDE3", "#C64B4B", "#2F5D50", "#1F3B73"],
}


def b64_to_bgr(image_base64: str):
    if cv2 is None:
        raise RuntimeError("OpenCV not installed")
    arr = np.frombuffer(base64.b64decode(image_base64), dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def extract_palette_kmeans(image_bgr, k: int = 6) -> List[str]:
    if cv2 is None:
        return []
    img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    Z = img.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    K = max(2, min(10, int(k)))
    _, _, center = cv2.kmeans(Z, K, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    center = np.uint8(center)
    return ["#%02X%02X%02X" % (c[0], c[1], c[2]) for c in center]


def deltaE_to_style_palette(palette_hex: List[str], style_id: str) -> Dict[str, float]:
    ref = STYLE_PALETTES.get(style_id) or []
    if not (deltaE_ciede2000 and rgb2lab) or not ref or not palette_hex:
        return {"avg": -1.0, "max": -1.0}

    def hex_to_rgb(h: str):
        h = h.lstrip("#")
        return [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    pal = np.array([hex_to_rgb(h) for h in palette_hex]).reshape((-1, 1, 3))
    refp = np.array([hex_to_rgb(h) for h in ref]).reshape((-1, 1, 3))
    pal_lab = rgb2lab(pal)
    ref_lab = rgb2lab(refp)

    dists: List[float] = []
    for a in pal_lab:
        d = np.min([deltaE_ciede2000(a, b).mean() for b in ref_lab])
        dists.append(float(d))

    return {"avg": float(np.mean(dists)), "max": float(np.max(dists))}


def polygon_area(points):
    a = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        a += x1 * y2 - x2 * y1
    return abs(a) * 0.5


def wwr_from_dxf_b64(b64: str) -> Dict[str, Any]:
    try:
        import ezdxf  # type: ignore
    except Exception as e:
        return {"error": "ezdxf not installed", "detail": str(e)}

    data = base64.b64decode(b64)
    tmp = tempfile.mktemp(suffix=".dxf")
    open(tmp, "wb").write(data)
    doc = ezdxf.readfile(tmp)
    msp = doc.modelspace()

    layers: Dict[str, int] = {}
    entity_types: Dict[str, int] = {}
    for e in msp:
        layer = (e.dxf.layer or "0").upper()
        etype = e.dxftype()
        layers[layer] = layers.get(layer, 0) + 1
        entity_types[etype] = entity_types.get(etype, 0) + 1

    def to_pts(e):
        if hasattr(e, "get_points"):
            return [(p[0], p[1]) for p in e.get_points("xy")]
        if hasattr(e, "points"):
            return [(p[0], p[1]) for p in e.points]
        return []

    facade = None
    wins = []
    for e in msp.query("LWPOLYLINE POLYLINE"):
        layer = (e.dxf.layer or "").upper()
        if layer == "FACADE":
            facade = to_pts(e)
        elif layer == "WINDOW":
            pts = to_pts(e)
            if pts:
                wins.append(pts)

    if not facade:
        return {
            "message": "DXF loaded",
            "note": "لحساب WWR، يحتاج الملف layers بأسماء FACADE و WINDOW",
            "layers_found": dict(sorted(layers.items())),
            "entity_types": dict(sorted(entity_types.items())),
            "total_entities": sum(entity_types.values()),
            "wwr_pct": 0.0,
        }

    wall_area = polygon_area(facade)
    win_area = sum(polygon_area(p) for p in wins)
    wwr = round((win_area / wall_area * 100.0), 2) if wall_area > 0 else 0.0
    return {"wall_area": wall_area, "window_area": win_area, "wwr_pct": wwr}


def wwr_from_ifc_b64(b64: str) -> Dict[str, Any]:
    try:
        import ifcopenshell  # type: ignore
    except Exception as e:
        return {"error": "IfcOpenShell not installed", "detail": str(e)}

    data = base64.b64decode(b64)
    tmp = tempfile.mktemp(suffix=".ifc")
    open(tmp, "wb").write(data)
    model = ifcopenshell.open(tmp)

    walls = model.by_type("IfcWall") + model.by_type("IfcWallStandardCase")
    wins = model.by_type("IfcWindow")

    def area_of(el):
        h = getattr(el, "OverallHeight", 0) or 0
        w = getattr(el, "OverallWidth", 0) or 0
        try:
            return float(h) * float(w)
        except Exception:
            return 0.0

    wall_area = sum(area_of(w) for w in walls)
    win_area = sum(area_of(wi) for wi in wins)
    wwr = round((win_area / wall_area * 100.0), 2) if wall_area > 0 else 0.0
    return {"wall_area": wall_area, "window_area": win_area, "wwr_pct": wwr}


def try_detect_elements(image_bgr, prompts: List[str]) -> List[Dict[str, Any]]:
    """Optional hook for vision detection. If hooks are not present, returns []."""
    try:
        from hooks import detect_with_grounding_dino  # type: ignore
    except Exception:
        try:
            from model_hooks import detect_with_grounding_dino  # type: ignore
        except Exception:
            return []

    try:
        return detect_with_grounding_dino(image_bgr, prompts)
    except Exception:
        return []
