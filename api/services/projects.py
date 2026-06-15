"""项目 / PRD / 报告读取（M3 只读）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import HTTPException

from api.config import REPO_ROOT
from api.services.path_safety import (
    _check_write_size,
    _scan_content_conflicts,
    MAX_UPLOAD_BYTES,
    resolve_prd_dir,
    resolve_prd_file,
    resolve_project_config_path,
    resolve_traceability_report,
    validate_project_id,
)

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_front_matter(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
        return {str(k): str(v) for k, v in data.items()}
    except yaml.YAMLError:
        return {}


def _project_dirs(project_id: str) -> List[Path]:
    return [
        REPO_ROOT / "prds" / project_id,
        REPO_ROOT / "tests" / "intermediate" / project_id,
        REPO_ROOT / "tests" / "generated" / project_id,
        REPO_ROOT / "tests" / "archive" / project_id,
        REPO_ROOT / "reports" / project_id,
    ]


def create_project(project_id: str, project_name: str, base_url: str) -> Dict[str, Any]:
    from api.services.path_safety import validate_new_project_id

    validate_new_project_id(project_id)
    base_url = base_url.strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="base_url is required")

    name = (project_name or project_id).strip()
    cred_env = project_id.upper().replace("-", "_") + "_CREDENTIALS"
    cfg: Dict[str, Any] = {
        "project_id": project_id,
        "project_name": name,
        "base_url": base_url,
        "prd_dir": f"./prds/{project_id}/",
        "intermediate_dir": f"./tests/intermediate/{project_id}/",
        "test_output_dir": f"./tests/generated/{project_id}/",
        "archive_dir": f"./tests/archive/{project_id}/",
        "report": {"format": "text", "output_dir": f"./reports/{project_id}/"},
        "vitest": {"enabled": False},
        "auth": {
            "type": "cookie",
            "login_url": "/login",
            "credentials_env": cred_env,
        },
        "dev": {
            "frontend_skill": "clean-ui",
            "backend_skill": "go-api",
        },
    }

    config_dir = (REPO_ROOT / "config" / "projects").resolve()
    config_path = (config_dir / f"{project_id}.yaml").resolve()
    if config_dir not in config_path.parents:
        raise HTTPException(status_code=400, detail="Invalid project config path")

    for folder in _project_dirs(project_id):
        folder.mkdir(parents=True, exist_ok=True)

    text = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)
    config_path.write_text(text, encoding="utf-8")

    from playwright_runtime import sync_playwright_runtime

    sync_playwright_runtime()

    return {
        "id": project_id,
        "name": name,
        "base_url": base_url,
        "prd_dir": cfg["prd_dir"],
        "path": str(config_path.relative_to(REPO_ROOT.resolve())),
    }


def list_projects() -> List[Dict[str, Any]]:
    projects_dir = REPO_ROOT / "config" / "projects"
    items = []
    for path in sorted(projects_dir.glob("*.yaml")):
        project_id = path.stem
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        items.append({
            "id": project_id,
            "name": cfg.get("project_name") or cfg.get("name", project_id),
            "base_url": cfg.get("base_url", ""),
            "prd_dir": cfg.get("prd_dir", f"./prds/{project_id}/"),
        })
    return items


def get_project(project_id: str) -> Dict[str, Any]:
    validate_project_id(project_id)
    path = REPO_ROOT / "config" / "projects" / f"{project_id}.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    public = {k: v for k, v in cfg.items() if not str(k).endswith("_env")}
    return {"id": project_id, **public}


def list_prds(project_id: str) -> List[Dict[str, Any]]:
    prd_dir = resolve_prd_dir(project_id)
    items = []
    for path in sorted(prd_dir.glob("*.md")):
        if path.is_symlink():
            continue
        meta = _parse_front_matter(path)
        items.append({
            "filename": path.name,
            "prd_id": meta.get("prd_id", path.stem.split("_")[0]),
            "version": meta.get("version", ""),
            "path": str(path.relative_to(REPO_ROOT)),
            "size": path.stat().st_size,
        })
    return items


def read_prd(project_id: str, filename: str) -> Dict[str, str]:
    path = resolve_prd_file(project_id, filename)
    return {
        "filename": filename,
        "path": str(path.relative_to(REPO_ROOT)),
        "content": path.read_text(encoding="utf-8"),
    }


def list_reports(project_id: str) -> List[Dict[str, Any]]:
    validate_project_id(project_id)
    report_dir = REPO_ROOT / "reports" / project_id
    if not report_dir.exists():
        return []
    seen: Dict[str, Dict[str, Any]] = {}
    for path in sorted(report_dir.glob("*_traceability*.txt")):
        if path.is_symlink():
            continue
        name = path.name
        if name.endswith("_traceability.skeleton.txt"):
            prd_id = name.replace("_traceability.skeleton.txt", "")
            kind = "skeleton"
        elif name.endswith("_traceability.txt"):
            prd_id = name.replace("_traceability.txt", "")
            kind = "final"
        else:
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        entry = {"prd_id": prd_id, "kind": kind, "updated_at": mtime, "path": str(path.relative_to(REPO_ROOT))}
        if prd_id not in seen or kind == "final":
            seen[prd_id] = entry
    return list(seen.values())


def read_traceability(project_id: str, prd_id: str) -> Dict[str, str]:
    path, kind = resolve_traceability_report(project_id, prd_id)
    return {"content": path.read_text(encoding="utf-8"), "kind": kind}


def read_project_yaml_text(project_id: str) -> Dict[str, str]:
    path = resolve_project_config_path(project_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Project config not found")
    return {"content": path.read_text(encoding="utf-8")}


def write_project_yaml_text(project_id: str, content: str) -> Dict[str, str]:
    _check_write_size(content)
    _scan_content_conflicts(content, "project config")
    try:
        parsed = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="YAML root must be a mapping")
    pid = parsed.get("project_id") or parsed.get("project")
    if pid and str(pid) != project_id:
        raise HTTPException(status_code=400, detail="project_id in YAML must match URL")
    path = resolve_project_config_path(project_id)
    path.write_text(content, encoding="utf-8")
    root = REPO_ROOT.resolve()
    return {"id": project_id, "path": str(path.resolve().relative_to(root))}


def write_prd_content(project_id: str, filename: str, content: str) -> Dict[str, str]:
    _check_write_size(content)
    _scan_content_conflicts(content, filename)
    path = resolve_prd_file(project_id, filename, must_exist=True)
    path.write_text(content, encoding="utf-8")
    root = REPO_ROOT.resolve()
    return {
        "filename": filename,
        "path": str(path.resolve().relative_to(root)),
        "size": path.stat().st_size,
    }


def upload_prd_file(project_id: str, filename: str, data: bytes) -> Dict[str, str]:
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Upload exceeds 1MB limit")
    path = resolve_prd_file(project_id, filename, must_exist=False)
    if path.exists():
        raise HTTPException(status_code=409, detail="PRD file already exists")
    text = data.decode("utf-8")
    _scan_content_conflicts(text, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    root = REPO_ROOT.resolve()
    return {
        "filename": filename,
        "path": str(path.resolve().relative_to(root)),
        "size": path.stat().st_size,
    }
