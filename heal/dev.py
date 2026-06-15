"""run.py dev — OpenHands 业务代码叠加（TECH §8.1）。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_dev(project_id: str, prd_path: str) -> int:
    sys.path.insert(0, str(ROOT))
    from config_loader import load_project_config
    from content_fingerprint import find_prd_path

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
    typeui = config.get("typeui") or {}
    skill = typeui.get("skill_path", "./design/SKILL.md")
    skill_path = (ROOT / skill).resolve()

    print("\n🔧 dev — 业务代码开发（OpenHands）")
    print(f"  项目：{project_id}")
    print(f"  PRD：{prd}")
    print(f"  repos：{repos}")
    print(f"  skill：{skill_path}")

    openhands = shutil.which("openhands") or shutil.which("openhands-cli")
    if not openhands:
        print("\n⚠️  未检测到 OpenHands CLI。请安装后重试，或手动在 repos 路径开发：")
        for name, rel in repos.items():
            target = (ROOT / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
            print(f"  - {name}: {target}")
        print("\n提示：dev 不修改 tests/generated/ 幂等逻辑。")
        return 0

    env = os.environ.copy()
    env["AUTO_DEV_PROJECT"] = project_id
    env["AUTO_DEV_PRD"] = str(prd.resolve())
    if skill_path.is_file():
        env["TYPEUI_SKILL_PATH"] = str(skill_path)

    cmd = [
        openhands,
        "run",
        "--task",
        f"根据 PRD {prd.name} 在业务仓实现功能；遵循 {skill_path}",
    ]
    print(f"\n执行：{' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(ROOT), env=env).returncode
