"""追溯报告历史归档与读取。"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent
SNAPSHOT_RE = re.compile(r"^\d{8}T\d{6}Z$")


def _history_dir(project_id: str, prd_id: str) -> Path:
    return ROOT / "reports" / project_id / "history" / prd_id


def _final_path(project_id: str, prd_id: str) -> Path:
    return ROOT / "reports" / project_id / f"{prd_id}_traceability.txt"


def _snapshot_from_mtime(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.strftime("%Y%m%dT%H%M%SZ")


def archive_final_report(project_id: str, prd_id: str) -> None:
    """写入新 final 报告前，将当前版本移入 history/。"""
    final = _final_path(project_id, prd_id)
    if not final.is_file() or final.is_symlink():
        return
    hist = _history_dir(project_id, prd_id)
    hist.mkdir(parents=True, exist_ok=True)
    snapshot = _snapshot_from_mtime(final)
    dest = hist / f"{snapshot}_traceability.txt"
    if dest.exists():
        return
    shutil.copy2(final, dest)


def list_traceability_history(project_id: str, prd_id: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    final = _final_path(project_id, prd_id)
    if final.is_file() and not final.is_symlink():
        mtime = datetime.fromtimestamp(final.stat().st_mtime, tz=timezone.utc).isoformat()
        entries.append(
            {
                "snapshot_id": "latest",
                "label": "最新",
                "updated_at": mtime,
                "path": str(final.relative_to(ROOT)),
            }
        )
    hist = _history_dir(project_id, prd_id)
    if hist.is_dir():
        for path in sorted(hist.glob("*_traceability.txt"), reverse=True):
            if path.is_symlink():
                continue
            snapshot = path.name.replace("_traceability.txt", "")
            if not SNAPSHOT_RE.match(snapshot):
                continue
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            entries.append(
                {
                    "snapshot_id": snapshot,
                    "label": _format_snapshot_label(snapshot),
                    "updated_at": mtime,
                    "path": str(path.relative_to(ROOT)),
                }
            )
    return entries


def read_traceability_snapshot(project_id: str, prd_id: str, snapshot_id: str) -> Dict[str, str]:
    if snapshot_id == "latest":
        from api.services.path_safety import resolve_traceability_report

        path, kind = resolve_traceability_report(project_id, prd_id)
        return {"content": path.read_text(encoding="utf-8"), "kind": kind, "snapshot_id": "latest"}

    if not SNAPSHOT_RE.match(snapshot_id):
        raise HTTPException(status_code=400, detail="Invalid snapshot_id")

    from api.services.path_safety import PRD_ID_RE, validate_project_id

    validate_project_id(project_id)
    if not PRD_ID_RE.match(prd_id):
        raise HTTPException(status_code=400, detail="Invalid prd_id")
    hist = (_history_dir(project_id, prd_id)).resolve()
    from api.config import REPO_ROOT

    report_root = (REPO_ROOT / "reports" / project_id).resolve()
    if not str(hist).startswith(str(report_root)):
        raise HTTPException(status_code=500, detail="Invalid history path")
    path = (hist / f"{snapshot_id}_traceability.txt").resolve()
    if not _is_under(path, hist) or not path.is_file() or path.is_symlink():
        raise HTTPException(status_code=404, detail="Report snapshot not found")
    return {"content": path.read_text(encoding="utf-8"), "kind": "final", "snapshot_id": snapshot_id}


def _format_snapshot_label(snapshot: str) -> str:
    dt = datetime.strptime(snapshot, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _is_under(path: Path, base: Path) -> bool:
    try:
        return path.is_relative_to(base)
    except AttributeError:
        import os

        return str(path).startswith(str(base) + os.sep)
