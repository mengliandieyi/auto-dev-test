"""M4：Vitest forks 并行与单线程 baseline 结果一致。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _case_statuses(report_path: Path) -> dict[str, str]:
    if not report_path.exists():
        return {}
    data = json.loads(report_path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for file_result in data.get("testResults") or []:
        for ar in file_result.get("assertionResults") or []:
            title = ar.get("title") or ""
            m = re.match(r"^(CTC-\d+)", title)
            if m:
                out[m.group(1)] = ar.get("status") or "unknown"
    return out


def _run_vitest(*, single_thread: bool) -> int:
    env = os.environ.copy()
    env["VITEST_PROJECT_ID"] = "project-a"
    env["VITEST_PRD_ID"] = "PROJ-001"
    env["VITEST_FRONTEND_ROOT"] = str(ROOT / "tests/fixtures/mock-frontend")
    env["VITEST_REPORT_DIR"] = str(ROOT / "reports/project-a")
    if single_thread:
        env["VITEST_SINGLE_THREAD"] = "1"
    else:
        env.pop("VITEST_SINGLE_THREAD", None)
        env["VITEST_MAX_WORKERS"] = "2"
    report = ROOT / "reports/project-a/vitest-results.json"
    if report.exists():
        report.unlink()
    script = "test:component:single" if single_thread else "test:component"
    return subprocess.run(["npm", "run", script], cwd=ROOT, env=env).returncode


class TestVitestParallel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = ROOT / "reports/project-a/vitest-results.json"

    def test_forks_matches_single_thread_baseline(self):
        single_rc = _run_vitest(single_thread=True)
        single_status = _case_statuses(self.report)
        self.assertEqual(single_rc, 0, "单线程 baseline 应通过")
        self.assertIn("CTC-001", single_status)
        self.assertEqual(single_status["CTC-001"], "passed")

        forks_rc = _run_vitest(single_thread=False)
        forks_status = _case_statuses(self.report)
        self.assertEqual(forks_rc, 0, "forks 并行应通过")
        self.assertEqual(single_status, forks_status, "pass/fail 集合须与 baseline 一致")


if __name__ == "__main__":
    unittest.main()
