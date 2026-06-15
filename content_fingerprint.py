"""PRD 内容指纹与合并冲突扫描（TECH §4.1 / §4.3）。"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

CONFLICT_MARKERS = ("<<<<<<<", ">>>>>>>")
_FRONT_MATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def prd_content_hash(prd_path: Path) -> str:
    """去 YAML front matter → 统一 LF → 行尾去空白 → SHA-256 hex。"""
    text = prd_path.read_text(encoding="utf-8")
    body = _FRONT_MATTER_RE.sub("", text, count=1)
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in body.split("\n"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def source_git_sha(context_path: Path) -> Optional[str]:
    """可选：写入 intermediate 的 Git SHA（仅追溯）。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=context_path.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            return sha if sha else None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _scan_file_head(path: Path, limit: int = 2048) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return None
    for marker in CONFLICT_MARKERS:
        if marker in head:
            return marker
    return None


def scan_merge_conflicts(paths: Iterable[Path], *, label: str = "文件") -> None:
    """命中冲突标记 → stderr `MERGE_CONFLICT` 并 exit 1。"""
    for path in paths:
        hit = _scan_file_head(path)
        if hit:
            print(f"MERGE_CONFLICT: {label} {path} 含合并冲突标记 {hit}", file=sys.stderr)
            sys.exit(1)


def find_prd_path(project_id: str, prd_id: str, root: Path) -> Optional[Path]:
    prd_dir = root / "prds" / project_id
    if not prd_dir.is_dir():
        return None
    matches = sorted(prd_dir.glob(f"{prd_id}_*.md"))
    return matches[0] if matches else None


def collect_generation_conflict_paths(
    project_id: str,
    prd_id: str,
    root: Path,
    *,
    layers: tuple[str, ...] = ("e2e", "component"),
) -> list[Path]:
    paths: list[Path] = []
    prd = find_prd_path(project_id, prd_id, root)
    if prd:
        paths.append(prd)
    inter = root / "tests/intermediate" / project_id / f"{prd_id}_test-cases.json"
    if inter.exists():
        paths.append(inter)
    for layer in layers:
        sub = "e2e" if layer == "e2e" else "component"
        ext = ".spec.ts" if layer == "e2e" else ".test.tsx"
        base = root / "tests/generated" / project_id / sub
        if base.is_dir():
            paths.extend(sorted(base.glob(f"{prd_id}_*{ext}")))
    return paths
