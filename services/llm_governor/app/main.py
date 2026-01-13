from __future__ import annotations

import os
import re
import uuid
import math
import hashlib
from typing import Any, List, Dict, Tuple, Optional

import numpy as np
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from sima_shared.db import get_db
from sima_shared import models

# Optional deps (service still runs without them)
try:
    from rank_bm25 import BM25Okapi  # type: ignore
except Exception:  # pragma: no cover
    BM25Okapi = None

try:
    from rapidfuzz.fuzz import token_set_ratio  # type: ignore
except Exception:  # pragma: no cover
    token_set_ratio = None

app = FastAPI(title="llm-governor", version="1.6")


def _tokenize(txt: str) -> List[str]:
    return [t for t in re.split(r"\W+", (txt or "").lower()) if t]


def _local_hash_embedding(text_in: str, dim: int = 1536) -> np.ndarray:
    """Deterministic local embedding (no external model). Good enough to enable vector retrieval + rerank plumbing."""
    toks = _tokenize(text_in)
    if not toks:
        return np.zeros((dim,), dtype=np.float32)

    vec = np.zeros((dim,), dtype=np.float32)
    for t in toks:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        # map first 4 bytes to an index
        idx = int.from_bytes(h[:4], "little") % dim
        val = (int.from_bytes(h[4:8], "little") % 1000) / 1000.0
        vec[idx] += 0.5 + val

    # L2 normalize
    n = float(np.linalg.norm(vec))
    if n > 0:
        vec /= n
    return vec


def _embed(text_in: str) -> np.ndarray:
    """Embedding provider selection.

    - If OPENAI_API_KEY exists and LLM_EMBED_PROVIDER=openai: will try OpenAI embeddings.
    - Otherwise falls back to deterministic local hash embeddings.
    """
    provider = (os.getenv("LLM_EMBED_PROVIDER") or "localhash").lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI()
            model = os.getenv("LLM_EMBED_MODEL") or "text-embedding-3-small"
            resp = client.embeddings.create(model=model, input=text_in)
            emb = np.array(resp.data[0].embedding, dtype=np.float32)
            # normalize
            n = float(np.linalg.norm(emb))
            if n > 0:
                emb /= n
            return emb
        except Exception:
            # hard fallback
            return _local_hash_embedding(text_in)

    return _local_hash_embedding(text_in)


def _chunk_text(text_in: str, max_chars: int = 700, overlap: int = 120) -> List[str]:
    t = (text_in or "").strip()
    if not t:
        return []
    chunks = []
    i = 0
    while i < len(t):
        end = min(len(t), i + max_chars)
        chunks.append(t[i:end])
        if end >= len(t):
            break
        i = max(0, end - overlap)
    return chunks


@app.get("/health")
def health():
    return {
        "ok": True,
        "vector_enabled": bool(models.Vector),
        "bm25_enabled": BM25Okapi is not None,
        "embed_provider": (os.getenv("LLM_EMBED_PROVIDER") or "localhash"),
    }


@app.post("/rag/index")
def rag_index(payload: dict, db: Session = Depends(get_db)):
    """Build / refresh RAG chunks for a guideline_version_id."""
    gv_id = (payload.get("guideline_version_id") or "").strip()
    if not gv_id:
        raise HTTPException(400, "guideline_version_id required")
    force = bool(payload.get("force") or False)

    gv = db.query(models.GuidelineVersion).filter(models.GuidelineVersion.id == gv_id).first()
    if not gv:
        raise HTTPException(404, "guideline_version not found")

    existing = db.query(models.RagChunk).filter(models.RagChunk.guideline_version_id == gv_id).count()
    if existing and not force:
        return {"ok": True, "message": "already_indexed", "chunks": existing}

    if force:
        db.query(models.RagChunk).filter(models.RagChunk.guideline_version_id == gv_id).delete()
        db.commit()

    items = db.query(models.GuideItem).filter(models.GuideItem.guideline_version_id == gv_id).all()
    created = 0
    for it in items:
        for c in _chunk_text(it.text):
            emb = _embed(c)
            ch = models.RagChunk(
                id=str(uuid.uuid4()),
                guideline_version_id=gv_id,
                guide_item_id=it.id,
                ref=it.ref,
                text=c,
                meta={"title": it.title, "tags": it.tags},
                embedding=emb.tolist() if not models.Vector else emb.tolist(),
            )
            db.add(ch)
            created += 1

    db.commit()
    return {"ok": True, "message": "indexed", "chunks": created}


def _vector_search(db: Session, gv_id: str, query_vec: np.ndarray, top_k: int = 20) -> List[Tuple[float, models.RagChunk]]:
    """Returns list of (score, chunk). Score is higher = better."""
    # If pgvector is active, use distance operator. Otherwise, fallback to lexical score.
    if models.Vector:
        # cosine distance: 1 - cosine_similarity; with normalized vectors, cosine distance correlates with <-> if using cosine ops.
        # We'll use <-> which defaults to L2 unless configured; normalized vectors makes L2 distance workable.
        qvec = "[" + ",".join(f"{x:.6f}" for x in query_vec.tolist()) + "]"
        q = text(
            """
            SELECT id, 1.0 / (1.0 + (embedding <-> :qvec::vector)) AS score
            FROM rag_chunks
            WHERE guideline_version_id = :gvid
            ORDER BY embedding <-> :qvec::vector
            LIMIT :k
            """
        )
        rows = db.execute(q, {"qvec": qvec, "gvid": gv_id, "k": top_k}).fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            return []
        chunks = db.query(models.RagChunk).filter(models.RagChunk.id.in_(ids)).all()
        m = {c.id: c for c in chunks}
        out = []
        for rid, score in rows:
            ch = m.get(rid)
            if ch:
                out.append((float(score), ch))
        return out

    # fallback lexical
    toks = set(_tokenize(" ".join(map(str, query_vec[:20]))))
    rows = db.query(models.RagChunk).filter(models.RagChunk.guideline_version_id == gv_id).limit(2000).all()
    out = []
    for ch in rows:
        inter = len(toks & set(_tokenize(ch.text)))
        if inter:
            out.append((float(inter), ch))
    out.sort(key=lambda x: x[0], reverse=True)
    return out[:top_k]


def _rerank(question: str, candidates: List[Tuple[float, models.RagChunk]], top_k: int = 8) -> List[Dict[str, Any]]:
    """Re-rank candidates using BM25/token heuristics. Returns dicts with scores + evidence."""
    if not candidates:
        return []

    q_toks = _tokenize(question)
    docs = [_tokenize(ch.text) for _, ch in candidates]
    bm25_scores = None
    if BM25Okapi is not None:
        try:
            bm = BM25Okapi(docs)
            bm25_scores = bm.get_scores(q_toks)
        except Exception:
            bm25_scores = None

    ranked = []
    for idx, (sim_score, ch) in enumerate(candidates):
        bm25 = float(bm25_scores[idx]) if bm25_scores is not None else 0.0
        fuzz = float(token_set_ratio(question, ch.text[:800])) / 100.0 if token_set_ratio else 0.0
        # Final: weight semantic + bm25 + fuzz
        final = (0.55 * float(sim_score)) + (0.30 * bm25) + (0.15 * fuzz)
        ranked.append({
            "final": final,
            "sim": float(sim_score),
            "bm25": bm25,
            "fuzz": fuzz,
            "ref": ch.ref,
            "chunk_id": ch.id,
            "text": ch.text,
            "meta": ch.meta or {},
        })

    ranked.sort(key=lambda d: d["final"], reverse=True)
    return ranked[:top_k]


@app.post("/rag/query")
def rag_query(payload: dict, db: Session = Depends(get_db)):
    gv_id = (payload.get("guideline_version_id") or "").strip()
    q = (payload.get("query") or "").strip()
    top_k = int(payload.get("top_k") or 10)
    if not gv_id or not q:
        raise HTTPException(400, "guideline_version_id and query required")

    vec = _embed(q)
    candidates = _vector_search(db, gv_id, vec, top_k=max(20, top_k))
    reranked = _rerank(q, candidates, top_k=top_k)
    return {"ok": True, "results": [
        {"ref": r["ref"], "score": r["final"], "sim": r["sim"], "bm25": r["bm25"], "text": r["text"][:500]}
        for r in reranked
    ]}


@app.post("/ask")
def ask(payload: dict, db: Session = Depends(get_db)):
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "question required")

    # Choose guideline version
    gv_id = (payload.get("guideline_version_id") or "").strip()
    if not gv_id:
        # latest
        gv = db.query(models.GuidelineVersion).order_by(models.GuidelineVersion.created_at.desc()).first()
        if not gv:
            raise HTTPException(409, "no guideline versions indexed")
        gv_id = gv.id

    # Ensure chunks exist
    chunk_count = db.query(models.RagChunk).filter(models.RagChunk.guideline_version_id == gv_id).count()
    if chunk_count == 0:
        return {
            "answer": "لا أستطيع الإجابة لأن الموجهات لم تُفهرس بعد (RAG index غير موجود). شغّل /rag/index أولاً.",
            "citations": [],
            "mode": "refuse_no_index",
        }

    vec = _embed(question)
    candidates = _vector_search(db, gv_id, vec, top_k=30)
    reranked = _rerank(question, candidates, top_k=8)
    if not reranked:
        return {
            "answer": "لا أستطيع الإجابة لأن السؤال لا يملك أدلة كافية من الموجهات المستوردة.",
            "citations": [],
            "mode": "refuse_no_evidence",
        }

    # Strict mode: answer is extractive synthesis only (no free-form claims)
    used = reranked[:3]
    snippets = [u["text"].strip()[:450] for u in used]
    citations = [{"ref": u["ref"], "chunk_id": u["chunk_id"], "score": u["final"]} for u in used]
    answer = " ".join(snippets)

    explain = {
        "guideline_version_id": gv_id,
        "retrieval_top": [
            {"ref": u["ref"], "sim": u["sim"], "bm25": u["bm25"], "fuzz": u["fuzz"], "final": u["final"], "preview": u["text"][:220]}
            for u in reranked
        ],
        "policy": {
            "mode": "extractive_rag",
            "no_hallucination": True,
            "answer_claims": "Only supported by retrieved chunks; otherwise refuse",
        }
    }

    run = models.ChatRun(
        id=str(uuid.uuid4()),
        question=question,
        mode="rag",
        answer=answer,
        evidence=explain,
    )
    db.add(run)
    db.commit()

    return {"answer": answer, "citations": citations, "mode": "extractive_rag", "explain": explain, "chat_run_id": run.id}
