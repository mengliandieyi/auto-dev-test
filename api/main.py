"""FastAPI 入口 — M3 Web 管理后台"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bootstrap import setup_repo_paths

setup_repo_paths()

from api.config import REPO_ROOT
from api.routers import artifacts, heal, pipeline, prds, projects, reports, settings, skills
from api.services import job_runner, job_store

from env_store import ensure_env_loaded  # noqa: E402
from playwright_runtime import sync_playwright_runtime  # noqa: E402
from version import VERSION  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_env_loaded()
    job_store.init_jobs_db()
    job_store.recover_stale_running_jobs()
    from heal.store import init_heal_db, recover_stale_heal_runs

    init_heal_db()
    recover_stale_heal_runs()
    from api.services.projects import ensure_all_project_dirs

    ensure_all_project_dirs()
    sync_playwright_runtime()
    job_runner.start_worker_on_startup()
    yield
    await job_runner.shutdown_workers()


app = FastAPI(
    title="auto-dev-test API",
    description="PRD 驱动测试平台 — Web 管理后台",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router)
app.include_router(heal.router)
app.include_router(projects.router)
app.include_router(prds.router)
app.include_router(pipeline.router)
app.include_router(reports.router)
app.include_router(artifacts.router)
app.include_router(skills.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
