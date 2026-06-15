"""路径穿越防护 — prd_dir 从项目 YAML 读取"""

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


def _load_project_yaml(project_id: str) -> dict:
    validate_project_id(project_id)
    config_path = REPO_ROOT / "config" / "projects" / f"{project_id}.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_prd_dir(project_id: str) -> Path:
    """从 yaml 的 prd_dir 解析绝对路径，必须在 REPO_ROOT 内。"""
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


def resolve_prd_file(project_id: str, filename: str) -> Path:
    if not FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    prd_dir = resolve_prd_dir(project_id)
    safe_path = (prd_dir / filename).resolve()
    if not _is_under(safe_path, prd_dir):
        raise HTTPException(status_code=400, detail="Path traversal detected")
    return safe_path


def resolve_prd_path(project_id: str, prd_rel: str) -> Path:
    """校验仓库内相对路径，且必须在 yaml 配置的 prd_dir 下。"""
    validate_project_id(project_id)
    if ".." in prd_rel or prd_rel.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid prd path")
    safe_path = (REPO_ROOT / prd_rel).resolve()
    prd_dir = resolve_prd_dir(project_id)
    if not _is_under(safe_path, prd_dir):
        raise HTTPException(status_code=400, detail="PRD path outside configured prd_dir")
    if safe_path.suffix != ".md":
        raise HTTPException(status_code=400, detail="PRD must be a .md file")
    return safe_path


def resolve_traceability_report(project_id: str, prd_id: str) -> Path:
    """校验 prd_id 并解析 reports/{project_id}/{prd_id}_traceability.txt。"""
    validate_project_id(project_id)
    if not PRD_ID_RE.match(prd_id):
        raise HTTPException(status_code=400, detail="Invalid prd_id")
    report_dir = (REPO_ROOT / "reports" / project_id).resolve()
    if not _is_under(report_dir, REPO_ROOT.resolve()):
        raise HTTPException(status_code=500, detail="Invalid report directory")
    safe_path = (report_dir / f"{prd_id}_traceability.txt").resolve()
    if not _is_under(safe_path, report_dir):
        raise HTTPException(status_code=400, detail="Path traversal detected")
    return safe_path


def _is_under(path: Path, base: Path) -> bool:
    try:
        return path.is_relative_to(base)
    except AttributeError:
        base_str = str(base) + os.sep
        return str(path).startswith(base_str) or path == base
