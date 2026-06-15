"""路径穿越 / symlink 防护（TECH §5.5）。"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from fastapi import HTTPException

from api.config import REPO_ROOT

PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.md$")
PRD_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
MAX_UPLOAD_BYTES = 1_048_576
MAX_WRITE_BYTES = 1_048_576
CONFLICT_MARKERS = ("<<<<<<<", ">>>>>>>")


def _scan_content_conflicts(content: str, label: str) -> None:
    head = content[:2048]
    for marker in CONFLICT_MARKERS:
        if marker in head:
            raise HTTPException(status_code=400, detail=f"MERGE_CONFLICT in {label}")


def _check_write_size(content: str | bytes) -> None:
    size = len(content.encode("utf-8") if isinstance(content, str) else content)
    if size > MAX_WRITE_BYTES:
        raise HTTPException(status_code=400, detail="Content exceeds 1MB limit")


def resolve_global_config_path() -> Path:
    """固定路径 config/global.yaml，禁止穿越与 symlink。"""
    config_dir = (REPO_ROOT / "config").resolve()
    path = (config_dir / "global.yaml").resolve()
    if not _is_under(path, config_dir):
        raise HTTPException(status_code=500, detail="Invalid global config path")
    if path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlink not allowed")
    return path


def resolve_project_config_path(project_id: str) -> Path:
    validate_project_id(project_id)
    config_dir = (REPO_ROOT / "config" / "projects").resolve()
    path = (config_dir / f"{project_id}.yaml").resolve()
    if not _is_under(path, config_dir):
        raise HTTPException(status_code=400, detail="Invalid project config path")
    if path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlink not allowed")
    return path


def _load_project_yaml(project_id: str) -> dict:
    validate_project_id(project_id)
    config_path = REPO_ROOT / "config" / "projects" / f"{project_id}.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_prd_dir(project_id: str) -> Path:
    cfg = _load_project_yaml(project_id)
    raw = cfg.get("prd_dir") or f"./prds/{project_id}/"
    prd_dir = (REPO_ROOT / raw).resolve()
    if not _is_under(prd_dir, REPO_ROOT.resolve()):
        raise HTTPException(status_code=500, detail="Invalid prd_dir in project config")
    if not prd_dir.is_dir():
        raise HTTPException(status_code=404, detail="PRD directory not found")
    return prd_dir


def validate_project_id(project_id: str) -> str:
    if not PROJECT_ID_RE.match(project_id):
        raise HTTPException(status_code=400, detail="Invalid project_id")
    config = REPO_ROOT / "config" / "projects" / f"{project_id}.yaml"
    if not config.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return project_id


def validate_new_project_id(project_id: str) -> str:
    if not PROJECT_ID_RE.match(project_id):
        raise HTTPException(status_code=400, detail="Invalid project_id")
    config = REPO_ROOT / "config" / "projects" / f"{project_id}.yaml"
    if config.exists():
        raise HTTPException(status_code=409, detail=f"Project already exists: {project_id}")
    return project_id


def resolve_prd_file(project_id: str, filename: str, *, must_exist: bool = True) -> Path:
    if not FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    prd_dir = resolve_prd_dir(project_id)
    candidate = prd_dir / filename
    if candidate.is_symlink():
        raise HTTPException(status_code=400, detail="Symlink not allowed")
    if must_exist:
        try:
            safe_path = candidate.resolve(strict=True)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="PRD not found")
    else:
        safe_path = candidate.resolve()
    if not _is_under(safe_path, prd_dir):
        raise HTTPException(status_code=400, detail="Path traversal detected")
    return safe_path


def resolve_prd_path(project_id: str, prd_rel: str) -> Path:
    validate_project_id(project_id)
    if ".." in prd_rel or prd_rel.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid prd path")
    raw = (REPO_ROOT / prd_rel)
    if raw.is_symlink():
        raise HTTPException(status_code=400, detail="Symlink not allowed")
    safe_path = raw.resolve()
    prd_dir = resolve_prd_dir(project_id)
    if not _is_under(safe_path, prd_dir):
        raise HTTPException(status_code=400, detail="PRD path outside configured prd_dir")
    if safe_path.suffix != ".md":
        raise HTTPException(status_code=400, detail="PRD must be a .md file")
    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="PRD not found")
    return safe_path


def resolve_traceability_report(project_id: str, prd_id: str) -> tuple[Path, str]:
    """返回 (path, kind) — 优先 final，无则 skeleton。"""
    validate_project_id(project_id)
    if not PRD_ID_RE.match(prd_id):
        raise HTTPException(status_code=400, detail="Invalid prd_id")
    report_dir = (REPO_ROOT / "reports" / project_id).resolve()
    if not _is_under(report_dir, REPO_ROOT.resolve()):
        raise HTTPException(status_code=500, detail="Invalid report directory")
    final = (report_dir / f"{prd_id}_traceability.txt").resolve()
    skeleton = (report_dir / f"{prd_id}_traceability.skeleton.txt").resolve()
    if _is_under(final, report_dir) and final.is_file() and not final.is_symlink():
        return final, "final"
    if _is_under(skeleton, report_dir) and skeleton.is_file() and not skeleton.is_symlink():
        return skeleton, "skeleton"
    raise HTTPException(status_code=404, detail="Report not found")


def _is_under(path: Path, base: Path) -> bool:
    try:
        return path.is_relative_to(base)
    except AttributeError:
        base_str = str(base) + os.sep
        return str(path).startswith(base_str) or path == base
