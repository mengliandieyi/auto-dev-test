"""追溯报告历史单测。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from report_history import archive_final_report, list_traceability_history, read_traceability_snapshot


class TestReportHistory(unittest.TestCase):
    def _isolate(self, tmp: str):
        import api.config as api_config
        import report_history as rh

        troot = Path(tmp)
        cfg = troot / "config" / "projects"
        cfg.mkdir(parents=True)
        (cfg / "project-a.yaml").write_text("project_id: project-a\n", encoding="utf-8")
        old_api = api_config.REPO_ROOT
        old_rh = rh.ROOT
        api_config.REPO_ROOT = troot
        rh.ROOT = troot
        return old_api, old_rh, api_config, rh, troot

    def test_archive_and_list_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_api, old_rh, api_config, rh, troot = self._isolate(tmp)
            try:
                report_dir = troot / "reports" / "project-a"
                report_dir.mkdir(parents=True)
                final = report_dir / "PROJ-001_traceability.txt"
                final.write_text("version-1\n", encoding="utf-8")
                archive_final_report("project-a", "PROJ-001")
                final.write_text("version-2\n", encoding="utf-8")
                history = list_traceability_history("project-a", "PROJ-001")
                self.assertGreaterEqual(len(history), 2)
                self.assertEqual(history[0]["snapshot_id"], "latest")
                archived = next(h for h in history if h["snapshot_id"] != "latest")
                snap = read_traceability_snapshot("project-a", "PROJ-001", archived["snapshot_id"])
                self.assertIn("version-1", snap["content"])
                latest = read_traceability_snapshot("project-a", "PROJ-001", "latest")
                self.assertIn("version-2", latest["content"])
            finally:
                api_config.REPO_ROOT = old_api
                rh.ROOT = old_rh


if __name__ == "__main__":
    unittest.main()
