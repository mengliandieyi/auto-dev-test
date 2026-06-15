#!/usr/bin/env python3
"""将 VERSION 文件同步到 package.json 与 admin/package.json。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

for rel in ("package.json", "admin/package.json"):
    path = ROOT / rel
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated {rel} -> {version}")

if __name__ == "__main__":
    sys.exit(0)
