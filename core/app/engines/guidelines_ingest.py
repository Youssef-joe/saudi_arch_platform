from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExtractedSnippet:
    page: int
    text: str


@dataclass
class SuggestedRule:
    """A machine-suggested rule candidate extracted from guideline PDFs.

    This is intentionally conservative: it surfaces *evidence snippets* with
    detected numeric constraints, but does not auto-enforce them without human
    confirmation.
    """

    category: str
    title: str
    snippets: List[ExtractedSnippet]
    detected_numbers: List[str]


_RE_PERCENT = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*%\b")
_RE_METERS = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*(?:م|متر|meter|meters)\b", re.IGNORECASE)
_RE_FLOORS = re.compile(r"\b(\d{1,2})\s*(?:طابق|أدوار|storey|stories|floors?)\b", re.IGNORECASE)
_RE_RANGE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s*[-–—]\s*(\d{1,3}(?:\.\d+)?)\b")


_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "openings": (
        "فتحات",
        "نوافذ",
        "wwr",
        "window",
        "opening",
        "نسبة",
        "واجهة",
    ),
    "height_mass": ("ارتفاع", "طابق", "أدوار", "mass", "massing", "height"),
    "materials": ("مواد", "جص", "الجص", "plaster", "coral", "مرجاني", "خشب", "wood"),
    "shading": ("ظل", "ظلال", "تظليل", "shading", "مشربية", "mashrabiya", "روشان", "roshan"),
    "entries": ("مدخل", "مداخل", "entrance", "portal"),
    "courtyard_arcades": ("فناء", "أفنية", "أروقة", "arcade", "رواق", "courtyard"),
}


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def extract_pdf_text_pages(pdf_path: Path, *, max_pages: Optional[int] = None) -> List[ExtractedSnippet]:
    """Extract text per page using pdfplumber.

    We keep page granularity because it is essential for evidence traceability.
    """

    import pdfplumber  # installed in this environment

    snippets: List[ExtractedSnippet] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        total = len(pdf.pages)
        n = total if max_pages is None else min(total, max_pages)
        for i in range(n):
            text = pdf.pages[i].extract_text() or ""
            text = _normalize_ws(text)
            if text:
                snippets.append(ExtractedSnippet(page=i + 1, text=text))
    return snippets


def _detect_numbers(text: str) -> List[str]:
    nums: List[str] = []
    nums += [m.group(0) for m in _RE_PERCENT.finditer(text)]
    nums += [m.group(0) for m in _RE_METERS.finditer(text)]
    nums += [m.group(0) for m in _RE_FLOORS.finditer(text)]
    nums += [m.group(0) for m in _RE_RANGE.finditer(text)]
    # de-dup while preserving order
    seen = set()
    out: List[str] = []
    for n in nums:
        if n not in seen:
            out.append(n)
            seen.add(n)
    return out


def suggest_rules_from_guidelines(pages: List[ExtractedSnippet]) -> List[SuggestedRule]:
    """Heuristically propose rule candidates from text pages.

    Strategy:
      - Look for paragraphs containing BOTH a keyword and a numeric constraint.
      - Group findings into coarse categories to seed the G2C Rule DSL.
    """

    buckets: Dict[str, List[ExtractedSnippet]] = {k: [] for k in _KEYWORDS}
    bucket_nums: Dict[str, List[str]] = {k: [] for k in _KEYWORDS}

    for snip in pages:
        t = snip.text.lower()
        nums = _detect_numbers(snip.text)
        if not nums:
            continue
        for cat, kws in _KEYWORDS.items():
            if any(kw.lower() in t for kw in kws):
                buckets[cat].append(snip)
                bucket_nums[cat].extend(nums)

    suggestions: List[SuggestedRule] = []
    for cat, snips in buckets.items():
        if not snips:
            continue
        nums = []
        seen = set()
        for n in bucket_nums[cat]:
            if n not in seen:
                nums.append(n)
                seen.add(n)

        # Keep only the top few snippets to avoid huge payloads
        top = snips[:12]
        title = {
            "openings": "Openings / WWR constraints",
            "height_mass": "Height / massing constraints",
            "materials": "Materials / finishes constraints",
            "shading": "Shading / screens constraints",
            "entries": "Entries / portals constraints",
            "courtyard_arcades": "Courtyards / arcades constraints",
        }.get(cat, cat)
        suggestions.append(
            SuggestedRule(
                category=cat,
                title=title,
                snippets=top,
                detected_numbers=nums,
            )
        )

    return suggestions


def write_suggestions_json(suggestions: List[SuggestedRule]) -> List[Dict[str, Any]]:
    """Return JSON-serializable representation."""

    out: List[Dict[str, Any]] = []
    for s in suggestions:
        out.append(
            {
                "category": s.category,
                "title": s.title,
                "detected_numbers": s.detected_numbers,
                "snippets": [{"page": x.page, "text": x.text} for x in s.snippets],
            }
        )
    return out
