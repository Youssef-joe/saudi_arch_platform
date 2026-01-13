from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

import requests


_ALLOWED_HOSTS = {
    "architsaudi.dasc.gov.sa",
}


@dataclass
class FetchedFile:
    url: str
    path: Path
    content_type: str
    size_bytes: int


_RE_BAD = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    name = (name or "file").strip()
    name = unquote(name)
    name = name.split("/")[-1]
    name = _RE_BAD.sub("_", name)
    name = name.strip("_") or "file"
    # keep it short-ish
    return name[:180]


def fetch_to_file(
    url: str,
    out_dir: Path,
    *,
    timeout_s: int = 45,
    max_bytes: int = 50 * 1024 * 1024,
    filename: Optional[str] = None,
) -> FetchedFile:
    """Download a remote file into out_dir with basic safety checks."""

    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("Only http/https URLs are allowed")

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise ValueError(f"Host not allowed: {host}")

    out_dir.mkdir(parents=True, exist_ok=True)

    fn = filename
    if not fn:
        fn = _safe_filename(Path(parsed.path).name or "guidelines.pdf")

    # Force .pdf extension when possible
    if not fn.lower().endswith(".pdf"):
        fn = f"{fn}.pdf"

    headers = {
        "User-Agent": "Mozilla/5.0 (SimaAI/0.4; +https://architsaudi.dasc.gov.sa)",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }

    r = requests.get(url, headers=headers, timeout=timeout_s, stream=True)
    r.raise_for_status()

    ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()

    out_path = out_dir / fn
    size = 0
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("File too large")
            f.write(chunk)

    return FetchedFile(url=url, path=out_path, content_type=ctype, size_bytes=size)
