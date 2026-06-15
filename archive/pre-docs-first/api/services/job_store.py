"""pipeline_jobs SQLite 存储"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.config import JOBS_DB, LOGS_DIR


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def init_jobs_db(db_path: Path = JOBS_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            id           TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL,
            command      TEXT NOT NULL,
            args_json    TEXT,
            status       TEXT NOT NULL,
            created_at   TEXT NOT NULL,
            started_at   TEXT,
            finished_at  TEXT,
            exit_code    INTEGER,
            log_path     TEXT
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status "
        "ON pipeline_jobs(status, created_at)"
    )
    conn.commit()
    conn.close()


def create_job(project_id: str, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
    init_jobs_db()
    job_id = uuid.uuid4().hex
    log_path = LOGS_DIR / f"{job_id}.log"
    conn = sqlite3.connect(JOBS_DB)
    conn.execute(
        """
        INSERT INTO pipeline_jobs
        (id, project_id, command, args_json, status, created_at, log_path)
        VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
        """,
        (job_id, project_id, command, json.dumps(args), _now(), str(log_path)),
    )
    conn.commit()
    conn.close()
    return get_job(job_id)


def pick_next_pending() -> Optional[Dict[str, Any]]:
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT * FROM pipeline_jobs
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    return _row_to_job(row) if row else None


def update_job_status(
    job_id: str,
    status: str,
    *,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    exit_code: Optional[int] = None,
) -> None:
    conn = sqlite3.connect(JOBS_DB)
    fields = ["status = ?"]
    values: List[Any] = [status]
    if started_at is not None:
        fields.append("started_at = ?")
        values.append(started_at)
    if finished_at is not None:
        fields.append("finished_at = ?")
        values.append(finished_at)
    if exit_code is not None:
        fields.append("exit_code = ?")
        values.append(exit_code)
    values.append(job_id)
    conn.execute(
        f"UPDATE pipeline_jobs SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)
    ).fetchone()
    conn.close()
    return _row_to_job(row) if row else None


def list_jobs(project_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB)
    conn.row_factory = sqlite3.Row
    if project_id:
        rows = conn.execute(
            """
            SELECT * FROM pipeline_jobs
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (project_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM pipeline_jobs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    conn.close()
    return [_row_to_job(r) for r in rows]


def recover_stale_running_jobs() -> int:
    """API 重启时将遗留 RUNNING 标为 FAILED，避免队列死锁。"""
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB)
    cur = conn.execute(
        """
        UPDATE pipeline_jobs
        SET status = 'FAILED', finished_at = ?, exit_code = 1
        WHERE status = 'RUNNING'
        """,
        (_now(),),
    )
    conn.commit()
    count = cur.rowcount
    conn.close()
    return count


def read_job_log(job_id: str, tail: int = 500) -> str:
    job = get_job(job_id)
    if not job or not job.get("log_path"):
        return ""
    log_path = Path(job["log_path"])
    if not log_path.exists():
        return ""
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > tail:
        return "\n".join(lines[-tail:])
    return text


def _row_to_job(row: sqlite3.Row) -> Dict[str, Any]:
    args = {}
    if row["args_json"]:
        try:
            args = json.loads(row["args_json"])
        except json.JSONDecodeError:
            args = {}
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "command": row["command"],
        "args": args,
        "status": row["status"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "exit_code": row["exit_code"],
        "log_path": row["log_path"],
    }
