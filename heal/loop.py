"""heal-loop 编排（TECH §8.2）。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from bootstrap import ROOT, setup_repo_paths

setup_repo_paths()


def run_heal_loop(project_id: str, prd_id: str, *, dry_run: bool = True) -> int:
    from config_loader import load_project_config
    from heal.analyze import analyze_failure, is_prd_drift
    from heal.fix import apply_fix, plan_fix
    from heal.flaky import collect_test_logs, extract_failures_from_reports, is_flaky_candidate
    from heal.preflight import run_preflight
    from heal.store import create_heal_run, read_patch_preview, update_heal_run
    from run import cmd_report, cmd_test

    config = load_project_config(project_id)
    heal_cfg = config.get("heal") or {}
    max_iter = int(heal_cfg.get("max_iterations", 3))
    wall_clock = int(heal_cfg.get("wall_clock_sec", 900))
    token_limit = float(heal_cfg.get("token_limit_per_run", 50000))

    run = create_heal_run(
        project_id,
        prd_id,
        max_iterations=max_iter,
        token_limit=token_limit,
        wall_clock_sec=wall_clock,
    )
    run_id = run["id"]
    patch_dir = Path(run["patch_dir"])
    (patch_dir / "meta.txt").write_text(prd_id, encoding="utf-8")
    report_dir = ROOT / "reports" / project_id
    started = time.time()

    from types import SimpleNamespace

    args = SimpleNamespace(project=project_id, prd_id=prd_id, layer="all", skeleton=False)
    print(f"\n🩹 heal-loop 开始：{project_id} / {prd_id} · run={run_id[:8]}")

    iteration = 0
    token_cost = 0.0
    while iteration < max_iter:
        if time.time() - started > wall_clock:
            update_heal_run(
                run_id,
                status="ABORTED",
                abort_reason="WALL_CLOCK",
                finished_at=_now(),
                iteration=iteration,
                token_cost=token_cost,
            )
            print("ABORTED: WALL_CLOCK", file=sys.stderr)
            return 1

        iteration += 1
        update_heal_run(run_id, iteration=iteration)

        rc = cmd_test(args)
        if rc == 0:
            update_heal_run(
                run_id,
                status="SUCCESS",
                finished_at=_now(),
                iteration=iteration,
                token_cost=token_cost,
            )
            print(f"✅ heal-loop SUCCESS（迭代 {iteration}）")
            return 0

        cmd_report(args)
        logs = collect_test_logs(report_dir)
        failures = extract_failures_from_reports(report_dir)
        report_path = report_dir / f"{prd_id}_traceability.txt"
        report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else logs

        pre_ok, pre_msg = run_preflight(config)
        flaky = is_flaky_candidate(logs, base_unreachable=not pre_ok)
        if flaky:
            print("  ↻ flaky 候选，原样重跑 test 一次…")
            rc2 = cmd_test(args)
            if rc2 == 0:
                update_heal_run(
                    run_id,
                    status="SUCCESS",
                    finished_at=_now(),
                    iteration=iteration,
                    token_cost=token_cost,
                )
                print("✅ flaky 重跑后 PASS")
                return 0
            update_heal_run(
                run_id,
                status="ABORTED",
                abort_reason="FLAKY_EXHAUSTED",
                finished_at=_now(),
                iteration=iteration,
                token_cost=token_cost,
            )
            print("ABORTED: FLAKY_EXHAUSTED", file=sys.stderr)
            return 1

        if not pre_ok:
            update_heal_run(
                run_id,
                status="ABORTED",
                abort_reason="CONFIG_ENV",
                finished_at=_now(),
                iteration=iteration,
                token_cost=token_cost,
            )
            print(f"ABORTED: CONFIG_ENV — {pre_msg}", file=sys.stderr)
            return 1

        diagnosis, cost = analyze_failure(project_id, prd_id, config, failures, report_text)
        token_cost += cost
        update_heal_run(run_id, diagnosis_json=diagnosis, token_cost=token_cost)

        if token_cost > token_limit:
            update_heal_run(
                run_id,
                status="ABORTED",
                abort_reason="TOKEN_LIMIT",
                finished_at=_now(),
            )
            print("ABORTED: TOKEN_LIMIT", file=sys.stderr)
            return 1

        if is_prd_drift(diagnosis):
            plan = plan_fix(diagnosis)
            apply_fix(project_id, prd_id, plan, patch_dir, dry_run=True)
            update_heal_run(
                run_id,
                status="ABORTED",
                abort_reason="PRD_DRIFT",
                fix_plan_json=plan,
                finished_at=_now(),
            )
            print("ABORTED: PRD_DRIFT（仅 diff 预览，不写 PRD）", file=sys.stderr)
            print(read_patch_preview(run_id)[:2000])
            return 1

        plan = plan_fix(diagnosis)
        update_heal_run(run_id, fix_plan_json=plan)
        _, applied = apply_fix(project_id, prd_id, plan, patch_dir, dry_run=dry_run)
        if dry_run:
            print(f"  dry-run 补丁预览：{patch_dir}")
            print(read_patch_preview(run_id)[:1500])

    update_heal_run(
        run_id,
        status="ABORTED",
        abort_reason="MAX_ITERATIONS",
        finished_at=_now(),
        iteration=iteration,
        token_cost=token_cost,
    )
    print("ABORTED: MAX_ITERATIONS", file=sys.stderr)
    return 1


def _now() -> str:
    from heal.store import _now as store_now

    return store_now()
