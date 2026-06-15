"""加载 config YAML，解析 reuse_existing_server: auto 等哨兵值。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parent


def resolve_reuse_existing_server(value: Any) -> bool:
    if value == "auto" or value is None:
        return os.getenv("CI", "").lower() not in ("true", "1", "yes")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
    return bool(value)


def _resolve_node(node: Any) -> Any:
    if isinstance(node, dict):
        out = {k: _resolve_node(v) for k, v in node.items()}
        if "reuse_existing_server" in out:
            out["reuse_existing_server"] = resolve_reuse_existing_server(
                out["reuse_existing_server"]
            )
        return out
    if isinstance(node, list):
        return [_resolve_node(x) for x in node]
    if isinstance(node, str):
        m = re.fullmatch(r"\$\{([^}:]+)(?::-(.+))?\}", node.strip())
        if m:
            key, default = m.group(1), m.group(2)
            return os.getenv(key, default if default is not None else "")
    return node


def load_project_config(project_id: str) -> dict:
    config_path = ROOT / "config" / "projects" / f"{project_id}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"找不到项目配置：{config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    global_path = ROOT / "config" / "global.yaml"
    global_cfg: dict = {}
    if global_path.exists():
        global_cfg = yaml.safe_load(global_path.read_text(encoding="utf-8")) or {}
    merged = {**global_cfg, **raw}
    return _resolve_node(merged)
