"""run.py dev — OpenHands 业务代码叠加（按前端/后端分层）。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
VALID_LAYERS = frozenset({"frontend", "backend", "all"})


def _resolve_repo_path(repos: Dict[str, Any], layer: str) -> Optional[Path]:
    rel = repos.get(layer)
    if not rel:
        return None
    p = Path(str(rel))
    return (ROOT / p).resolve() if not p.is_absolute() else p.resolve()


def _resolve_skill_for_layer(
    config: Dict[str, Any],
    layer: str,
    overrides: Optional[Dict[str, str]] = None,
) -> Optional[Path]:
    sys.path.insert(0, str(ROOT))
    from skills_registry import resolve_skill_path

    if overrides and overrides.get(layer):
        return resolve_skill_path(str(overrides[layer]))

    dev = config.get("dev") if isinstance(config.get("dev"), dict) else {}
    skill_id = dev.get(f"{layer}_skill")
    if skill_id:
        return resolve_skill_path(str(skill_id))

    if layer == "frontend":
        typeui = config.get("typeui") or {}
        legacy = typeui.get("skill_path", "./design/SKILL.md")
        legacy_path = (ROOT / legacy).resolve()
        if legacy_path.is_file():
            return legacy_path
    return None


def _run_layer_dev(
    *,
    project_id: str,
    prd: Path,
    layer: str,
    repo_path: Path,
    skill_path: Optional[Path],
    openhands: str,
) -> int:
    env = os.environ.copy()
    env["AUTO_DEV_PROJECT"] = project_id
    env["AUTO_DEV_PRD"] = str(prd.resolve())
    env["AUTO_DEV_LAYER"] = layer
    env["AUTO_DEV_REPO"] = str(repo_path)
    if skill_path and skill_path.is_file():
        env["TYPEUI_SKILL_PATH"] = str(skill_path)

    skill_hint = str(skill_path) if skill_path else "（无 Skill）"
    task = (
        f"根据 PRD {prd.name} 在 {layer} 业务仓 {repo_path} 实现功能；"
        f"工作目录为业务仓；遵循 Skill：{skill_hint}；"
        "不要修改 tests/generated/ 下的测试产物。"
    )
    cmd = [openhands, "run", "--task", task]
    print(f"\n执行 [{layer}]：{' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(repo_path), env=env).returncode


def run_dev(
    project_id: str,
    prd_path: str,
    layer: str = "all",
    skill_frontend: Optional[str] = None,
    skill_backend: Optional[str] = None,
) -> int:
    sys.path.insert(0, str(ROOT))
    from config_loader import load_project_config
    from content_fingerprint import find_prd_path

    layer = (layer or "all").strip().lower()
    if layer not in VALID_LAYERS:
        print(f"❌ 无效 layer：{layer}（可选 frontend / backend / all）", file=sys.stderr)
        return 1

    config = load_project_config(project_id)
    prd = Path(prd_path)
    if not prd.is_file():
        found = find_prd_path(project_id, prd.stem.split("_")[0], ROOT)
        if found:
            prd = found
    if not prd.is_file():
        print(f"❌ PRD 不存在：{prd_path}", file=sys.stderr)
        return 1

    repos = config.get("repos") or {}
    layers: List[str] = ["frontend", "backend"] if layer == "all" else [layer]
    skill_overrides: Dict[str, str] = {}
    if skill_frontend and skill_frontend.strip():
        skill_overrides["frontend"] = skill_frontend.strip()
    if skill_backend and skill_backend.strip():
        skill_overrides["backend"] = skill_backend.strip()

    print("\n🔧 dev — 业务代码开发（OpenHands）")
    print(f"  项目：{project_id}")
    print(f"  PRD：{prd}")
    print(f"  范围：{layer}")

    openhands = shutil.which("openhands") or shutil.which("openhands-cli")
    if not openhands:
        print("\n⚠️  未检测到 OpenHands CLI。请安装后重试，或手动在 repos 路径开发：")
        for lyr in layers:
            target = _resolve_repo_path(repos, lyr)
            skill = _resolve_skill_for_layer(config, lyr, skill_overrides)
            print(f"  - {lyr}: repo={target or '未配置'}, skill={skill or '无'}")
        print("\n提示：dev 不修改 tests/generated/ 幂等逻辑。")
        return 0

    exit_code = 0
    ran_any = False
    for lyr in layers:
        repo_path = _resolve_repo_path(repos, lyr)
        if not repo_path:
            print(f"\n⚠️  未配置 repos.{lyr}，跳过")
            continue
        skill_path = _resolve_skill_for_layer(config, lyr, skill_overrides)
        print(f"\n── {lyr} ──")
        print(f"  repo：{repo_path}")
        print(f"  skill：{skill_path or '（无）'}")
        if not repo_path.is_dir():
            print(f"⚠️  仓库路径不存在：{repo_path}，跳过")
            continue
        ran_any = True
        rc = _run_layer_dev(
            project_id=project_id,
            prd=prd,
            layer=lyr,
            repo_path=repo_path,
            skill_path=skill_path,
            openhands=openhands,
        )
        exit_code = max(exit_code, rc)

    if not ran_any:
        print("\n❌ 没有可执行的仓库（请先在项目配置中填写前端/后端仓库路径）", file=sys.stderr)
        return 1
    return exit_code
