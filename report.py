"""追溯报告（TECH §3.8）。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).parent


def _load_playwright_results(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, str] = {}

    def walk_suites(suites: list) -> None:
        for suite in suites or []:
            for spec in suite.get("specs") or []:
                title = spec.get("title") or ""
                m = re.match(r"^(ETC-\d+)", title)
                if not m:
                    continue
                cid = m.group(1)
                tests = spec.get("tests") or []
                status = "NOT_RUN"
                if tests:
                    results = (tests[0].get("results") or [{}])[0]
                    st = results.get("status") or tests[0].get("status")
                    if st == "passed":
                        status = "PASS"
                    elif st == "failed":
                        status = "FAIL"
                    elif st == "skipped":
                        status = "SKIP"
                out[cid] = status
            walk_suites(suite.get("suites") or [])

    walk_suites(data.get("suites") or [])
    return out


def _load_vitest_results(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, str] = {}
    for file_result in data.get("testResults") or []:
        for ar in file_result.get("assertionResults") or []:
            title = ar.get("title") or ""
            m = re.match(r"^(CTC-\d+)", title)
            if not m:
                continue
            st = ar.get("status")
            if st == "passed":
                out[m.group(1)] = "PASS"
            elif st == "failed":
                out[m.group(1)] = "FAIL"
            elif st == "skipped":
                out[m.group(1)] = "SKIP"
    return out


def _load_results(path: Path, runner: str) -> Dict[str, str]:
    if runner == "playwright":
        return _load_playwright_results(path)
    return _load_vitest_results(path)


def _criteria_from_prd(prd_id: str, project_id: str) -> List[str]:
    prd_dir = ROOT / "prds" / project_id
    for p in prd_dir.glob(f"{prd_id}_*.md"):
        text = p.read_text(encoding="utf-8")
        sec = re.search(r"## 验收标准\s*\n(.*?)(?=\n## |\Z)", text, re.S)
        if not sec:
            return []
        items = []
        for line in sec.group(1).splitlines():
            m = re.match(r"^- \[[ x]\]\s+(.+)$", line.strip())
            if m:
                items.append(m.group(1).strip())
        return items
    return []


def generate_report(
    config: dict,
    project_id: str,
    layer: str = "all",
    prd_id: Optional[str] = None,
    *,
    skeleton: bool = False,
):
    report_dir = ROOT / "reports" / project_id
    report_dir.mkdir(parents=True, exist_ok=True)

    inter_dir = ROOT / "tests/intermediate" / project_id
    if not inter_dir.exists():
        print(f"⚠️  无 intermediate：{inter_dir}")
        return

    pw = _load_results(report_dir / "pw-results.json", "playwright")
    vt = _load_results(report_dir / "vitest-results.json", "vitest")
    has_run = bool(pw or vt)
    run_at = datetime.now(timezone.utc).isoformat()

    for tc_file in sorted(inter_dir.glob("*_test-cases.json")):
        pid = tc_file.stem.replace("_test-cases", "")
        if prd_id and pid != prd_id:
            continue
        data = json.loads(tc_file.read_text(encoding="utf-8"))
        lines = _build_report(data, project_id, pw, vt, has_run, run_at)
        if skeleton:
            out = report_dir / f"{pid}_traceability.skeleton.txt"
        else:
            from report_history import archive_final_report

            archive_final_report(project_id, pid)
            out = report_dir / f"{pid}_traceability.txt"
            sk = report_dir / f"{pid}_traceability.skeleton.txt"
            if sk.exists():
                sk.unlink()
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        kind = "skeleton" if skeleton else "final"
        print(f"✅ 追溯报告（{kind}）：{out}")


def _build_report(data: dict, project_id: str, pw: dict, vt: dict, has_run: bool, run_at: str) -> List[str]:
    prd_id = data["prd_id"]
    version = data.get("prd_version", "?")
    feature = data.get("feature_name") or prd_id
    criteria = _criteria_from_prd(prd_id, project_id) or [
        (c.get("source_criterion") or "") for c in (data.get("e2e_test_cases") or [])
    ]

    etc = data.get("e2e_test_cases") or []
    ctc = data.get("component_test_cases") or []
    mapped = len(etc) + len(ctc)

    def lookup(tc_id: str, layer: str) -> str:
        if not has_run:
            return "NOT_RUN"
        res = pw.get(tc_id) if layer == "e2e" else vt.get(tc_id)
        return res or "NOT_COVERED"

    executed = passed = failed = 0
    rows: List[str] = []

    for i, crit in enumerate(criteria, 1):
        etc_match = next((e for e in etc if crit in (e.get("source_criterion") or "")), None)
        cid = etc_match["id"] if etc_match else "—"
        st = lookup(cid, "e2e") if etc_match else "NOT_COVERED"
        if st in ("PASS", "FAIL"):
            executed += 1
            passed += st == "PASS"
            failed += st == "FAIL"
        rows.append(f"| {i} | {crit[:28]}... | {cid} | {st} | |")

    for tc in ctc:
        st = lookup(tc["id"], "component")
        if st in ("PASS", "FAIL"):
            executed += 1
            passed += st == "PASS"
            failed += st == "FAIL"
        rows.append(f"|   | （组件）{tc.get('title', '')} | {tc['id']} | {st} | |")

    case_statuses = [lookup(t["id"], "e2e") for t in etc] + [lookup(t["id"], "component") for t in ctc]
    overall = "NOT_RUN"
    if has_run:
        overall = "PASS" if case_statuses and all(s == "PASS" for s in case_statuses) else "FAIL"
    uncovered = max(0, len(criteria) + len(ctc) - executed)

    lines = [
        f"# 追溯报告 · {prd_id} v{version} · {feature}",
        f"生成时间: {run_at}",
        f"测试执行: {run_at if has_run else '—'} | 总体: {overall}",
        "",
        "## 覆盖率",
        f"验收标准: {len(criteria)} | 已映射: {mapped} | 已执行: {executed} | "
        f"PASS: {passed} | FAIL: {failed} | 未覆盖: {uncovered}",
        "",
        "## 明细",
        "| # | 验收标准（摘要） | 用例 | 状态 | 备注 |",
        "|---|----------------|------|------|------|",
        *rows,
    ]
    return lines
