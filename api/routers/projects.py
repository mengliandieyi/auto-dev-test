from fastapi import APIRouter

from api.models.schemas import TextContentRequest
from api.services import projects as project_service
from api.services.path_safety import validate_project_id

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects():
    return project_service.list_projects()


@router.get("/{project_id}")
def get_project(project_id: str):
    return project_service.get_project(project_id)


@router.get("/{project_id}/yaml")
def get_project_yaml(project_id: str):
    """M5：返回原始 YAML 文本供在线编辑。"""
    validate_project_id(project_id)
    return project_service.read_project_yaml_text(project_id)


@router.put("/{project_id}")
def update_project(project_id: str, body: TextContentRequest):
    validate_project_id(project_id)
    return project_service.write_project_yaml_text(project_id, body.content)
