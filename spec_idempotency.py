"""生成幂等：M2 以 intermediate hash + spec 文件头为准。"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).parent
SPEC_HEADER_RE = re.compile(r"PRD:\s*(\S+)\s+v([\d.]+)", re.IGNORECASE)
HASH_HEADER_RE = re.compile(r"Hash:\s*(\S+)", re.IGNORECASE)


@dataclass
class GenerationDecision:
    action: str  # skip | archive | generate
    existing_version: Optional[str] = None
    spec_path: Optional[Path] = None
    warned: bool = False


def read_spec_header(spec_path: Path) -> Optional[Tuple[str, str]]:
    """从 spec 文件头解析 (prd_id, prd_version)。"""
    if not spec_path.exists():
        return None
    head = spec_path.read_text(encoding="utf-8")[:2500]
    match = SPEC_HEADER_RE.search(head)
    if not match:
        return None
    return match.group(1), match.group(2)


def read_spec_hash(spec_path: Path) -> Optional[str]:
    if not spec_path.exists():
        return None
    head = spec_path.read_text(encoding="utf-8")[:2500]
    match = HASH_HEADER_RE.search(head)
    return match.group(1) if match else None


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


def parse_version(version: str) -> Tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def is_version_upgrade(old_ver: str, new_ver: str) -> bool:
    return parse_version(new_ver) > parse_version(old_ver)


def _content_drift_exit(force: bool) -> None:
    if force:
        return
    if os.getenv("CI", "").lower() in ("1", "true", "yes"):
        print("CONTENT_DRIFT: PRD 正文已变更但 version 未 bump", file=sys.stderr)
        sys.exit(1)
    print("CONTENT_DRIFT: PRD 正文已变更但 version 未 bump（本地允许继续）", file=sys.stderr)


def decide_generation(
    project_id: str,
    prd_id: str,
    layer: str,
    current_version: str,
    current_hash: str,
    preferred_spec: Path,
    *,
    force: bool = False,
) -> GenerationDecision:
    """
    M2 generate 判定（TECH §4.2）。

    | hash | version | 行为 |
    | 同   | 同      | skip |
    | 同   | 异      | skip + VERSION_DRIFT |
    | 异   | 同      | CONTENT_DRIFT 分级 |
    | 异   | 升      | archive + generate |
    """
    spec_path = find_generated_spec(project_id, prd_id, layer, preferred_spec)
    if not spec_path:
        return GenerationDecision(action="generate")

    header = read_spec_header(spec_path)
    if not header:
        return GenerationDecision(action="generate", spec_path=spec_path)

    header_prd, header_ver = header
    if header_prd != prd_id:
        return GenerationDecision(action="generate", spec_path=spec_path)

    header_hash = read_spec_hash(spec_path)

    # M1 兼容：spec 尚无 Hash 行时仅按 version 判定
    if header_hash is None:
        if header_ver == current_version:
            return GenerationDecision(action="skip", existing_version=header_ver, spec_path=spec_path)
        return GenerationDecision(
            action="archive",
            existing_version=header_ver,
            spec_path=spec_path,
        )

    if header_hash == current_hash:
        if header_ver == current_version:
            return GenerationDecision(action="skip", existing_version=header_ver, spec_path=spec_path)
        print(
            f"VERSION_DRIFT: spec v{header_ver} 与 intermediate v{current_version} 不一致，但内容 hash 未变",
            file=sys.stderr,
        )
        return GenerationDecision(
            action="skip",
            existing_version=header_ver,
            spec_path=spec_path,
            warned=True,
        )

    if header_ver == current_version:
        _content_drift_exit(force)
        return GenerationDecision(
            action="archive",
            existing_version=header_ver,
            spec_path=spec_path,
            warned=True,
        )

    if is_version_upgrade(header_ver, current_version):
        return GenerationDecision(
            action="archive",
            existing_version=header_ver,
            spec_path=spec_path,
        )

    _content_drift_exit(force)
    return GenerationDecision(
        action="archive",
        existing_version=header_ver,
        spec_path=spec_path,
        warned=True,
    )


# 保留旧 API 供过渡
def check_generation_idempotency(
    project_id: str,
    prd_id: str,
    layer: str,
    current_version: str,
    preferred_spec: Path,
) -> Tuple[str, Optional[str], Optional[Path]]:
    decision = decide_generation(
        project_id,
        prd_id,
        layer,
        current_version,
        "",
        preferred_spec,
    )
    return decision.action, decision.existing_version, decision.spec_path
