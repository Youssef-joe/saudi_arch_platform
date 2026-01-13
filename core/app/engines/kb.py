from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_kb(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # normalize: v3 is dict {entries:[...]}
    if isinstance(data, dict) and "entries" in data:
        entries = data["entries"]
    elif isinstance(data, list):
        entries = data
    else:
        entries = []
    return {"raw": data, "entries": entries}


def kb_by_pattern(kb: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for e in kb.get("entries", []):
        code = e.get("pattern_code")
        if code:
            out[str(code)] = e
    return out
