from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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

from ..utils.base64io import b64_to_tempfile


STYLE_PALETTES: Dict[str, List[str]] = {
    "coastal_hejazi": ["#FFFFFF", "#2E6F6A", "#5A3E2B", "#E8DCC7"],
    "central_najdi": ["#EFE6DD", "#A56B3F", "#6E4B3A"],
}

TEXT_PROMPTS = ["window", "door", "roshan", "mashrabiya", "arcade", "screen", "lattice"]


def _b64_to_bgr(s: str):
    arr = np.frombuffer(base64.b64decode(s), dtype=np.uint8)
    if cv2 is None:
        raise RuntimeError("OpenCV not installed")
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def extract_palette_kmeans(image_bgr, k: int = 6) -> List[str]:
    if cv2 is None:
        return []
    img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    Z = img.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    K = max(2, min(10, k))
    _, label, center = cv2.kmeans(Z, K, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
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


def polygon_area(points: List[Tuple[float, float]]) -> float:
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

    tmp = b64_to_tempfile(b64, ".dxf")
    doc = ezdxf.readfile(str(tmp))
    msp = doc.modelspace()

    layers: Dict[str, int] = {}
    entity_types: Dict[str, int] = {}

    for e in msp:
        layer = (getattr(e.dxf, "layer", None) or "0").upper()
        etype = e.dxftype()
        layers[layer] = layers.get(layer, 0) + 1
        entity_types[etype] = entity_types.get(etype, 0) + 1

    def to_pts(e) -> List[Tuple[float, float]]:
        if hasattr(e, "get_points"):
            return [(p[0], p[1]) for p in e.get_points("xy")]
        if hasattr(e, "points"):
            return [(p[0], p[1]) for p in e.points]
        return []

    facade = None
    wins: List[List[Tuple[float, float]]] = []
    for e in msp.query("LWPOLYLINE POLYLINE"):
        layer = (getattr(e.dxf, "layer", "") or "").upper()
        if layer == "FACADE":
            facade = to_pts(e)
        elif layer == "WINDOW":
            pts = to_pts(e)
            if pts:
                wins.append(pts)

    if not facade:
        return {
            "message": "DXF file loaded successfully",
            "note": "لحساب WWR، يجب أن يحتوي الملف على layers بأسماء FACADE و WINDOW",
            "layers_found": dict(sorted(layers.items())),
            "entity_types": dict(sorted(entity_types.items())),
            "total_entities": int(sum(entity_types.values())),
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

    tmp = b64_to_tempfile(b64, ".ifc")
    model = ifcopenshell.open(str(tmp))

    walls = model.by_type("IfcWall") + model.by_type("IfcWallStandardCase")
    wins = model.by_type("IfcWindow")

    def area_of(el) -> float:
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


def analyze_image_features(image_base64: str, style_candidates: Optional[List[str]] = None) -> Dict[str, Any]:
    image_bgr = _b64_to_bgr(image_base64)

    # Optional model hooks
    try:
        from hooks import detect_with_grounding_dino, segment_with_sam2, classify_with_clip
    except Exception:
        try:
            from model_hooks import detect_with_grounding_dino, segment_with_sam2, classify_with_clip
        except Exception:
            detect_with_grounding_dino = lambda _img, _prompts: []  # type: ignore
            segment_with_sam2 = lambda _img, _boxes: None  # type: ignore
            classify_with_clip = lambda _img, _cands: {}  # type: ignore

    dets = detect_with_grounding_dino(image_bgr, TEXT_PROMPTS) or []
    mask = segment_with_sam2(image_bgr, [d.get("bbox") for d in dets if d.get("bbox")])

    H, W = image_bgr.shape[:2]
    wall_area = float(mask.sum()) if (mask is not None and hasattr(mask, "sum")) else float(H * W)

    # crude window area from bboxes labeled window
    window_area = 0.0
    for d in dets:
        if str(d.get("label", "")).lower() == "window":
            x, y, w, h = d.get("bbox", [0, 0, 0, 0])
            window_area += float(max(0, w) * max(0, h))

    wwr_pct = round((window_area / wall_area * 100.0), 2) if wall_area > 0 else 0.0

    palette = extract_palette_kmeans(image_bgr, 6)
    cands = style_candidates or ["coastal_hejazi", "central_najdi"]
    style_scores = classify_with_clip(image_bgr, cands) or {}
    top1 = max(style_scores, key=lambda k: style_scores[k]) if style_scores else (cands[0] if cands else "coastal_hejazi")
    dE = deltaE_to_style_palette(palette, top1)

    # element presence
    labels = [str(d.get("label", "")).lower() for d in dets]
    elements = {
        "roshan": int("roshan" in labels),
        "mashrabiya": int("mashrabiya" in labels),
        "arcade": int("arcade" in labels),
        "lattice": int("lattice" in labels),
    }

    return {
        "wwr_pct": wwr_pct,
        "palette_hex": palette,
        "vision": {"detections": dets, "elements": elements},
        "style_hint": {"top1": top1, "scores": style_scores, "palette_deltaE": dE},
    }
