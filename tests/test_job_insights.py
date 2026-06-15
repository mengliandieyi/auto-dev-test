"""任务洞察与清理单测。"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.services.job_insights import classify_job_failure
from api.services import job_store


class TestJobInsights(unittest.TestCase):
    def test_classify_content_drift(self):
        hint = classify_job_failure("stderr: CONTENT_DRIFT\n", status="FAILED", exit_code=1)
        self.assertIn("version", hint or "")

    def test_classify_cancelled(self):
        self.assertEqual(classify_job_failure("", status="CANCELLED"), "用户取消")

    def test_prune_keeps_recent(self):
        for _ in range(4):
            job = job_store.create_job("project-a", "report", {})
            job_store.update_job_status(
                job["id"], "SUCCESS", finished_at=job_store._now(), exit_code=0
            )
        before = len(job_store.list_jobs(limit=100))
        removed = job_store.prune_jobs(keep=2)
        after = len(job_store.list_jobs(limit=100))
        self.assertGreaterEqual(removed, 1)
        self.assertLessEqual(after, before)


if __name__ == "__main__":
    unittest.main()
