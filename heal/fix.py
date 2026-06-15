"""Heal 修复应用（TECH §8.6）。"""

from __future__ import annotations

import difflib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent


def plan_fix(diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    target = diagnosis.get("fix_target") or diagnosis.get("category") or "test_script"
    return {
        "target": target,
        "actions": ["regenerate_specs"] if target == "test_script" else ["write_diff_only"],
        "dry_run": target in ("business_code", "prd_drift"),
    }


def apply_fix(
    project_id: str,
    prd_id: str,
    plan: Dict[str, Any],
    patch_dir: Path,
    *,
    dry_run: bool = True,
) -> Tuple[List[str], bool]:
    target = plan.get("target", "test_script")
    gen_dir = ROOT / "tests" / "generated" / project_id

    if target == "test_script":
        before = _snapshot_tree(gen_dir)
        backup_dir = patch_dir / "_backup_generated"
        _restore_tree(gen_dir, before, backup_dir)

        subprocess.run(
            [
                sys.executable,
                str(ROOT / "run.py"),
                "generate",
                "--project",
                project_id,
                "--prd-id",
                prd_id,
                "--force",
            ],
            cwd=str(ROOT),
            check=False,
        )
        after = _snapshot_tree(gen_dir)
        diffs = _write_diffs(patch_dir, before, after)

        if dry_run:
            _restore_tree(gen_dir, before, backup_dir)
            return diffs, False

        return diffs, True

    if target == "business_code":
        note = patch_dir / "business_code.TODO.md"
        note.write_text("业务代码修复需人工审核后在 repos 路径应用。\n", encoding="utf-8")
        return ["business_code dry-run"], False

    return [], False


def apply_patch_dir(patch_dir: Path, project_id: str, prd_id: str) -> bool:
    meta = patch_dir / "meta.txt"
    if meta.exists():
        prd_id = meta.read_text(encoding="utf-8").strip() or prd_id
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "run.py"),
            "generate",
            "--project",
            project_id,
            "--prd-id",
            prd_id,
            "--force",
        ],
        cwd=str(ROOT),
        check=False,
    )
    return True


def discard_patch_dir(patch_dir: Path) -> None:
    if patch_dir.is_dir():
        shutil.rmtree(patch_dir, ignore_errors=True)


def _prd_from_patch(patch_dir: Path) -> str:
    meta = patch_dir / "meta.txt"
    if meta.exists():
        return meta.read_text(encoding="utf-8").strip()
    return "PROJ-001"


def _snapshot_tree(base: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not base.is_dir():
        return out
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in (".ts", ".tsx"):
            out[str(p.relative_to(base))] = p.read_text(encoding="utf-8")
    return out


def _restore_tree(base: Path, snapshot: Dict[str, str], backup_dir: Path) -> None:
    if base.is_dir():
        shutil.copytree(base, backup_dir, dirs_exist_ok=True)
    for rel, content in snapshot.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _write_diffs(patch_dir: Path, before: Dict[str, str], after: Dict[str, str]) -> List[str]:
    diffs: List[str] = []
    for key in sorted(set(before) | set(after)):
        a = before.get(key, "").splitlines(keepends=True)
        b = after.get(key, "").splitlines(keepends=True)
        if a == b:
            continue
        diff = "".join(difflib.unified_diff(a, b, fromfile=f"a/{key}", tofile=f"b/{key}"))
        if diff:
            diffs.append(diff)
            (patch_dir / f"{key}.diff").write_text(diff, encoding="utf-8")
            out = patch_dir / "tests" / "generated" / key
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("".join(b), encoding="utf-8")
    return diffs
