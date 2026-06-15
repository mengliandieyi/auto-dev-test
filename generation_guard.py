"""E2E / 组件 generate 共享逻辑（M2）。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from content_fingerprint import collect_generation_conflict_paths, scan_merge_conflicts
from meta_db import archive_old_spec, ensure_project_db
from spec_idempotency import GenerationDecision, decide_generation

ROOT = Path(__file__).parent


def guard_generation(
    project_id: str,
    prd_id: str,
    layer: str,
    current_version: str,
    current_hash: str,
    spec_path: Path,
    *,
    force: bool = False,
) -> Optional[GenerationDecision]:
    """
    合并冲突扫描 + 幂等判定。
    返回 None 表示应继续生成；否则按 decision.action 处理。
  CONTENT_DRIFT 在 CI 下于 decide_generation 内 exit 1。
    """
    scan_merge_conflicts(
        collect_generation_conflict_paths(project_id, prd_id, ROOT, layers=(layer,)),
        label="generate",
    )
    decision = decide_generation(
        project_id,
        prd_id,
        layer,
        current_version,
        current_hash or "",
        spec_path,
        force=force,
    )
    if decision.action == "skip":
        return decision
    if decision.action == "archive" and decision.spec_path and decision.existing_version:
        db_path = ensure_project_db(project_id)
        ext = ".spec.ts" if layer == "e2e" else ".test.tsx"
        archive_old_spec(
            db_path,
            {
                "project_id": project_id,
                "prd_id": prd_id,
                "layer": layer,
                "prd_version": decision.existing_version,
            },
            decision.spec_path,
            ext,
        )
    return None
