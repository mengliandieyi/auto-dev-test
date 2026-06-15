"""
report.py — PRD 可追溯矩阵报告（支持分层 e2e / component）

无当次测试结果时，用例状态为 NOT_RUN（骨架报告），不报错中止。
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from meta_db import db_path_for_project, ensure_project_db

ROOT = Path(__file__).parent


def generate_report(config: dict, project_id: str, layer: str = "all"):
    report_dir = ROOT / "reports" / project_id
    report_dir.mkdir(parents=True, exist_ok=True)

    layers = ["e2e", "component"] if layer == "all" else [layer]
    db_path = ensure_project_db(project_id)

    specs = _load_specs(db_path, project_id, layers)
    if not specs:
        specs = _specs_from_intermediate(project_id, layers)

    if not specs:
        print(f"⚠️  项目 {project_id} 暂无生成记录或中间产物")
        return

    pw_results = _load_playwright_results(project_id)
    vitest_results = _load_vitest_results()
    has_run = bool(pw_results or vitest_results)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    by_prd: dict[str, list] = {}
    for spec in specs:
        by_prd.setdefault(spec["prd_id"], []).append(spec)

    all_lines = [
        f"PRD 可追溯矩阵 — {project_id}",
        f"生成时间：{generated_at}",
        "",
    ]

    for prd_id, prd_specs in by_prd.items():
        prd_lines = _build_prd_report(
            project_id, prd_id, prd_specs, has_run, pw_results, vitest_results, generated_at
        )
        prd_path = report_dir / f"{prd_id}_traceability.txt"
        prd_path.write_text("\n".join(prd_lines), encoding="utf-8")
        print(f"✅ 追溯报告：{prd_path}")
        all_lines.extend(prd_lines)
        all_lines.append("")

    combined = "\n".join(all_lines).rstrip() + "\n"
    (report_dir / "traceability.txt").write_text(combined, encoding="utf-8")
    (report_dir / "latest_traceability.txt").write_text(combined, encoding="utf-8")


def _build_prd_report(
    project_id: str,
    prd_id: str,
    prd_specs: list,
    has_run: bool,
    pw_results: dict,
    vitest_results: dict,
    generated_at: str,
) -> list:
    tc_file = ROOT / "tests" / "intermediate" / project_id / f"{prd_id}_test-cases.json"
    tc_data = {}
    if tc_file.exists():
        with open(tc_file, encoding="utf-8") as f:
            tc_data = json.load(f)
    feature_name = tc_data.get("feature_name") or tc_data.get("feature") or prd_id
    version = tc_data.get("prd_version", "?")

    lines = [
        f"PRD {prd_id} v{version} — {feature_name}",
        f"项目：{project_id}  生成时间：{generated_at}",
        "",
    ]
    if not has_run:
        lines += ["（骨架报告：尚未执行 test，用例状态为 NOT_RUN）", ""]

    for spec in prd_specs:
        lyr = spec["layer"]
        if lyr == "e2e":
            cases = tc_data.get("e2e_test_cases") or []
            results = pw_results
            label = "E2E（Playwright）"
        else:
            cases = tc_data.get("component_test_cases") or []
            results = vitest_results
            label = "组件（Vitest）"

        lines += [f"── {label} ──", f"脚本：{spec['spec_file']}", ""]
        lines.append(f"{'验收标准':<36} {'用例':<10} 结果")
        lines.append("-" * 60)

        passed = failed = not_run = 0
        for tc in cases:
            tc_id = tc.get("id", "?")
            criterion = (tc.get("source_criterion") or "")[:34]
            result = results.get(tc_id)
            if result is None:
                result = "NOT_RUN" if not has_run else "SKIP"
            if result == "PASS":
                icon, passed = "✅", passed + 1
            elif result == "FAIL":
                icon, failed = "❌", failed + 1
            elif result == "NOT_RUN":
                icon, not_run = "⏳", not_run + 1
            else:
                icon = "⏸️"
            lines.append(f"{icon} {criterion:<34} {tc_id:<10} {result}")

        total = len(cases)
        crit = spec.get("criteria_count") or total
        lines += [
            "-" * 60,
            f"覆盖率(用例数): {total}/{crit}  "
            f"已执行: PASS {passed} / FAIL {failed} / NOT_RUN {not_run}",
            "",
        ]
    return lines


def _load_specs(db_path: Path, project_id: str, layers: list) -> list:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM generated_specs WHERE project_id=? ORDER BY prd_id, layer",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows if r["layer"] in layers]


def _specs_from_intermediate(project_id: str, layers: list) -> list:
    """无 meta.db 时从 intermediate + generated 推断（骨架）。"""
    inter_dir = ROOT / "tests" / "intermediate" / project_id
    if not inter_dir.exists():
        return []
    specs = []
    for tc_file in inter_dir.glob("*_test-cases.json"):
        prd_id = tc_file.stem.replace("_test-cases", "")
        with open(tc_file, encoding="utf-8") as f:
            tc_data = json.load(f)
        version = tc_data.get("prd_version", "?")
        if "e2e" in layers:
            for p in (ROOT / "tests" / "generated" / project_id / "e2e").glob(f"{prd_id}_*.spec.ts"):
                specs.append({
                    "prd_id": prd_id,
                    "layer": "e2e",
                    "spec_file": str(p.relative_to(ROOT)),
                    "criteria_count": len(tc_data.get("e2e_test_cases") or []),
                    "covered_count": 0,
                    "prd_version": version,
                    "project_id": project_id,
                })
        if "component" in layers:
            comp_dir = ROOT / "tests" / "generated" / project_id / "component"
            for p in comp_dir.glob(f"{prd_id}_*.test.tsx"):
                specs.append({
                    "prd_id": prd_id,
                    "layer": "component",
                    "spec_file": str(p.relative_to(ROOT)),
                    "criteria_count": len(tc_data.get("component_test_cases") or []),
                    "covered_count": 0,
                    "prd_version": version,
                    "project_id": project_id,
                })
    return specs


def _load_playwright_results(project_id: str) -> dict:
    path = ROOT / "reports" / project_id / "pw-results.json"
    if not path.exists():
        path = ROOT / "reports" / "pw-results.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    mapping = {}
    for suite in data.get("suites", []):
        for spec in suite.get("specs", []):
            title = spec.get("title", "")
            status = "PASS" if spec.get("ok") else "FAIL"
            for prefix in ("ETC-", "TC-"):
                for word in title.split():
                    if word.startswith(prefix):
                        mapping[word.rstrip("]")[:10]] = status
    return mapping


def _load_vitest_results() -> dict:
    path = ROOT / "reports" / "vitest-results.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    mapping = {}
    for f in data.get("testResults", []):
        for a in f.get("assertionResults", []):
            title = a.get("title", "")
            status = "PASS" if a.get("status") == "passed" else "FAIL"
            for prefix in ("CTC-", "TC-"):
                for word in title.split():
                    if word.startswith(prefix):
                        mapping[word] = status
    return mapping
