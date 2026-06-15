from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.models.schemas import JobDetailResponse, JobResponse, PipelineRequest
from api.services import job_store
from api.services import job_runner
from api.services.path_safety import validate_project_id

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _to_job_response(job: dict) -> JobResponse:
    return JobResponse(
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
    args = {}
    if body.prd_path:
        args["prd_path"] = body.prd_path
    if body.prd_id:
        args["prd_id"] = body.prd_id
    if body.type:
        args["type"] = body.type
    if body.layer:
        args["layer"] = body.layer
    if command in ("validate", "parse", "generate-pipeline") and not body.prd_path:
        raise HTTPException(400, "prd_path is required")
    if command == "generate" and not body.prd_id:
        raise HTTPException(400, "prd_id is required")
    job = await job_runner.enqueue_job(command, body.project_id, args)
    return _to_job_response(job)


@router.post("/validate", response_model=JobResponse)
async def pipeline_validate(body: PipelineRequest):
    return await _enqueue("validate", body)


@router.post("/parse", response_model=JobResponse)
async def pipeline_parse(body: PipelineRequest):
    return await _enqueue("parse", body)


@router.post("/generate", response_model=JobResponse)
async def pipeline_generate(body: PipelineRequest):
    return await _enqueue("generate", body)


@router.post("/generate-pipeline", response_model=JobResponse)
async def pipeline_generate_pipeline(body: PipelineRequest):
    return await _enqueue("generate-pipeline", body)


@router.post("/test", response_model=JobResponse)
async def pipeline_test(body: PipelineRequest):
    return await _enqueue("test", body)


@router.post("/report", response_model=JobResponse)
async def pipeline_report(body: PipelineRequest):
    return await _enqueue("report", body)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    log = job_store.read_job_log(job_id)
    return JobDetailResponse(**_to_job_response(job).model_dump(), log=log)


@router.get("/jobs")
def list_jobs(project_id: Optional[str] = Query(None), limit: int = Query(20)):
    return job_store.list_jobs(project_id=project_id, limit=limit)
