"""项目 / PRD / 报告文件读取"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from api.config import REPO_ROOT
from api.services.path_safety import (
    resolve_prd_dir,
    resolve_prd_file,
    resolve_traceability_report,
    validate_project_id,
)


def list_projects() -> List[Dict[str, Any]]:
    projects_dir = REPO_ROOT / "config" / "projects"
    items = []
    for path in sorted(projects_dir.glob("*.yaml")):
        project_id = path.stem
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        items.append({
            "id": project_id,
            "base_url": cfg.get("base_url", ""),
            "prd_dir": cfg.get("prd_dir", f"./prds/{project_id}/"),
        })
    return items


def get_project(project_id: str) -> Dict[str, Any]:
    validate_project_id(project_id)
    path = REPO_ROOT / "config" / "projects" / f"{project_id}.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return {"id": project_id, **cfg}


def list_prds(project_id: str) -> List[Dict[str, Any]]:
    prd_dir = resolve_prd_dir(project_id)
    if not prd_dir.exists():
        return []
    items = []
    for path in sorted(prd_dir.glob("*.md")):
        rel = str(path.relative_to(REPO_ROOT))
        items.append({
            "filename": path.name,
            "path": rel,
            "size": path.stat().st_size,
        })
    return items


def read_prd(project_id: str, filename: str) -> Dict[str, str]:
    path = resolve_prd_file(project_id, filename)
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="PRD not found")
    return {
        "filename": filename,
        "path": str(path.relative_to(REPO_ROOT)),
        "content": path.read_text(encoding="utf-8"),
    }


def list_reports(project_id: str) -> List[Dict[str, str]]:
    validate_project_id(project_id)
    report_dir = REPO_ROOT / "reports" / project_id
    if not report_dir.exists():
        return []
    items = []
    for path in sorted(report_dir.glob("*_traceability.txt")):
        prd_id = path.name.replace("_traceability.txt", "")
        items.append({
            "prd_id": prd_id,
            "filename": path.name,
            "path": str(path.relative_to(REPO_ROOT)),
        })
    return items


def read_traceability(project_id: str, prd_id: str) -> str:
    path = resolve_traceability_report(project_id, prd_id)
    if not path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return path.read_text(encoding="utf-8")
