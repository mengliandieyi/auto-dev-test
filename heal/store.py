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


def _parse_ts(value: str) -> datetime:
    text = (value or "").strip().replace(" UTC", "")
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


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


def recover_stale_heal_runs() -> int:
    """将遗留 RUNNING 记录标为终态（分析完成 / 超时孤儿）。"""
    init_heal_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM heal_runs WHERE status = 'RUNNING'").fetchall()
    conn.close()
    now = datetime.now(timezone.utc)
    updated = 0
    for row in rows:
        run_id = row["id"]
        created = _parse_ts(row["created_at"])
        age_sec = (now - created).total_seconds()
        wall_sec = int(row["wall_clock_sec"] or 900)
        has_diagnosis = bool(row["diagnosis_json"])

        if has_diagnosis:
            update_heal_run(
                run_id,
                status="ANALYZED",
                finished_at=row["finished_at"] or _now(),
            )
            updated += 1
            continue

        if age_sec > wall_sec + 120:
            update_heal_run(
                run_id,
                status="ABORTED",
                abort_reason="STALE",
                finished_at=_now(),
            )
            updated += 1
    return updated


def prune_heal_runs(
    *,
    keep: int = 50,
    project_id: Optional[str] = None,
    prd_id: Optional[str] = None,
) -> int:
    """删除较早的终态 heal 记录，保留最近 keep 条（不删 RUNNING）。"""
    init_heal_db()
    keep = max(1, min(int(keep), 500))
    terminal = frozenset({"SUCCESS", "FAILED", "ABORTED", "ANALYZED"})
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    if project_id and prd_id:
        rows = conn.execute(
            "SELECT id, status, patch_dir FROM heal_runs WHERE project_id=? AND prd_id=? ORDER BY created_at DESC",
            (project_id, prd_id),
        ).fetchall()
    elif project_id:
        rows = conn.execute(
            "SELECT id, status, patch_dir FROM heal_runs WHERE project_id=? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, status, patch_dir FROM heal_runs ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    if len(rows) <= keep:
        return 0
    to_delete = [r for r in rows[keep:] if r["status"] in terminal]
    if not to_delete:
        return 0
    ids = [r["id"] for r in to_delete]
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM heal_runs WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()
    import shutil

    for r in to_delete:
        patch_dir = r["patch_dir"]
        if patch_dir:
            try:
                shutil.rmtree(patch_dir, ignore_errors=True)
            except OSError:
                pass
    return len(ids)


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
