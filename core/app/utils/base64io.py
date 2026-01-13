from __future__ import annotations

import base64
import tempfile
from pathlib import Path


def b64_to_bytes(b64: str) -> bytes:
    return base64.b64decode(b64)


def b64_to_tempfile(b64: str, suffix: str) -> Path:
    data = b64_to_bytes(b64)
    fd, path = tempfile.mkstemp(suffix=suffix)
    Path(path).write_bytes(data)
    return Path(path)
