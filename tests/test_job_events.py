"""job-event 解析单测。"""

from __future__ import annotations

import os
import unittest
from io import StringIO
from unittest.mock import patch

from job_events import emit_job_event, parse_job_events


class TestJobEvents(unittest.TestCase):
    def test_emit_only_when_job_id_set(self):
        buf = StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.stdout", buf):
                emit_job_event("start", command="test")
        self.assertEqual(buf.getvalue(), "")

        buf = StringIO()
        with patch.dict(os.environ, {"AUTO_DEV_JOB_ID": "abc123"}, clear=False):
            with patch("sys.stdout", buf):
                emit_job_event("start", command="test", project="project-a")
        line = buf.getvalue().strip()
        self.assertTrue(line.startswith("[job-event] "))
        events = parse_job_events(line)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "start")
        self.assertEqual(events[0]["job_id"], "abc123")

    def test_parse_multiple_events(self):
        log = '\n'.join(
            [
                "plain log",
                '[job-event] {"job_id":"x","event":"start","command":"parse"}',
                '[job-event] {"job_id":"x","event":"finish","exit_code":0}',
            ]
        )
        events = parse_job_events(log)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
