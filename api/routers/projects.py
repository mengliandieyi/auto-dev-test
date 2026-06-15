from fastapi import APIRouter, Query

from api.models.schemas import CreateProjectRequest, TextContentRequest, ProjectSettingsForm
from api.services import projects as project_service
from api.services import project_settings as project_settings_service
from api.services import repo_changes as repo_changes_service
from api.services.path_safety import validate_project_id

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects():
    return project_service.list_projects()


@router.post("", status_code=201)
def create_project(body: CreateProjectRequest):
    return project_service.create_project(body.project_id, body.project_name, body.base_url)


@router.get("/{project_id}")
def get_project(project_id: str):
    return project_service.get_project(project_id)


@router.get("/{project_id}/yaml")
def get_project_yaml(project_id: str):
    """M5：返回原始 YAML 文本供在线编辑。"""
    validate_project_id(project_id)
    return project_service.read_project_yaml_text(project_id)


@router.get("/{project_id}/settings")
def get_project_settings(project_id: str):
    validate_project_id(project_id)
    return project_settings_service.read_project_settings_form(project_id)


@router.put("/{project_id}/settings")
def update_project_settings(project_id: str, body: ProjectSettingsForm):
    validate_project_id(project_id)
    return project_settings_service.write_project_settings_form(project_id, body.model_dump())


@router.put("/{project_id}")
def update_project(project_id: str, body: TextContentRequest):
    validate_project_id(project_id)
    return project_service.write_project_yaml_text(project_id, body.content)


@router.get("/{project_id}/repos/changes")
def get_repo_changes(project_id: str, layer: str = Query("all")):
    validate_project_id(project_id)
    return repo_changes_service.list_repo_changes(project_id, layer)
