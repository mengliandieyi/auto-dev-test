"""单一版本来源（与 VERSION 文件同步）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
