"""异步任务 Worker：限并发执行 run.py（TECH §5.4）。"""

from __future__ import annotations

import asyncio
import os
import signal
from typing import Any, Dict, List, Optional

from api.config import REPO_ROOT
from api.services import job_store
from api.config import MAX_CONCURRENT_JOBS

_semaphore: Optional[asyncio.Semaphore] = None
_worker_task: Optional[asyncio.Task] = None
_running_procs: Dict[str, asyncio.subprocess.Process] = {}
_shutting_down = False


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
    return _semaphore


def build_argv(command: str, project_id: str, args: Dict[str, Any]) -> List[str]:
    base = ["python3", str(REPO_ROOT / "run.py"), command, "--project", project_id]
    prd_cmds = ("validate", "parse", "generate-pipeline", "run-full", "dev")
    if command in prd_cmds:
        prd = args.get("prd_path") or args.get("prd")
        if not prd:
            raise ValueError("prd is required")
        base.extend(["--prd", prd])
    if command == "dev":
        base.extend(["--layer", args.get("layer", "all")])
        if args.get("skill_frontend"):
            base.extend(["--skill-frontend", args["skill_frontend"]])
        if args.get("skill_backend"):
            base.extend(["--skill-backend", args["skill_backend"]])
    if command == "generate":
        base.extend(["--prd-id", args["prd_id"]])
        base.extend(["--type", args.get("type", "all")])
    if command == "heal-loop":
        base.extend(["--prd-id", args["prd_id"]])
        if args.get("apply"):
            base.append("--apply")
    if command in ("report", "test"):
        base.extend(["--layer", args.get("layer", "all")])
        if args.get("prd_id"):
            base.extend(["--prd-id", args["prd_id"]])
    if args.get("force"):
        base.append("--force")
    return base


async def enqueue_job(
    command: str, project_id: str, args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    job_store.init_jobs_db()
    job = job_store.create_job(project_id, command, args or {})
    _ensure_worker()
    return job


def _ensure_worker() -> None:
    global _worker_task
    if _shutting_down:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if _worker_task is None or _worker_task.done():
        _worker_task = loop.create_task(_worker_loop())


async def _worker_loop() -> None:
    while not _shutting_down:
        job = job_store.pick_next_pending()
        if not job:
            await asyncio.sleep(0.5)
            continue
        asyncio.create_task(_run_job(job))


async def cancel_job(job_id: str) -> Dict[str, Any]:
    job = job_store.get_job(job_id)
    if not job:
        raise ValueError("Job not found")
    if job["status"] not in ("PENDING", "RUNNING"):
        raise ValueError(f"Job already {job['status']}")

    if job["status"] == "RUNNING":
        proc = _running_procs.get(job_id)
        if proc:
            await _terminate_proc(proc)
            _running_procs.pop(job_id, None)

    if not job_store.try_mark_cancelled(job_id):
        current = job_store.get_job(job_id)
        if current and current["status"] == "CANCELLED":
            return current
        raise ValueError("Job could not be cancelled")

    job_store.append_job_log(job_id, "[cancelled] 用户取消任务")
    updated = job_store.get_job(job_id)
    assert updated is not None
    return updated


async def _run_job(job: Dict[str, Any]) -> None:
    sem = _get_semaphore()
    async with sem:
        job_id = job["id"]
        current = job_store.get_job(job_id)
        if not current or current["status"] == "CANCELLED":
            return
        log_path = job.get("log_path")
        proc: Optional[asyncio.subprocess.Process] = None
        try:
            argv = build_argv(job["command"], job["project_id"], job.get("args") or {})
            if not log_path:
                raise ValueError("log_path missing")
            with open(log_path, "wb") as log_file:
                env = os.environ.copy()
                env["AUTO_DEV_JOB_ID"] = job_id
                env["AUTO_DEV_JOB_COMMAND"] = job["command"]
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    stdout=log_file,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=str(REPO_ROOT),
                    start_new_session=True,
                    env=env,
                )
                _running_procs[job_id] = proc
                exit_code = await proc.wait()
            final = job_store.get_job(job_id)
            if final and final["status"] == "CANCELLED":
                job_store.sync_job_events(job_id)
                return
            status = "SUCCESS" if exit_code == 0 else "FAILED"
            job_store.update_job_status(
                job_id, status, finished_at=job_store._now(), exit_code=exit_code
            )
            job_store.sync_job_events(job_id)
        except asyncio.CancelledError:
            if proc and proc.returncode is None:
                await _terminate_proc(proc)
            job_store.update_job_status(
                job_id, "FAILED", finished_at=job_store._now(), exit_code=-1
            )
            if log_path:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("\n[worker] 任务因服务关闭被终止\n")
            raise
        except Exception as exc:
            if proc and proc.returncode is None:
                await _terminate_proc(proc)
            if log_path:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n[worker error] {exc}\n")
            job_store.update_job_status(
                job_id, "FAILED", finished_at=job_store._now(), exit_code=1
            )
        finally:
            _running_procs.pop(job_id, None)


async def _terminate_proc(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            return
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
    except ProcessLookupError:
        pass


async def shutdown_workers() -> None:
    global _shutting_down, _worker_task
    _shutting_down = True
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    for job_id, proc in list(_running_procs.items()):
        await _terminate_proc(proc)
        job_store.update_job_status(
            job_id, "FAILED", finished_at=job_store._now(), exit_code=-1
        )
        _running_procs.pop(job_id, None)
    job_store.recover_stale_running_jobs()


def start_worker_on_startup() -> None:
    global _shutting_down
    _shutting_down = False
    job_store.recover_stale_running_jobs()
    _ensure_worker()
