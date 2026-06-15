"""job-event 持久化单测。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class TestJobEventPersistence(unittest.TestCase):
    def test_sync_job_events_from_log(self):
        import api.config as api_config
        import api.services.job_store as job_store

        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            logs = troot / "logs"
            logs.mkdir()
            db = troot / "jobs.db"
            old_root = api_config.REPO_ROOT
            old_db = api_config.JOBS_DB
            old_logs = api_config.LOGS_DIR
            api_config.REPO_ROOT = troot
            api_config.JOBS_DB = db
            api_config.LOGS_DIR = logs
            job_store.JOBS_DB = db
            job_store.LOGS_DIR = logs
            try:
                job_store.init_jobs_db(db)
                job = job_store.create_job("project-a", "test", {})
                log_path = Path(job["log_path"])
                log_path.write_text(
                    '[job-event] {"job_id":"%s","event":"start","command":"test"}\n'
                    '[job-event] {"job_id":"%s","event":"finish","exit_code":0}\n'
                    % (job["id"], job["id"]),
                    encoding="utf-8",
                )
                events = job_store.sync_job_events(job["id"])
                self.assertEqual(len(events), 2)
                self.assertEqual(events[0]["event"], "start")
                loaded = job_store.read_job_events(job["id"])
                self.assertEqual(len(loaded), 2)
            finally:
                api_config.REPO_ROOT = old_root
                api_config.JOBS_DB = old_db
                api_config.LOGS_DIR = old_logs
                job_store.JOBS_DB = old_db
                job_store.LOGS_DIR = old_logs

    def test_prune_jobs_scoped_by_project(self):
        import api.services.job_store as job_store

        for _ in range(3):
            job = job_store.create_job("project-a", "report", {})
            job_store.update_job_status(
                job["id"], "SUCCESS", finished_at=job_store._now(), exit_code=0
            )
        for _ in range(2):
            job = job_store.create_job("project-b", "report", {})
            job_store.update_job_status(
                job["id"], "SUCCESS", finished_at=job_store._now(), exit_code=0
            )
        removed = job_store.prune_jobs(keep=1, project_id="project-a")
        self.assertGreaterEqual(removed, 1)
        remaining_b = job_store.list_jobs(project_id="project-b", limit=10)
        self.assertGreaterEqual(len(remaining_b), 1)


if __name__ == "__main__":
    unittest.main()
