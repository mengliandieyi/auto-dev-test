from fastapi import APIRouter

from api.services import projects as project_service
from api.services.path_safety import validate_project_id

router = APIRouter(prefix="/api/projects", tags=["prds"])


@router.get("/{project_id}/prds")
def list_prds(project_id: str):
    validate_project_id(project_id)
    return project_service.list_prds(project_id)


@router.get("/{project_id}/prds/{filename}")
def get_prd(project_id: str, filename: str):
    return project_service.read_prd(project_id, filename)
