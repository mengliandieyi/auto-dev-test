"""API 运行时配置"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JOBS_DB = REPO_ROOT / "tests" / "generated" / "jobs.db"
LOGS_DIR = REPO_ROOT / "logs" / "jobs"
MAX_CONCURRENT_JOBS = int(os.getenv("API_MAX_WORKERS", "2"))
LOG_TAIL_MAX_BYTES = 8192
