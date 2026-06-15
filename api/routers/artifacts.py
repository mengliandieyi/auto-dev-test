from fastapi import APIRouter, Query

from api.services import artifacts as artifact_service
from api.services.path_safety import validate_project_id

router = APIRouter(prefix="/api/projects", tags=["artifacts"])


@router.get("/{project_id}/artifacts/{prd_id}/test-cases")
def get_test_cases(project_id: str, prd_id: str):
    validate_project_id(project_id)
    return artifact_service.read_test_cases(project_id, prd_id)


@router.get("/{project_id}/artifacts/{prd_id}/generated")
def list_generated(project_id: str, prd_id: str):
    validate_project_id(project_id)
    files = artifact_service.list_generated_files(project_id, prd_id)
    return {"prd_id": prd_id, "files": files}


@router.get("/{project_id}/artifacts/generated-file")
def get_generated_file(project_id: str, path: str = Query(..., alias="path")):
    validate_project_id(project_id)
    return artifact_service.read_generated_file(project_id, path)


@router.get("/{project_id}/artifacts/{prd_id}/changes")
def list_changes(project_id: str, prd_id: str):
    validate_project_id(project_id)
    return artifact_service.list_changes(project_id, prd_id)
