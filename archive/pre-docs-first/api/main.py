"""FastAPI 入口 — v1 主入口，CLI 为引擎"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import pipeline, prds, projects, reports
from api.services import job_runner, job_store

app = FastAPI(
    title="auto-dev-test API",
    description="PRD 驱动测试平台 — Web 管理后台后端",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(prds.router)
app.include_router(pipeline.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup():
    job_store.init_jobs_db()
    job_runner.start_worker_on_startup()


@app.on_event("shutdown")
async def on_shutdown():
    await job_runner.shutdown_workers()


@app.get("/api/health")
def health():
    return {"status": "ok"}
