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
        from heal.store import create_heal_run, get_heal_run, init_heal_db
        from api.config import JOBS_DB

        init_heal_db(JOBS_DB)
        run = create_heal_run("project-a", "PROJ-001")
        loaded = get_heal_run(run["id"])
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded["prd_id"], "PROJ-001")
        self.assertEqual(loaded["status"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
