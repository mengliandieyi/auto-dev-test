"""子进程 PATH 补全（OpenHands / uv 工具链）。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, Optional


def augment_path_env(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    merged = (env or os.environ).copy()
    if merged.get("AUTO_DEV_DISABLE_TOOL_PATH") == "1":
        return merged
    extras = (
        Path.home() / ".local" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
    )
    parts = [p for p in merged.get("PATH", "").split(os.pathsep) if p]
    for directory in extras:
        text = str(directory)
        if directory.is_dir() and text not in parts:
            parts.insert(0, text)
    merged["PATH"] = os.pathsep.join(parts)
    return merged


def which_tool(*names: str) -> Optional[str]:
    path = augment_path_env().get("PATH", "")
    for name in names:
        found = shutil.which(name, path=path)
        if found:
            return found
    return None
