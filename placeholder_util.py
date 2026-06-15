"""占位符 {{a.b}} → 字面量（generate 阶段）。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


def load_test_data(project_id: str) -> dict:
    candidates = [
        ROOT / "tests" / "fixtures" / project_id / "test_data.json",
        ROOT / "tests" / "fixtures" / "test_data.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _lookup(data: dict, key: str) -> str:
    cur: Any = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            env_key = key.upper().replace(".", "_")
            if os.getenv(env_key):
                return os.getenv(env_key, "")
            return f"{{{{{key}}}}}"
        cur = cur[part]
    return str(cur)


def replace_placeholders(value: Any, data: dict) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            return _lookup(data, m.group(1))

        return PLACEHOLDER_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: replace_placeholders(v, data) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_placeholders(v, data) for v in value]
    return value


def resolve_intermediate(data: dict, project_id: str) -> dict:
    td = load_test_data(project_id)
    return replace_placeholders(data, td)
