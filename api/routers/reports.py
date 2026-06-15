from fastapi import APIRouter

from api.services import projects as project_service
from api.services.path_safety import validate_project_id
from report_history import list_traceability_history, read_traceability_snapshot

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{project_id}")
def list_reports(project_id: str):
    validate_project_id(project_id)
    return project_service.list_reports(project_id)


@router.get("/{project_id}/{prd_id}/traceability/history")
def get_traceability_history(project_id: str, prd_id: str):
    validate_project_id(project_id)
    return {"project_id": project_id, "prd_id": prd_id, "history": list_traceability_history(project_id, prd_id)}


@router.get("/{project_id}/{prd_id}/traceability/history/{snapshot_id}")
def get_traceability_history_item(project_id: str, prd_id: str, snapshot_id: str):
    validate_project_id(project_id)
    data = read_traceability_snapshot(project_id, prd_id, snapshot_id)
    return {"project_id": project_id, "prd_id": prd_id, **data}


@router.get("/{project_id}/{prd_id}/traceability")
def get_traceability(project_id: str, prd_id: str):
    data = project_service.read_traceability(project_id, prd_id)
    return {"project_id": project_id, "prd_id": prd_id, **data, "snapshot_id": "latest"}
