from fastapi import APIRouter

from api.services import projects as project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects():
    return project_service.list_projects()


@router.get("/{project_id}")
def get_project(project_id: str):
    return project_service.get_project(project_id)
