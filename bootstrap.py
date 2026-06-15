"""统一仓库根路径引导，避免各处重复 sys.path.insert。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_PATH_ENTRIES = (
    ROOT,
    ROOT / "prd-parser",
    ROOT / "test-generator",
    ROOT / "component-generator",
)


def setup_repo_paths() -> Path:
    """将仓库根及子模块目录加入 sys.path（幂等）。"""
    for entry in _PATH_ENTRIES:
        text = str(entry)
        if text not in sys.path:
            sys.path.insert(0, text)
    return ROOT
