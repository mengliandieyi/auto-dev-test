"""Flaky 判定（TECH §8.3）。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

FLAKY_PATTERNS = (
    "Timeout",
    "ETIMEDOUT",
    "ECONNRESET",
    "ENOTFOUND",
    "net::ERR_",
)


def is_flaky_candidate(log_text: str, *, base_unreachable: bool = False) -> bool:
    if base_unreachable:
        return True
    return any(p in log_text for p in FLAKY_PATTERNS)


def collect_test_logs(report_dir: Path) -> str:
    parts: List[str] = []
    for name in ("pw-results.json", "vitest-results.json"):
        p = report_dir / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
    logs = report_dir.parent.parent / "logs" / "jobs"
    if logs.is_dir():
        for p in sorted(logs.glob("*.log"))[-3:]:
            parts.append(p.read_text(encoding="utf-8", errors="replace")[-8000:])
    return "\n".join(parts)


def extract_failures_from_reports(report_dir: Path) -> List[str]:
    import json

    failed: List[str] = []
    pw = report_dir / "pw-results.json"
    if pw.exists():
        data = json.loads(pw.read_text(encoding="utf-8"))

        def walk(suites: list) -> None:
            for suite in suites or []:
                for spec in suite.get("specs") or []:
                    title = spec.get("title") or ""
                    tests = spec.get("tests") or []
                    if tests and (tests[0].get("results") or [{}])[0].get("status") == "failed":
                        failed.append(title)
                walk(suite.get("suites") or [])

        walk(data.get("suites") or [])
    vt = report_dir / "vitest-results.json"
    if vt.exists():
        data = json.loads(vt.read_text(encoding="utf-8"))
        for fr in data.get("testResults") or []:
            for ar in fr.get("assertionResults") or []:
                if ar.get("status") == "failed":
                    failed.append(ar.get("title") or "unknown")
    return failed
