"""heal_runs 存储（TECH §9.3，与 jobs.db 同库）。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.config import JOBS_DB, REPO_ROOT

HEAL_FIX_DIR = REPO_ROOT / "heal" / "fix-runs"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def init_heal_db(db_path: Path = JOBS_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    HEAL_FIX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS heal_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            prd_id TEXT NOT NULL,
            status TEXT NOT NULL,
            iteration INTEGER DEFAULT 0,
            max_iterations INTEGER DEFAULT 3,
            token_cost REAL DEFAULT 0,
            token_limit REAL,
            wall_clock_sec INTEGER DEFAULT 900,
            abort_reason TEXT,
            diagnosis_json TEXT,
            fix_plan_json TEXT,
            patch_dir TEXT,
            parent_job_id TEXT,
            created_at TEXT NOT NULL,
            finished_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def create_heal_run(
    project_id: str,
    prd_id: str,
    *,
    max_iterations: int = 3,
    token_limit: float = 50000,
    wall_clock_sec: int = 900,
    parent_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    init_heal_db()
    run_id = uuid.uuid4().hex
    patch_dir = HEAL_FIX_DIR / run_id
    patch_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.execute(
        """
        INSERT INTO heal_runs
        (id, project_id, prd_id, status, iteration, max_iterations,
         token_cost, token_limit, wall_clock_sec, patch_dir, parent_job_id, created_at)
        VALUES (?, ?, ?, 'RUNNING', 0, ?, 0, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            project_id,
            prd_id,
            max_iterations,
            token_limit,
            wall_clock_sec,
            str(patch_dir),
            parent_job_id,
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    row = get_heal_run(run_id)
    assert row is not None
    return row


def update_heal_run(run_id: str, **fields: Any) -> None:
    init_heal_db()
    if not fields:
        return
    cols = []
    vals: List[Any] = []
    for k, v in fields.items():
        if k in ("diagnosis_json", "fix_plan_json") and isinstance(v, dict):
            v = json.dumps(v, ensure_ascii=False)
        cols.append(f"{k} = ?")
        vals.append(v)
    vals.append(run_id)
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.execute(f"UPDATE heal_runs SET {', '.join(cols)} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_heal_run(run_id: str) -> Optional[Dict[str, Any]]:
    init_heal_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM heal_runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    return _row_to_run(row) if row else None


def list_heal_runs(project_id: str, prd_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    init_heal_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    if prd_id:
        rows = conn.execute(
            "SELECT * FROM heal_runs WHERE project_id=? AND prd_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, prd_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM heal_runs WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
    conn.close()
    return [_row_to_run(r) for r in rows]


def read_patch_preview(run_id: str) -> str:
    run = get_heal_run(run_id)
    if not run or not run.get("patch_dir"):
        return ""
    patch_dir = Path(run["patch_dir"])
    parts: List[str] = []
    for p in sorted(patch_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(patch_dir)
            parts.append(f"--- {rel} ---\n{p.read_text(encoding='utf-8', errors='replace')}\n")
    return "\n".join(parts) if parts else "（无补丁预览）"


def _row_to_run(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    for key in ("diagnosis_json", "fix_plan_json"):
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except json.JSONDecodeError:
                pass
    return d
