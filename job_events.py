"""流水线任务结构化事件（写入子进程 stdout，供 job log 解析）。"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_PREFIX = "[job-event] "


def emit_job_event(event: str, **fields: Any) -> None:
    job_id = os.environ.get("AUTO_DEV_JOB_ID", "").strip()
    if not job_id:
        return
    payload: dict[str, Any] = {"job_id": job_id, "event": event, **fields}
    print(f"{_PREFIX}{json.dumps(payload, ensure_ascii=False)}", flush=True)


def parse_job_events(log_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in (log_text or "").splitlines():
        if not line.startswith(_PREFIX):
            continue
        try:
            events.append(json.loads(line[len(_PREFIX) :]))
        except json.JSONDecodeError:
            continue
    return events
