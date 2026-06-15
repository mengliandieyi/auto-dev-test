"""Heal API（TECH §8.7）。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services import job_runner
from api.services.path_safety import validate_project_id
from heal.analyze import analyze_failure
from heal.fix import apply_patch_dir, discard_patch_dir, plan_fix
from heal.flaky import collect_test_logs, extract_failures_from_reports
from heal.store import create_heal_run, get_heal_run, list_heal_runs, read_patch_preview, update_heal_run

router = APIRouter(prefix="/api/heal", tags=["heal"])


class HealLoopRequest(BaseModel):
    project_id: str
    prd_id: str


class HealAnalyzeRequest(BaseModel):
    project_id: str
    prd_id: str
    job_id: Optional[str] = None


class HealApplyRequest(BaseModel):
    commit: bool = False


@router.post("/loop", status_code=202)
async def heal_loop(body: HealLoopRequest):
    validate_project_id(body.project_id)
    job = await job_runner.enqueue_job(
        "heal-loop",
        body.project_id,
        {"prd_id": body.prd_id},
    )
    return {"job_id": job["id"], "heal_enqueue": True}


@router.post("/analyze")
def heal_analyze(body: HealAnalyzeRequest):
    from api.config import REPO_ROOT
    from config_loader import load_project_config

    validate_project_id(body.project_id)
    config = load_project_config(body.project_id)
    report_dir = REPO_ROOT / "reports" / body.project_id
    failures = extract_failures_from_reports(report_dir)
    logs = collect_test_logs(report_dir)
    report_path = report_dir / f"{body.prd_id}_traceability.txt"
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else logs
    diagnosis, cost = analyze_failure(body.project_id, body.prd_id, config, failures, report_text)
    run = create_heal_run(body.project_id, body.prd_id, parent_job_id=body.job_id)
    update_heal_run(
        run["id"],
        status="ANALYZED",
        diagnosis_json=diagnosis,
        token_cost=cost,
        parent_job_id=body.job_id,
        finished_at=_now(),
    )
    return {"heal_run_id": run["id"], "diagnosis": diagnosis, "token_cost": cost}


@router.get("/runs/{run_id}")
def heal_get_run(run_id: str):
    run = get_heal_run(run_id)
    if not run:
        raise HTTPException(404, "heal run not found")
    run["patch_preview"] = read_patch_preview(run_id)
    return run


@router.get("/runs")
def heal_list_runs(project_id: str, prd_id: Optional[str] = None):
    validate_project_id(project_id)
    from heal.store import recover_stale_heal_runs

    recover_stale_heal_runs()
    return list_heal_runs(project_id, prd_id)


@router.post("/runs/{run_id}/apply")
def heal_apply(run_id: str, body: HealApplyRequest):
    run = get_heal_run(run_id)
    if not run:
        raise HTTPException(404, "heal run not found")
    patch_dir = run.get("patch_dir")
    if not patch_dir:
        raise HTTPException(400, "no patch_dir")
    from pathlib import Path

    ok = apply_patch_dir(Path(patch_dir), run["project_id"], run["prd_id"])
    if ok:
        update_heal_run(run_id, status="SUCCESS", finished_at=_now())
    return {"applied": ok, "commit": body.commit}


@router.post("/runs/{run_id}/discard")
def heal_discard(run_id: str):
    run = get_heal_run(run_id)
    if not run:
        raise HTTPException(404, "heal run not found")
    from pathlib import Path

    if run.get("patch_dir"):
        discard_patch_dir(Path(run["patch_dir"]))
    update_heal_run(run_id, status="ABORTED", abort_reason="DISCARDED", finished_at=_now())
    return {"discarded": True}


def _now() -> str:
    from heal.store import _now as n

    return n()
