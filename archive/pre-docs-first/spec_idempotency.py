"""生成幂等：以 intermediate prd_version + 已提交 spec 文件头为准（不依赖 meta.db）。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).parent
SPEC_HEADER_RE = re.compile(r"PRD:\s*(\S+)\s+v([\d.]+)", re.IGNORECASE)


def read_spec_header(spec_path: Path) -> Optional[Tuple[str, str]]:
    """从 spec 文件头解析 (prd_id, prd_version)。"""
    if not spec_path.exists():
        return None
    head = spec_path.read_text(encoding="utf-8")[:2500]
    match = SPEC_HEADER_RE.search(head)
    if not match:
        return None
    return match.group(1), match.group(2)


def find_generated_spec(
    project_id: str,
    prd_id: str,
    layer: str,
    preferred: Optional[Path] = None,
) -> Optional[Path]:
    if preferred and preferred.exists():
        return preferred
    subdir = "e2e" if layer == "e2e" else "component"
    ext = ".spec.ts" if layer == "e2e" else ".test.tsx"
    base = ROOT / "tests" / "generated" / project_id / subdir
    if not base.is_dir():
        return None
    matches = sorted(base.glob(f"{prd_id}_*{ext}"))
    return matches[0] if matches else None


def check_generation_idempotency(
    project_id: str,
    prd_id: str,
    layer: str,
    current_version: str,
    preferred_spec: Path,
) -> Tuple[str, Optional[str], Optional[Path]]:
    """
    判定是否应跳过生成。

    Returns:
        action: "skip" | "archive" | "generate"
        existing_version: 旧版本号（archive 时）
        spec_path: 现有 spec 路径
    """
    spec_path = find_generated_spec(project_id, prd_id, layer, preferred_spec)
    if not spec_path:
        return "generate", None, None

    header = read_spec_header(spec_path)
    if header:
        header_prd, header_ver = header
        if header_prd == prd_id and header_ver == current_version:
            return "skip", header_ver, spec_path
        if header_prd == prd_id and header_ver != current_version:
            return "archive", header_ver, spec_path

    return "generate", None, spec_path
