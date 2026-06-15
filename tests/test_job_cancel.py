"""任务取消 API 单测。"""

import unittest


from api.services import job_store


class TestJobCancel(unittest.TestCase):
    def test_cancel_pending_job(self):
        job = job_store.create_job("project-a", "validate", {"prd": "prds/project-a/x.md"})
        self.assertTrue(job_store.try_mark_cancelled(job["id"]))
        updated = job_store.get_job(job["id"])
        assert updated is not None
        self.assertEqual(updated["status"], "CANCELLED")
        self.assertEqual(updated["exit_code"], -1)

    def test_cancel_finished_job_fails(self):
        job = job_store.create_job("project-a", "validate", {})
        job_store.update_job_status(job["id"], "SUCCESS", finished_at=job_store._now(), exit_code=0)
        self.assertFalse(job_store.try_mark_cancelled(job["id"]))

    def test_runner_cancel_pending(self):
        import asyncio
        from api.services import job_runner

        job = job_store.create_job("project-a", "report", {"layer": "all"})
        result = asyncio.run(job_runner.cancel_job(job["id"]))
        self.assertEqual(result["status"], "CANCELLED")

    def test_runner_cancel_unknown_raises(self):
        import asyncio
        from api.services import job_runner

        with self.assertRaises(ValueError):
            asyncio.run(job_runner.cancel_job("nonexistent-job-id"))


if __name__ == "__main__":
    unittest.main()
