"""在业务前端仓中按组件名检索 component_path（v1.1）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).parent.parent

# 相对 frontend_root 的优先候选（组件名即文件名）
_REL_CANDIDATES = (
    "src/components/{name}.tsx",
    "src/components/{name}/index.tsx",
    "src/components/{name}.jsx",
    "src/components/{name}/index.jsx",
    "src/components/{name}/index.ts",
)


def frontend_root_from_config(project_config: dict) -> Path:
    """从 project.yaml 解析业务前端根目录。"""
    repos = project_config.get("repos") or {}
    vitest = project_config.get("vitest") or {}
    raw = repos.get("frontend") or vitest.get("frontend_root")
    if not raw:
        raise ValueError(
            "未配置 repos.frontend 或 vitest.frontend_root，无法自动检索组件路径"
        )
    root = (ROOT / str(raw)).resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"业务前端目录不存在：{root}（请检查 config/projects/*.yaml 中 repos.frontend）"
        )
    return root


def find_component_path(component_name: str, frontend_root: Path) -> Optional[str]:
    """
    在 frontend_root 下检索组件文件。
    返回相对 frontend_root 的路径（POSIX 风格，如 src/components/LoginForm.tsx）。
    """
    name = (component_name or "").strip()
    if not name or not frontend_root.is_dir():
        return None

    for pattern in _REL_CANDIDATES:
        rel = pattern.format(name=name)
        if (frontend_root / rel).is_file():
            return rel.replace("\\", "/")

    components_dir = frontend_root / "src" / "components"
    if not components_dir.is_dir():
        return None

    matches: List[Path] = []
    for path in components_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.stem == name and path.suffix in (".tsx", ".jsx", ".ts", ".js"):
            matches.append(path)
        elif path.parent.name == name and path.name.startswith("index."):
            matches.append(path)

    if not matches:
        return None

    matches.sort(key=lambda p: (len(p.relative_to(frontend_root).parts), str(p)))
    return str(matches[0].relative_to(frontend_root)).replace("\\", "/")


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def resolve_component_test_cases(
    cases: List[Dict[str, Any]],
    project_config: dict,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    为 component_test_cases 补全或校验 component_path。

    Returns:
        (resolved_cases, log_lines)
    """
    if not cases:
        return [], []

    frontend_root = frontend_root_from_config(project_config)
    logs: List[str] = []
    resolved: List[Dict[str, Any]] = []

    for case in cases:
        item = dict(case)
        component = (item.get("component") or "").strip()
        if not component:
            resolved.append(item)
            continue

        raw_path = _normalize_path(item.get("component_path") or "")
        if raw_path:
            full = (frontend_root / raw_path).resolve()
            try:
                full.relative_to(frontend_root.resolve())
            except ValueError:
                raise ValueError(
                    f"组件 {component} 的 component_path 越界：{raw_path}"
                )
            if full.is_file():
                item["component_path"] = raw_path
                resolved.append(item)
                continue
            found = find_component_path(component, frontend_root)
            if found:
                logs.append(
                    f"  ⚠️  {component}：PRD 路径 {raw_path} 不存在，已改用 {found}"
                )
                item["component_path"] = found
                resolved.append(item)
                continue
            raise FileNotFoundError(
                f"组件 {component}：component_path={raw_path} 不存在，"
                f"且在 {frontend_root} 下无法按组件名检索"
            )

        found = find_component_path(component, frontend_root)
        if not found:
            raise FileNotFoundError(
                f"组件 {component} 未填写 component_path，且在 "
                f"{frontend_root}/src/components 下未找到匹配文件；"
                f"请补全路径或先落地业务组件"
            )
        logs.append(f"  🔍 {component}：自动解析 component_path → {found}")
        item["component_path"] = found
        resolved.append(item)

    return resolved, logs


def resolve_in_test_cases_data(data: dict, project_config: dict) -> dict:
    """就地补全 data['component_test_cases'] 的 component_path。"""
    cases = data.get("component_test_cases") or []
    if not cases:
        return data
    resolved, logs = resolve_component_test_cases(cases, project_config)
    for line in logs:
        print(line)
    data["component_test_cases"] = resolved
    return data
