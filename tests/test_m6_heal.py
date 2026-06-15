"""M6 heal 单测。"""

from __future__ import annotations

import unittest
from unittest.mock import patch



class TestM6Heal(unittest.TestCase):
    def test_preflight_mock_e2e(self):
        from heal.preflight import run_preflight

        ok, msg = run_preflight({"base_url": "http://127.0.0.1:4173", "health_check_url": "/health"})
        self.assertTrue(ok or "失败" in msg)

    def test_flaky_pattern(self):
        from heal.flaky import is_flaky_candidate

        self.assertTrue(is_flaky_candidate("Error: Timeout 30000ms exceeded"))
        self.assertFalse(is_flaky_candidate("AssertionError: expected true"))

    def test_heal_loop_success_when_test_passes(self):
        from heal.loop import run_heal_loop

        with patch("run.cmd_test", return_value=0), patch("run.cmd_report", return_value=0):
            rc = run_heal_loop("project-a", "PROJ-001", dry_run=True)
        self.assertEqual(rc, 0)

    def test_heal_store_roundtrip(self):
        from heal.store import _now, create_heal_run, get_heal_run, init_heal_db, update_heal_run
        from api.config import JOBS_DB

        init_heal_db(JOBS_DB)
        run = create_heal_run("project-a", "PROJ-001")
        loaded = get_heal_run(run["id"])
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded["prd_id"], "PROJ-001")
        self.assertEqual(loaded["status"], "RUNNING")
        update_heal_run(run["id"], status="ABORTED", abort_reason="TEST", finished_at=_now())

    def test_recover_stale_analyzed_legacy(self):
        from heal.store import (
            _now,
            create_heal_run,
            get_heal_run,
            init_heal_db,
            recover_stale_heal_runs,
            update_heal_run,
        )
        from api.config import JOBS_DB

        init_heal_db(JOBS_DB)
        run = create_heal_run("project-a", "PROJ-001")
        update_heal_run(
            run["id"],
            diagnosis_json={"category": "test_script", "summary": "legacy"},
        )
        n = recover_stale_heal_runs()
        self.assertGreaterEqual(n, 1)
        loaded = get_heal_run(run["id"])
        assert loaded is not None
        self.assertEqual(loaded["status"], "ANALYZED")

    def test_prune_heal_runs_keeps_recent(self):
        from heal.store import _now, create_heal_run, init_heal_db, prune_heal_runs, update_heal_run
        from api.config import JOBS_DB

        init_heal_db(JOBS_DB)
        ids = []
        for _ in range(4):
            run = create_heal_run("project-a", "PROJ-001")
            update_heal_run(run["id"], status="ANALYZED", finished_at=_now())
            ids.append(run["id"])
        removed = prune_heal_runs(keep=2, project_id="project-a", prd_id="PROJ-001")
        self.assertGreaterEqual(removed, 1)

    def test_healing_progress(self):
        from heal.progress import healing_improved, healing_stalled

        self.assertTrue(healing_improved(["a", "b"], ["a"]))
        self.assertFalse(healing_improved(["a"], ["a", "b"]))
        self.assertTrue(healing_stalled(["a", "b"], ["a", "b", "c"]))
        self.assertTrue(healing_stalled(["a"], ["b"]))

    def test_heal_loop_stops_on_no_improvement(self):
        from heal.loop import run_heal_loop

        failures = ["login should work"]
        analyze_calls = {"n": 0}

        def fake_analyze(*_args, **_kwargs):
            analyze_calls["n"] += 1
            return {"category": "test_script", "summary": "mock"}, 0.0

        with patch("run.cmd_test", return_value=1), patch("run.cmd_report", return_value=0), patch(
            "heal.flaky.extract_failures_from_reports",
            return_value=failures,
        ), patch("heal.flaky.collect_test_logs", return_value="AssertionError"), patch(
            "heal.preflight.run_preflight",
            return_value=(True, ""),
        ), patch("heal.flaky.is_flaky_candidate", return_value=False), patch(
            "heal.analyze.analyze_failure",
            side_effect=fake_analyze,
        ), patch("heal.fix.apply_fix", return_value=(["diff"], False)):
            rc = run_heal_loop("project-a", "PROJ-001", dry_run=True)

        self.assertEqual(rc, 1)
        self.assertEqual(analyze_calls["n"], 1)

    def test_heal_loop_stops_when_fix_empty(self):
        from heal.loop import run_heal_loop
        from heal.store import get_heal_run, init_heal_db, list_heal_runs
        from api.config import JOBS_DB

        init_heal_db(JOBS_DB)
        before = len(list_heal_runs("project-a", "PROJ-001"))

        with patch("run.cmd_test", return_value=1), patch("run.cmd_report", return_value=0), patch(
            "heal.flaky.extract_failures_from_reports",
            return_value=["only failure"],
        ), patch("heal.flaky.collect_test_logs", return_value="AssertionError"), patch(
            "heal.preflight.run_preflight",
            return_value=(True, ""),
        ), patch("heal.flaky.is_flaky_candidate", return_value=False), patch(
            "heal.analyze.analyze_failure",
            return_value=({"category": "test_script"}, 0.0),
        ), patch("heal.fix.apply_fix", return_value=([], False)):
            rc = run_heal_loop("project-a", "PROJ-001", dry_run=True)

        self.assertEqual(rc, 1)
        runs = list_heal_runs("project-a", "PROJ-001")
        self.assertGreater(len(runs), before)
        latest = runs[0]
        self.assertEqual(latest["abort_reason"], "NO_IMPROVEMENT")


if __name__ == "__main__":
    unittest.main()
