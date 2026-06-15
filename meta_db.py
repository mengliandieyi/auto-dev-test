"""SQLite 元数据：按项目隔离（tests/generated/{project_id}/meta.db）"""

from __future__ import annotations

import sqlite3
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).parent
LEGACY_DB = ROOT / "tests" / "generated" / "meta.db"


def db_path_for_project(project_id: str) -> Path:
    return ROOT / "tests" / "generated" / project_id / "meta.db"


def init_db(db_path: Optional[Path] = None) -> None:
    db_path = db_path or LEGACY_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generated_specs (
            project_id     TEXT NOT NULL,
            prd_id         TEXT NOT NULL,
            layer          TEXT NOT NULL DEFAULT 'e2e',
            prd_version    TEXT NOT NULL,
            spec_file      TEXT NOT NULL,
            generated_at   TEXT NOT NULL,
            criteria_count INTEGER DEFAULT 0,
            covered_count  INTEGER DEFAULT 0,
            PRIMARY KEY (project_id, prd_id, layer)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS archived_specs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id   TEXT,
            prd_id       TEXT,
            prd_version  TEXT,
            layer        TEXT,
            archive_path TEXT,
            archived_at  TEXT
        )
    """)
    _migrate_legacy_schema(conn)
    conn.commit()
    conn.close()


def ensure_project_db(project_id: str) -> Path:
    """返回项目 meta.db 路径；若存在旧版全局库则迁移本项目行。"""
    path = db_path_for_project(project_id)
    init_db(path)
    if LEGACY_DB.exists() and path != LEGACY_DB:
        _migrate_rows_from_legacy(LEGACY_DB, path, project_id)
    return path


def _migrate_rows_from_legacy(legacy: Path, target: Path, project_id: str) -> None:
    src = sqlite3.connect(legacy)
    dst = sqlite3.connect(target)
    rows = src.execute(
        "SELECT project_id, prd_id, layer, prd_version, spec_file, generated_at, "
        "criteria_count, covered_count FROM generated_specs WHERE project_id=?",
        (project_id,),
    ).fetchall()
    for row in rows:
        dst.execute(
            """
            INSERT OR IGNORE INTO generated_specs VALUES (?,?,?,?,?,?,?,?)
            """,
            row,
        )
    dst.commit()
    src.close()
    dst.close()


def _migrate_legacy_schema(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(generated_specs)")}
    if not cols or "layer" in cols:
        return
    conn.execute("ALTER TABLE generated_specs RENAME TO generated_specs_old")
    conn.execute("""
        CREATE TABLE generated_specs (
            project_id     TEXT NOT NULL,
            prd_id         TEXT NOT NULL,
            layer          TEXT NOT NULL DEFAULT 'e2e',
            prd_version    TEXT NOT NULL,
            spec_file      TEXT NOT NULL,
            generated_at   TEXT NOT NULL,
            criteria_count INTEGER DEFAULT 0,
            covered_count  INTEGER DEFAULT 0,
            PRIMARY KEY (project_id, prd_id, layer)
        )
    """)
    conn.execute("""
        INSERT INTO generated_specs
        SELECT project_id, prd_id, 'e2e', prd_version, spec_file,
               generated_at, criteria_count, covered_count
        FROM generated_specs_old
    """)
    conn.execute("DROP TABLE generated_specs_old")


def get_existing_record(
    db_path: Path, project_id: str, prd_id: str, layer: str
) -> Optional[Dict]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT * FROM generated_specs WHERE project_id=? AND prd_id=? AND layer=?",
        (project_id, prd_id, layer),
    ).fetchone()
    conn.close()
    if not row:
        return None
    cols = [
        "project_id", "prd_id", "layer", "prd_version", "spec_file",
        "generated_at", "criteria_count", "covered_count",
    ]
    return dict(zip(cols, row))


def upsert_record(db_path: Path, record: dict) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT OR REPLACE INTO generated_specs
        (project_id, prd_id, layer, prd_version, spec_file, generated_at,
         criteria_count, covered_count)
        VALUES (:project_id, :prd_id, :layer, :prd_version, :spec_file,
                :generated_at, :criteria_count, :covered_count)
    """, record)
    conn.commit()
    conn.close()


def archive_old_spec(
    db_path: Path, record: dict, old_spec_path: Path, ext: str = ".spec.ts"
) -> None:
    archive_dir = ROOT / "tests" / "archive" / record["project_id"]
    archive_dir.mkdir(parents=True, exist_ok=True)
    layer = record.get("layer", "e2e")
    archive_name = (
        f"{record['prd_id']}_v{record['prd_version']}_{layer}_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    )
    archive_path = archive_dir / archive_name
    if old_spec_path.exists():
        shutil.move(str(old_spec_path), str(archive_path))
        print(f"  📦 旧版本已归档：{archive_path.relative_to(ROOT)}")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO archived_specs
        (project_id, prd_id, prd_version, layer, archive_path, archived_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        record["project_id"], record["prd_id"], record["prd_version"],
        layer, str(archive_path), datetime.now(timezone.utc).isoformat(),
    ))
    conn.commit()
    conn.close()
