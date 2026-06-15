"""API 运行时配置"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JOBS_DB = REPO_ROOT / "tests" / "generated" / "jobs.db"
LOGS_DIR = REPO_ROOT / "logs" / "jobs"
MAX_CONCURRENT_JOBS = 2
