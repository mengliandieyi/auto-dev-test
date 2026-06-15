#!/usr/bin/env python3
"""
run.py — 统一 CLI 入口

  python run.py validate  --project <id> --prd <path>
  python run.py parse     --project <id> --prd <path>
  python run.py generate  --project <id> --prd-id <id> [--type e2e|component|all]
  python run.py report    --project <id> [--layer e2e|component|all]
  python run.py test      --project <id> [--layer e2e|component|all]  # 末尾自动 report
  python run.py generate-pipeline --project <id> --prd <path>   # 生成链路，不含 test
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "prd-parser"))
sys.path.insert(0, str(ROOT / "test-generator"))
sys.path.insert(0, str(ROOT / "component-generator"))


def _load_project_config(project_id: str) -> dict:
    import yaml
    config_path = ROOT / "config" / "projects" / f"{project_id}.yaml"
    if not config_path.exists():
        print(f"❌ 找不到项目配置：{config_path}")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        project_cfg = yaml.safe_load(f)
    global_path = ROOT / "config" / "global.yaml"
    global_cfg = {}
    if global_path.exists():
        with open(global_path, encoding="utf-8") as f:
            global_cfg = yaml.safe_load(f) or {}
    return {**global_cfg, **project_cfg}


def cmd_validate(args) -> int:
    from validator import validate
    result = validate(Path(args.prd))
    print(result.report(str(args.prd)))
    return 0 if result.valid else 1


def cmd_parse(args) -> int:
    from parse import parse
    try:
        output = parse(args.project, args.prd)
        print(f"✅ 中间产物已写入：{output}")
        return 0
    except SystemExit as e:
        return int(e.code) if e.code else 1
    except Exception as e:
        print(f"❌ 解析失败：{e}")
        return 1


def cmd_generate(args) -> int:
    gen_type = getattr(args, "type", "all") or "all"
    ok = True
    if gen_type in ("e2e", "all"):
        from generate import generate
        ok = generate(args.project, args.prd_id) and ok
    if gen_type in ("component", "all"):
        from generate_component import generate_component
        ok = generate_component(args.project, args.prd_id) and ok
    return 0 if ok else 1


def cmd_report(args) -> int:
    sys.path.insert(0, str(ROOT))
    from report import generate_report
    layer = getattr(args, "layer", "all") or "all"
    config = _load_project_config(args.project)
    generate_report(config, args.project, layer=layer)
    return 0


def cmd_test(args) -> int:
    layer = getattr(args, "layer", "all") or "all"
    rc = 0
    if layer in ("component", "all"):
        print("\n── 执行 Vitest 组件测试 ──")
        config = _load_project_config(args.project)
        vitest_cfg = config.get("vitest") or {}
        env = os.environ.copy()
        frontend_root = vitest_cfg.get("frontend_root", "../acme-web")
        env["VITEST_FRONTEND_ROOT"] = str((ROOT / frontend_root).resolve())
        r = subprocess.run(["npm", "run", "test:component"], cwd=ROOT, env=env)
        rc = rc or r.returncode
    if layer in ("e2e", "all"):
        print(f"\n── 执行 Playwright E2E（project={args.project}）──")
        r = subprocess.run(
            ["npx", "playwright", "test", f"--project={args.project}"],
            cwd=ROOT / "test-generator",
        )
        rc = rc or r.returncode

    print("\n── 刷新追溯报告（test 末尾自动 report）──")
    report_rc = cmd_report(args)
    return rc or report_rc


def cmd_generate_pipeline(args) -> int:
    print(f"\n{'='*50}")
    print(f"🚀 生成链路（不含 test）：project={args.project}, prd={args.prd}")
    print(f"{'='*50}\n")

    if cmd_validate(args) != 0:
        return 1
    if cmd_parse(args) != 0:
        return 1

    intermediate_dir = ROOT / "tests" / "intermediate" / args.project
    prd_stem = Path(args.prd).stem.split("_")[0]
    tc_file = intermediate_dir / f"{prd_stem}_test-cases.json"
    if not tc_file.exists():
        candidates = sorted(intermediate_dir.glob("*_test-cases.json"))
        if not candidates:
            print("❌ 找不到 test-cases.json")
            return 1
        tc_file = candidates[-1]

    with open(tc_file, encoding="utf-8") as f:
        prd_id = json.load(f).get("prd_id", prd_stem)

    args.prd_id = prd_id
    args.type = "all"
    if cmd_generate(args) != 0:
        return 1

    args.layer = "all"
    cmd_report(args)

    print(f"\n{'='*50}")
    print("✅ generate-pipeline 完成（生成链路）。执行测试请运行：")
    print(f"  python run.py test --project {args.project}")
    print(f"{'='*50}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="auto-dev-test 统一入口")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("validate", "parse"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.add_argument("--prd", required=True)

    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--project", required=True)
    p_gen.add_argument("--prd-id", required=True, dest="prd_id")
    p_gen.add_argument("--type", choices=["e2e", "component", "all"], default="all")

    p_rep = sub.add_parser("report")
    p_rep.add_argument("--project", required=True)
    p_rep.add_argument("--layer", choices=["e2e", "component", "all"], default="all")

    p_test = sub.add_parser("test", help="执行 Playwright / Vitest（需已生成脚本）")
    p_test.add_argument("--project", required=True)
    p_test.add_argument("--layer", choices=["e2e", "component", "all"], default="all")

    p_gp = sub.add_parser("generate-pipeline", help="生成链路：validate→parse→generate→report（不含 test）")
    p_gp.add_argument("--project", required=True)
    p_gp.add_argument("--prd", required=True)

    args = parser.parse_args()
    handlers = {
        "validate": cmd_validate,
        "parse": cmd_parse,
        "generate": cmd_generate,
        "report": cmd_report,
        "test": cmd_test,
        "generate-pipeline": cmd_generate_pipeline,
    }
    sys.exit(handlers[args.command](args) or 0)


if __name__ == "__main__":
    main()
