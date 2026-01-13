from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "sima.db"

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              token TEXT UNIQUE NOT NULL,
              created_at TEXT NOT NULL,
              project_json TEXT,
              pattern_code TEXT,
              features_json TEXT,
              evaluation_json TEXT
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_token ON evaluations(token);")
        conn.commit()

def insert_evaluation(
    *,
    token: str,
    created_at: str,
    project: Dict[str, Any],
    pattern_code: Optional[str],
    features: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO evaluations(token, created_at, project_json, pattern_code, features_json, evaluation_json)
            VALUES(?,?,?,?,?,?)
            """,
            (
                token,
                created_at,
                json.dumps(project, ensure_ascii=False),
                pattern_code,
                json.dumps(features, ensure_ascii=False),
                json.dumps(evaluation, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)

def get_evaluation_by_id(evaluation_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM evaluations WHERE id = ?", (evaluation_id,)).fetchone()
        if not row:
            return None
        return _row_to_obj(row)

def get_evaluation_by_token(token: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM evaluations WHERE token = ?", (token,)).fetchone()
        if not row:
            return None
        return _row_to_obj(row)

def _row_to_obj(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": int(row["id"]),
        "token": row["token"],
        "created_at": row["created_at"],
        "pattern_code": row["pattern_code"],
        "project": json.loads(row["project_json"] or "{}"),
        "features": json.loads(row["features_json"] or "{}"),
        "evaluation": json.loads(row["evaluation_json"] or "{}"),
    }
