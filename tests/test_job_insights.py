"""任务洞察与清理单测。"""

import unittest

from api.services.job_insights import classify_job_failure
from api.services import job_store


class TestJobInsights(unittest.TestCase):
    def test_classify_content_drift(self):
        hint = classify_job_failure("stderr: CONTENT_DRIFT\n", status="FAILED", exit_code=1)
        self.assertIn("version", hint or "")

    def test_classify_cancelled(self):
        self.assertEqual(classify_job_failure("", status="CANCELLED"), "用户取消")

    def test_classify_job_event_error(self):
        log = '[job-event] {"job_id":"x","event":"error","message":"disk full"}\n'
        hint = classify_job_failure(log, status="FAILED", exit_code=1)
        self.assertEqual(hint, "执行异常：disk full")

    def test_classify_job_event_finish_exit_code(self):
        log = '[job-event] {"job_id":"x","event":"finish","exit_code":2}\n'
        hint = classify_job_failure(log, status="FAILED", exit_code=2)
        self.assertEqual(hint, "命令退出码 2")

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
