"""pipeline_jobs SQLite 存储"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.config import JOBS_DB, LOGS_DIR, LOG_TAIL_MAX_BYTES


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def init_jobs_db(db_path: Path = JOBS_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
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
    cols = {r[1] for r in conn.execute("PRAGMA table_info(pipeline_jobs)")}
    if "events_json" not in cols:
        conn.execute("ALTER TABLE pipeline_jobs ADD COLUMN events_json TEXT")
    conn.commit()
    conn.close()
    try:
        from heal.store import init_heal_db

        init_heal_db(db_path)
    except ImportError:
        pass


def create_job(project_id: str, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
    init_jobs_db()
    job_id = uuid.uuid4().hex
    log_path = LOGS_DIR / f"{job_id}.log"
    conn = sqlite3.connect(JOBS_DB, timeout=30)
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
    job = get_job(job_id)
    assert job is not None
    return job


def pick_next_pending() -> Optional[Dict[str, Any]]:
    """原子领取：PENDING → RUNNING，避免 worker 重复拾取。"""
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT * FROM pipeline_jobs
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            conn.commit()
            return None
        conn.execute(
            "UPDATE pipeline_jobs SET status = 'RUNNING', started_at = ? WHERE id = ?",
            (_now(), row["id"]),
        )
        conn.commit()
        return _row_to_job(row)
    finally:
        conn.close()


def update_job_status(
    job_id: str,
    status: str,
    *,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    exit_code: Optional[int] = None,
) -> None:
    conn = sqlite3.connect(JOBS_DB, timeout=30)
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
    conn.execute(f"UPDATE pipeline_jobs SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return _row_to_job(row) if row else None


def list_jobs(project_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
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
            "SELECT * FROM pipeline_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [_row_to_job(r) for r in rows]


def recover_stale_running_jobs() -> int:
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
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


def prune_jobs(*, keep: int = 100, project_id: Optional[str] = None) -> int:
    """删除较早的终态任务记录，保留最近 keep 条（不删 PENDING/RUNNING）。"""
    init_jobs_db()
    keep = max(1, min(int(keep), 1000))
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    if project_id:
        rows = conn.execute(
            "SELECT id, log_path, status FROM pipeline_jobs WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, log_path, status FROM pipeline_jobs ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    if len(rows) <= keep:
        return 0
    terminal = {"SUCCESS", "FAILED", "CANCELLED"}
    to_delete = [r for r in rows[keep:] if r["status"] in terminal]
    if not to_delete:
        return 0
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    ids = [r["id"] for r in to_delete]
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM pipeline_jobs WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()
    for r in to_delete:
        log_path = r["log_path"]
        if log_path:
            try:
                Path(log_path).unlink(missing_ok=True)
            except OSError:
                pass
    return len(ids)


def try_mark_cancelled(job_id: str) -> bool:
    """将 PENDING / RUNNING 任务标为 CANCELLED；已为终态则返回 False。"""
    init_jobs_db()
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        conn.close()
        return False
    if row["status"] not in ("PENDING", "RUNNING"):
        conn.close()
        return False
    conn.execute(
        "UPDATE pipeline_jobs SET status = 'CANCELLED', finished_at = ?, exit_code = -1 WHERE id = ?",
        (_now(), job_id),
    )
    conn.commit()
    conn.close()
    return True


def append_job_log(job_id: str, message: str) -> None:
    job = get_job(job_id)
    if not job or not job.get("log_path"):
        return
    log_path = Path(job["log_path"])
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(message if message.endswith("\n") else message + "\n")


def read_job_log_tail(job_id: str) -> str:
    job = get_job(job_id)
    if not job or not job.get("log_path"):
        return ""
    log_path = Path(job["log_path"])
    if not log_path.exists():
        return ""
    data = log_path.read_bytes()
    if len(data) > LOG_TAIL_MAX_BYTES:
        data = data[-LOG_TAIL_MAX_BYTES:]
    return data.decode("utf-8", errors="replace")


def _read_job_log_full(job_id: str) -> str:
    job = get_job(job_id)
    if not job or not job.get("log_path"):
        return ""
    log_path = Path(job["log_path"])
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8", errors="replace")


def sync_job_events(job_id: str) -> list[dict[str, Any]]:
    """从完整日志解析 job-event 并持久化（避免 log_tail 截断丢失）。"""
    from job_events import parse_job_events

    events = parse_job_events(_read_job_log_full(job_id))
    conn = sqlite3.connect(JOBS_DB, timeout=30)
    conn.execute(
        "UPDATE pipeline_jobs SET events_json = ? WHERE id = ?",
        (json.dumps(events, ensure_ascii=False), job_id),
    )
    conn.commit()
    conn.close()
    return events


def read_job_events(job_id: str) -> list[dict[str, Any]]:
    job = get_job(job_id)
    if not job:
        return []
    raw = job.get("events_json")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    events = sync_job_events(job_id)
    return events


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
        "events_json": row["events_json"] if "events_json" in row.keys() else None,
    }
