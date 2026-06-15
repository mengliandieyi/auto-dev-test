"""在 vitest.frontend_root 下解析 component_path。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).parent.parent

_SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next"}

_REL_CANDIDATES = (
    "src/components/{name}.tsx",
    "src/components/{name}/index.tsx",
)


def frontend_root_from_config(project_config: dict) -> Path:
    vitest = project_config.get("vitest") or {}
    raw = vitest.get("frontend_root") or (project_config.get("repos") or {}).get("frontend")
    if not raw:
        raise ValueError("未配置 vitest.frontend_root")
    root = (ROOT / str(raw)).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"frontend_root 不存在：{root}")
    return root


def _dfs_find(frontend_root: Path, name: str) -> List[str]:
    matches: List[str] = []
    for path in frontend_root.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.parts)
        if parts & _SKIP_DIRS:
            continue
        rel = path.relative_to(frontend_root).as_posix()
        if path.stem == name and path.suffix in (".tsx", ".jsx"):
            matches.append(rel)
        elif path.parent.name == name and path.name.startswith("index."):
            matches.append(rel)
    return sorted(set(matches))


def find_component_path(component_name: str, frontend_root: Path) -> str:
    name = (component_name or "").strip()
    if not name:
        raise ValueError("component 名为空")

    for pattern in _REL_CANDIDATES:
        rel = pattern.format(name=name)
        if (frontend_root / rel).is_file():
            return rel

    matches = _dfs_find(frontend_root, name)
    if not matches:
        raise FileNotFoundError(
            f"组件 {name} 未找到；请补全 component_path 或检查 {frontend_root}"
        )
    if len(matches) > 1:
        print("AMBIGUOUS_COMPONENT_PATH", file=sys.stderr)
        for m in matches:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def resolve_in_test_cases_data(data: dict, project_config: dict) -> dict:
    cases = data.get("component_test_cases") or []
    if not cases:
        return data
    root = frontend_root_from_config(project_config)
    resolved = []
    for case in cases:
        item = dict(case)
        component = (item.get("component") or "").strip()
        raw_path = (item.get("component_path") or "").strip()
        if raw_path and (root / raw_path).is_file():
            item["component_path"] = raw_path.replace("\\", "/")
        elif component:
            item["component_path"] = find_component_path(component, root)
        resolved.append(item)
    data["component_test_cases"] = resolved
    return data
