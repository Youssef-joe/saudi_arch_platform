from typing import List, Dict
from pypdf import PdfReader
import io, re

def pdf_to_items(pdf_bytes: bytes, ref_prefix: str) -> List[Dict]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    items=[]
    for pi, page in enumerate(reader.pages):
        txt = (page.extract_text() or "").strip()
        if not txt: 
            continue
        # Split into blocks by double newlines
        blocks = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
        for bi, b in enumerate(blocks[:200]):
            items.append({
                "ref": f"{ref_prefix}#p={pi+1}&b={bi+1}",
                "title": None,
                "text": b,
                "tags": {"page": pi+1, "enforceable": True},
            })
    return items
