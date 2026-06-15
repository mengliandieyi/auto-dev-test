from fastapi import APIRouter

from api.services import projects as project_service
from api.services.path_safety import validate_project_id

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{project_id}")
def list_reports(project_id: str):
    validate_project_id(project_id)
    return project_service.list_reports(project_id)


@router.get("/{project_id}/{prd_id}/traceability")
def get_traceability(project_id: str, prd_id: str):
    content = project_service.read_traceability(project_id, prd_id)
    return {"project_id": project_id, "prd_id": prd_id, "content": content}
