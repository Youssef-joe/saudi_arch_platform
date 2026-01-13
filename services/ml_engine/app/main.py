from __future__ import annotations

import os
import math
from typing import Any, Dict, List, Tuple

import numpy as np
import cv2
from fastapi import FastAPI, UploadFile, File


app = FastAPI(title="ml-engine", version="1.6")


def _decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("invalid image")
    return img


def _a_hash(gray: np.ndarray, size: int = 16) -> str:
    """Simple average hash for near-duplicate detection."""
    g = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    mean = float(g.mean())
    bits = (g > mean).astype(np.uint8).flatten()
    # convert bits to hex string
    out = 0
    s = []
    for i, b in enumerate(bits):
        out = (out << 1) | int(b)
        if (i + 1) % 4 == 0:
            s.append(format(out, "x"))
            out = 0
    return "".join(s)


def _hamming_hex(a: str, b: str) -> int:
    la = int(a, 16)
    lb = int(b, 16)
    return int((la ^ lb).bit_count())


def _fallback_openings(gray: np.ndarray) -> Tuple[List[Dict[str, int]], float]:
    """Fallback heuristic: edges+contours -> boxes + estimated opening ratio."""
    h, w = gray.shape[:2]
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 160)
    edges = cv2.dilate(edges, None, iterations=1)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: List[Dict[str, int]] = []
    area_sum = 0
    for c in cnts:
        x, y, ww, hh = cv2.boundingRect(c)
        area = ww * hh
        if area < (w * h) * 0.0006:
            continue
        if ww < 8 or hh < 8:
            continue
        boxes.append({"x": int(x), "y": int(y), "w": int(ww), "h": int(hh)})
        area_sum += area
        if len(boxes) >= 80:
            break
    opening_ratio = float(area_sum) / float(w * h) if w * h else 0.0
    boxes = sorted(boxes, key=lambda b: b["w"] * b["h"], reverse=True)[:50]
    return boxes, opening_ratio


def _dominant_colors(img_bgr: np.ndarray) -> List[Dict[str, Any]]:
    """Very light k-means (k=3) on downsampled pixels."""
    small = cv2.resize(img_bgr, (160, 160), interpolation=cv2.INTER_AREA)
    data = small.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
    K = 3
    _, labels, centers = cv2.kmeans(data, K, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=K)
    total = float(counts.sum()) if counts.sum() else 1.0
    out = []
    for i in range(K):
        b, g, r = centers[i]
        out.append({
            "rgb": [int(r), int(g), int(b)],
            "share": float(counts[i]) / total,
        })
    out.sort(key=lambda x: x["share"], reverse=True)
    return out


@app.post("/facade/segment")
async def facade_segment(image: UploadFile = File(...)):
    """Returns detected opening boxes + lightweight mask proxy.

    Note: This is a fallback heuristic. For national-grade accuracy you will plug in a
    trained segmentation model (e.g., SAM-assisted fine-tuning).
    """
    data = await image.read()
    img = _decode_image(data)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    boxes, opening_ratio = _fallback_openings(gray)
    return {
        "ok": True,
        "method": "fallback_edges",
        "boxes": boxes,
        "opening_ratio_est": opening_ratio,
    }


@app.post("/facade/metrics")
async def facade_metrics(image: UploadFile = File(...)):
    """Computes facade metrics that can feed risk scoring / compliance hints."""
    data = await image.read()
    img = _decode_image(data)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    boxes, opening_ratio = _fallback_openings(gray)
    colors = _dominant_colors(img)

    # Rhythm proxy: variance of x-centroids spacing
    centroids = sorted([b["x"] + b["w"] / 2.0 for b in boxes])
    spacings = [centroids[i + 1] - centroids[i] for i in range(len(centroids) - 1)]
    rhythm = float(np.std(spacings)) if spacings else 0.0

    return {
        "ok": True,
        "opening_ratio_est": opening_ratio,
        "window_count_est": len(boxes),
        "rhythm_sigma_px": rhythm,
        "dominant_colors": colors,
        "note": "National accuracy requires trained segmentation + calibrated measurement rules.",
    }


@app.post("/image/similarity")
async def image_similarity(a: UploadFile = File(...), b: UploadFile = File(...)):
    """Near-duplicate similarity (helps detect copy/paste facades)."""
    ia = _decode_image(await a.read())
    ib = _decode_image(await b.read())
    ga = cv2.cvtColor(ia, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(ib, cv2.COLOR_BGR2GRAY)
    ha = _a_hash(ga)
    hb = _a_hash(gb)
    dist = _hamming_hex(ha, hb)
    # normalize: 0..1
    max_bits = 16 * 16
    score = 1.0 - (float(dist) / float(max_bits))
    return {"ok": True, "score": score, "hash_a": ha, "hash_b": hb, "hamming": dist}


@app.post("/risk/facade")
async def facade_risk(image: UploadFile = File(...)):
    """Risk scoring placeholder: combines metrics into a normalized risk [0..1]."""
    img = _decode_image(await image.read())
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    boxes, opening_ratio = _fallback_openings(gray)
    # Heuristic: too many tiny boxes => noisy; too high/low opening ratio => risk
    count = len(boxes)
    ratio_risk = min(1.0, abs(opening_ratio - 0.22) / 0.22)  # expected center ~0.22 (example)
    count_risk = min(1.0, max(0.0, (count - 25) / 60.0))
    risk = 0.65 * ratio_risk + 0.35 * count_risk
    return {
        "ok": True,
        "risk": float(max(0.0, min(1.0, risk))),
        "features": {"opening_ratio_est": opening_ratio, "window_count_est": count},
        "note": "Replace heuristic with trained segmentation + region/style calibrated thresholds.",
    }
