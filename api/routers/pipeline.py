from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models.schemas import JobDetailResponse, JobResponse, PipelineRequest
from api.services import job_runner, job_store
from api.services.path_safety import resolve_prd_path, validate_project_id

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _to_job_response(job: dict) -> JobResponse:
    return JobResponse(
        job_id=job["id"],
        id=job["id"],
        project_id=job["project_id"],
        command=job["command"],
        args=job.get("args") or {},
        status=job["status"],
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        finished_at=job.get("finished_at"),
        exit_code=job.get("exit_code"),
    )


async def _enqueue(command: str, body: PipelineRequest) -> JobResponse:
    validate_project_id(body.project_id)
    args: dict = {}
    prd = body.resolved_prd()
    if prd:
        safe_prd = resolve_prd_path(body.project_id, prd)
        from api.config import REPO_ROOT

        prd = str(safe_prd.relative_to(REPO_ROOT.resolve()))
        args["prd"] = prd
    if body.prd_id:
        args["prd_id"] = body.prd_id
    if body.type:
        args["type"] = body.type
    if body.layer:
        args["layer"] = body.layer
    if body.skill_frontend:
        args["skill_frontend"] = body.skill_frontend
    if body.skill_backend:
        args["skill_backend"] = body.skill_backend
    if body.force:
        args["force"] = True
    if command in ("validate", "parse", "generate-pipeline", "run-full", "dev") and not prd:
        raise HTTPException(400, "prd is required")
    if command == "generate" and not body.prd_id:
        raise HTTPException(400, "prd_id is required")
    job = await job_runner.enqueue_job(command, body.project_id, args)
    return _to_job_response(job)


@router.post("/validate", response_model=JobResponse, status_code=202)
async def pipeline_validate(body: PipelineRequest):
    return await _enqueue("validate", body)


@router.post("/parse", response_model=JobResponse, status_code=202)
async def pipeline_parse(body: PipelineRequest):
    return await _enqueue("parse", body)


@router.post("/generate", response_model=JobResponse, status_code=202)
async def pipeline_generate(body: PipelineRequest):
    return await _enqueue("generate", body)


@router.post("/generate-pipeline", response_model=JobResponse, status_code=202)
async def pipeline_generate_pipeline(body: PipelineRequest):
    return await _enqueue("generate-pipeline", body)


@router.post("/run-full", response_model=JobResponse, status_code=202)
async def pipeline_run_full(body: PipelineRequest):
    return await _enqueue("run-full", body)


@router.post("/test", response_model=JobResponse, status_code=202)
async def pipeline_test(body: PipelineRequest):
    return await _enqueue("test", body)


@router.post("/report", response_model=JobResponse, status_code=202)
async def pipeline_report(body: PipelineRequest):
    return await _enqueue("report", body)


@router.post("/dev", response_model=JobResponse, status_code=202)
async def pipeline_dev(body: PipelineRequest):
    if body.layer not in ("frontend", "backend", "all"):
        raise HTTPException(400, "layer must be frontend, backend, or all")
    return await _enqueue("dev", body)


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: str):
    try:
        job = await job_runner.cancel_job(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _to_job_response(job)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str):
    from api.services.job_insights import classify_job_failure

    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    log_tail = job_store.read_job_log_tail(job_id)
    hint = classify_job_failure(
        log_tail,
        status=job.get("status", ""),
        exit_code=job.get("exit_code"),
    )
    return JobDetailResponse(
        **_to_job_response(job).model_dump(),
        log_tail=log_tail,
        failure_hint=hint or "",
        events=job_store.read_job_events(job_id),
    )


@router.post("/jobs/prune")
def prune_jobs(
    keep: int = Query(100, ge=1, le=1000),
    project_id: Optional[str] = Query(None),
):
    if project_id:
        validate_project_id(project_id)
    removed = job_store.prune_jobs(keep=keep, project_id=project_id)
    return {"removed": removed, "keep": keep, "project_id": project_id}


@router.get("/jobs")
def list_jobs(project_id: Optional[str] = Query(None), limit: int = Query(20)):
    return [_to_job_response(j) for j in job_store.list_jobs(project_id=project_id, limit=limit)]
