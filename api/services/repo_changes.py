"""业务仓 git 变更只读查询（dev 产物）。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import HTTPException

from api.config import REPO_ROOT
from api.services.path_safety import validate_project_id

VALID_LAYERS = frozenset({"frontend", "backend", "all"})
MAX_DIFF_BYTES = 65_536
GIT_TIMEOUT_SEC = 15


def _load_cfg(project_id: str) -> dict:
    validate_project_id(project_id)
    path = REPO_ROOT / "config" / "projects" / f"{project_id}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Project config not found")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_repo_path(project_id: str, layer: str) -> Optional[Path]:
    cfg = _load_cfg(project_id)
    repos = cfg.get("repos") if isinstance(cfg.get("repos"), dict) else {}
    rel = repos.get(layer)
    if not rel or not str(rel).strip():
        return None
    p = Path(str(rel).strip())
    resolved = p.resolve() if p.is_absolute() else (REPO_ROOT / p).resolve()
    if resolved.is_symlink():
        raise HTTPException(status_code=400, detail=f"Symlink not allowed: repos.{layer}")
    return resolved


def _run_git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 1, "git 命令超时"
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _truncate(text: str, limit: int = MAX_DIFF_BYTES) -> str:
    if len(text.encode("utf-8")) <= limit:
        return text
    encoded = text.encode("utf-8")[:limit]
    return encoded.decode("utf-8", errors="ignore") + "\n…（diff 已截断）"


def describe_repo(project_id: str, layer: str) -> Dict[str, Any]:
    if layer not in ("frontend", "backend"):
        raise HTTPException(status_code=400, detail="layer must be frontend or backend")
    cfg = _load_cfg(project_id)
    repos = cfg.get("repos") if isinstance(cfg.get("repos"), dict) else {}
    configured = str(repos.get(layer) or "").strip()
    resolved = resolve_repo_path(project_id, layer)
    item: Dict[str, Any] = {
        "layer": layer,
        "configured_path": configured,
        "absolute_path": str(resolved) if resolved else "",
        "exists": bool(resolved and resolved.is_dir()),
        "is_git_repo": False,
        "branch": "",
        "status_lines": [],
        "diff_stat": "",
        "diff": "",
        "summary": "",
    }
    if not configured:
        item["summary"] = "未配置仓库路径"
        return item
    if not resolved or not resolved.is_dir():
        item["summary"] = "仓库路径不存在"
        return item
    if not (resolved / ".git").exists():
        item["summary"] = "目录存在但不是 git 仓库"
        return item

    item["is_git_repo"] = True
    _, branch_out = _run_git(resolved, "rev-parse", "--abbrev-ref", "HEAD")
    item["branch"] = branch_out if branch_out and "fatal" not in branch_out.lower() else ""

    _, status_out = _run_git(resolved, "status", "--porcelain")
    status_lines = [ln for ln in status_out.splitlines() if ln.strip()]
    item["status_lines"] = status_lines

    _, stat_out = _run_git(resolved, "diff", "--stat")
    item["diff_stat"] = stat_out

    _, diff_out = _run_git(resolved, "diff")
    if not diff_out.strip():
        _, untracked = _run_git(resolved, "ls-files", "--others", "--exclude-standard")
        if untracked.strip():
            diff_out = "（以下为新文件，git diff 默认不展示内容）\n" + untracked
    item["diff"] = _truncate(diff_out)

    if not status_lines:
        item["summary"] = "工作区干净，无未提交变更"
    else:
        item["summary"] = f"{len(status_lines)} 个路径有变更"
    return item


def list_repo_changes(project_id: str, layer: str = "all") -> Dict[str, Any]:
    if layer not in VALID_LAYERS:
        raise HTTPException(status_code=400, detail="layer must be frontend, backend, or all")
    layers: List[str] = ["frontend", "backend"] if layer == "all" else [layer]
    return {"repos": [describe_repo(project_id, lyr) for lyr in layers]}
