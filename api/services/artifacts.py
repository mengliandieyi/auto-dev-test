"""测试产物读取：intermediate、generated、归档对比。"""

from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from api.config import REPO_ROOT
from api.services.path_safety import PRD_ID_RE, _is_under, validate_project_id


def _intermediate_path(project_id: str, prd_id: str) -> Path:
    if not PRD_ID_RE.match(prd_id):
        raise HTTPException(status_code=400, detail="Invalid prd_id")
    base = (REPO_ROOT / "tests" / "intermediate" / project_id).resolve()
    path = (base / f"{prd_id}_test-cases.json").resolve()
    if not _is_under(path, base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return path


def _generated_root(project_id: str) -> Path:
    base = (REPO_ROOT / "tests" / "generated" / project_id).resolve()
    if not _is_under(base, REPO_ROOT.resolve()):
        raise HTTPException(status_code=500, detail="Invalid generated root")
    return base


def read_test_cases(project_id: str, prd_id: str) -> Dict[str, Any]:
    validate_project_id(project_id)
    path = _intermediate_path(project_id, prd_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="尚未提取测试用例，请先执行「提取测试用例」")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "data": data,
    }


def list_generated_files(project_id: str, prd_id: str) -> List[Dict[str, Any]]:
    validate_project_id(project_id)
    if not PRD_ID_RE.match(prd_id):
        raise HTTPException(status_code=400, detail="Invalid prd_id")
    root = _generated_root(project_id)
    items: List[Dict[str, Any]] = []
    for layer in ("e2e", "component"):
        layer_dir = root / layer
        if not layer_dir.is_dir():
            continue
        for path in sorted(layer_dir.glob(f"{prd_id}_*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            items.append({
                "layer": layer,
                "filename": path.name,
                "path": rel,
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
                "size": path.stat().st_size,
            })
    return items


def read_generated_file(project_id: str, relative_path: str) -> Dict[str, str]:
    validate_project_id(project_id)
    if ".." in relative_path or relative_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    path = (REPO_ROOT / relative_path).resolve()
    root = _generated_root(project_id)
    if not _is_under(path, root) or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlink not allowed")
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "content": path.read_text(encoding="utf-8"),
    }


def list_changes(project_id: str, prd_id: str) -> Dict[str, Any]:
    validate_project_id(project_id)
    if not PRD_ID_RE.match(prd_id):
        raise HTTPException(status_code=400, detail="Invalid prd_id")

    archives: List[Dict[str, Any]] = []
    archive_dir = REPO_ROOT / "tests" / "archive" / project_id
    if archive_dir.is_dir():
        for path in sorted(archive_dir.glob(f"*{prd_id}*"), reverse=True)[:5]:
            if path.is_file():
                archives.append({
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "updated_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
                })

    diffs: List[Dict[str, str]] = []
    generated = list_generated_files(project_id, prd_id)
    gen_by_layer = {g["layer"]: g for g in generated}
    for arch in archives:
        arch_path = REPO_ROOT / arch["path"]
        layer = _archive_layer(arch_path.name)
        current = gen_by_layer.get(layer) if layer else None
        if not current:
            continue
        cur_path = REPO_ROOT / current["path"]
        diff = _unified_diff(arch_path, cur_path, arch["path"], current["path"])
        if diff.strip():
            diffs.append({
                "title": f"{layer}：归档 → 当前",
                "from_path": arch["path"],
                "to_path": current["path"],
                "diff": diff,
            })

    heal_patches: List[Dict[str, Any]] = []
    try:
        from heal.store import list_heal_runs

        for run in list_heal_runs(project_id, prd_id)[:5]:
            preview = (run.get("patch_preview") or "").strip()
            if preview:
                heal_patches.append({
                    "id": run["id"],
                    "status": run.get("status"),
                    "created_at": run.get("created_at"),
                    "diff": preview,
                })
    except Exception:
        pass

    return {
        "archives": archives,
        "diffs": diffs,
        "heal_patches": heal_patches,
    }


def _archive_layer(filename: str) -> Optional[str]:
    for layer in ("e2e", "component"):
        if f"_{layer}_" in filename:
            return layer
    return None


def _unified_diff(old_path: Path, new_path: Path, old_label: str, new_label: str) -> str:
    if not old_path.is_file() or not new_path.is_file():
        return ""
    old_lines = old_path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = new_path.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_lines, fromfile=old_label, tofile=new_label))
