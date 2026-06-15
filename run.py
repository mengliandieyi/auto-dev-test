#!/usr/bin/env python3
"""auto-dev-test CLI（M1–M6）。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from bootstrap import ROOT, setup_repo_paths

setup_repo_paths()
from env_store import ensure_env_loaded  # noqa: E402

ensure_env_loaded()


def _load_config(project_id: str) -> dict:
    from config_loader import load_project_config

    return load_project_config(project_id)


def _resolve_cli_prd(project_id: str, prd_rel: str) -> Path:
    from fastapi import HTTPException
    from api.services.path_safety import resolve_prd_path

    try:
        return resolve_prd_path(project_id, prd_rel)
    except HTTPException as exc:
        raise SystemExit(str(exc.detail)) from exc


def cmd_validate(args) -> int:
    from validator import validate

    try:
        prd_path = _resolve_cli_prd(args.project, args.prd)
    except SystemExit as exc:
        print(f"❌ PRD 路径无效：{exc}")
        return 1
    result = validate(prd_path, expected_project=args.project)
    print(result.report(str(prd_path)))
    return 0 if result.valid else 2


def cmd_parse(args) -> int:
    from parse import parse

    try:
        prd_path = _resolve_cli_prd(args.project, args.prd)
    except SystemExit as exc:
        print(f"❌ PRD 路径无效：{exc}")
        return 1
    args.prd = str(prd_path)
    try:
        output = parse(args.project, args.prd)
        print(f"✅ 中间产物：{output}")
        return 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1
    except Exception as e:
        print(f"❌ 解析失败：{e}")
        return 1


def cmd_generate(args) -> int:
    force = getattr(args, "force", False)
    gen_type = getattr(args, "type", "all") or "all"
    ok = True
    if gen_type in ("e2e", "all"):
        from generate import generate

        ok = generate(args.project, args.prd_id, force=force) and ok
    if gen_type in ("component", "all"):
        from generate_component import generate_component

        ok = generate_component(args.project, args.prd_id, force=force) and ok
    return 0 if ok else 1


def cmd_report(args) -> int:
    from report import generate_report

    config = _load_config(args.project)
    generate_report(
        config,
        args.project,
        layer=getattr(args, "layer", "all") or "all",
        prd_id=getattr(args, "prd_id", None),
        skeleton=getattr(args, "skeleton", False),
    )
    return 0


def cmd_test(args) -> int:
    layer = getattr(args, "layer", "all") or "all"
    config = _load_config(args.project)
    rc = 0
    report_dir = ROOT / "reports" / args.project
    report_dir.mkdir(parents=True, exist_ok=True)

    if layer in ("component", "all"):
        vitest_cfg = config.get("vitest") or {}
        if vitest_cfg.get("enabled", True):
            print("\n── Vitest 组件测试 ──")
            env = os.environ.copy()
            frontend_root = vitest_cfg.get("frontend_root", "./tests/fixtures/mock-frontend")
            env["VITEST_FRONTEND_ROOT"] = str((ROOT / frontend_root).resolve())
            env["VITEST_REPORT_DIR"] = str(report_dir)
            env["VITEST_PROJECT_ID"] = args.project
            if getattr(args, "prd_id", None):
                env["VITEST_PRD_ID"] = args.prd_id
                print(f"  按 PRD 过滤：{args.prd_id}")
            max_workers = vitest_cfg.get("max_workers")
            if max_workers is not None:
                env["VITEST_MAX_WORKERS"] = str(max_workers)
            pool = vitest_cfg.get("pool", "forks")
            if pool != "forks" and not os.getenv("VITEST_SINGLE_THREAD"):
                print(f"  ⚠️  M4 推荐 vitest.pool=forks，当前配置：{pool}", file=sys.stderr)
            r = subprocess.run(["npm", "run", "test:component"], cwd=ROOT, env=env)
            rc = rc or r.returncode

    if layer in ("e2e", "all"):
        print(f"\n── Playwright E2E（{args.project}）──")
        from playwright_runtime import export_playwright_runtime

        export_playwright_runtime(ROOT)
        env = os.environ.copy()
        env["PLAYWRIGHT_ACTIVE_PROJECT"] = args.project
        proj_env_key = f"PROJECT_{args.project.upper().replace('-', '_')}_BASE_URL"
        env[proj_env_key] = config.get("base_url", "http://127.0.0.1:4173")
        env["PLAYWRIGHT_REPORT_DIR"] = str(report_dir)
        r = subprocess.run(
            ["npx", "playwright", "test", "--config=test-generator/playwright.config.ts", f"--project={args.project}"],
            cwd=ROOT,
            env=env,
        )
        rc = rc or r.returncode

    print("\n── 刷新追溯报告 ──")
    cmd_report(args)
    return rc


def _resolve_prd_id(project: str, prd_path: str) -> str:
    inter = ROOT / "tests/intermediate" / project
    stem = Path(prd_path).stem.split("_")[0]
    tc = inter / f"{stem}_test-cases.json"
    if tc.exists():
        return json.loads(tc.read_text(encoding="utf-8")).get("prd_id", stem)
    return stem


def cmd_generate_pipeline(args) -> int:
    print(f"\n{'=' * 50}\n🚀 generate-pipeline：{args.project} / {args.prd}\n{'=' * 50}\n")
    if cmd_validate(args) != 0:
        return 1
    if cmd_parse(args) != 0:
        return 1
    args.prd_id = _resolve_prd_id(args.project, args.prd)
    args.type = "all"
    args.force = getattr(args, "force", False)
    if cmd_generate(args) != 0:
        return 1
    args.skeleton = True
    return cmd_report(args)


def cmd_run_full(args) -> int:
    rc = cmd_generate_pipeline(args)
    if rc != 0:
        return rc
    args.layer = "all"
    return cmd_test(args)


def cmd_heal_loop(args) -> int:
    from heal.loop import run_heal_loop

    dry_run = not getattr(args, "apply", False)
    return run_heal_loop(args.project, args.prd_id, dry_run=dry_run)


def cmd_dev(args) -> int:
    from heal.dev import run_dev

    try:
        prd_path = _resolve_cli_prd(args.project, args.prd)
    except SystemExit as exc:
        print(f"❌ PRD 路径无效：{exc}")
        return 1
    return run_dev(
        args.project,
        str(prd_path),
        layer=getattr(args, "layer", "all"),
        skill_frontend=getattr(args, "skill_frontend", None),
        skill_backend=getattr(args, "skill_backend", None),
    )


def main():
    parser = argparse.ArgumentParser(description="auto-dev-test CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("validate", "parse"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.add_argument("--prd", required=True)

    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--project", required=True)
    p_gen.add_argument("--prd-id", required=True, dest="prd_id")
    p_gen.add_argument("--type", choices=["e2e", "component", "all"], default="all")
    p_gen.add_argument("--force", action="store_true")

    p_rep = sub.add_parser("report")
    p_rep.add_argument("--project", required=True)
    p_rep.add_argument("--layer", choices=["e2e", "component", "all"], default="all")
    p_rep.add_argument("--prd-id", dest="prd_id", default=None)

    p_test = sub.add_parser("test")
    p_test.add_argument("--project", required=True)
    p_test.add_argument("--layer", choices=["e2e", "component", "all"], default="all")
    p_test.add_argument("--prd-id", dest="prd_id", default=None)

    for name, extra in (
        ("generate-pipeline", True),
        ("run-full", True),
    ):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.add_argument("--prd", required=True)
        if extra:
            p.add_argument("--force", action="store_true")

    p_heal = sub.add_parser("heal-loop")
    p_heal.add_argument("--project", required=True)
    p_heal.add_argument("--prd-id", required=True, dest="prd_id")
    p_heal.add_argument("--apply", action="store_true", help="应用 test_script 修复（默认 dry-run）")

    p_dev = sub.add_parser("dev")
    p_dev.add_argument("--project", required=True)
    p_dev.add_argument("--prd", required=True)
    p_dev.add_argument("--layer", choices=["frontend", "backend", "all"], default="all")
    p_dev.add_argument("--skill-frontend", dest="skill_frontend", default=None)
    p_dev.add_argument("--skill-backend", dest="skill_backend", default=None)

    args = parser.parse_args()
    handlers = {
        "validate": cmd_validate,
        "parse": cmd_parse,
        "generate": cmd_generate,
        "report": cmd_report,
        "test": cmd_test,
        "generate-pipeline": cmd_generate_pipeline,
        "run-full": cmd_run_full,
        "heal-loop": cmd_heal_loop,
        "dev": cmd_dev,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
