from typing import Optional

from fastapi import APIRouter, Query

from api.models.schemas import AiSettingsForm, CredentialsForm, TextContentRequest
from api.services import credentials, global_settings
from api.services.path_safety import validate_project_id

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/global/yaml")
def get_global_yaml():
    """返回 config/global.yaml 原文（含 ai.model 等）。"""
    return global_settings.read_global_yaml_text()


@router.get("/credentials")
def get_credentials():
    """连接状态（不回传完整 API Key）。"""
    return credentials.get_credentials()


@router.put("/credentials")
def update_credentials(body: CredentialsForm):
    """保存 API Key / Base URL 到本地 .env（不进入 git）。"""
    return credentials.update_credentials(
        api_key=body.api_key,
        base_url=body.base_url,
        openai_api_key=body.openai_api_key,
        openai_base_url=body.openai_base_url,
        use_llm_parse=body.use_llm_parse,
        clear_api_key=body.clear_api_key,
        clear_openai_api_key=body.clear_openai_api_key,
    )


@router.get("/ai")
def get_ai_settings():
    """表单化 AI 配置（无需手写 YAML）。"""
    return global_settings.read_ai_settings_form()


@router.put("/ai")
def update_ai_settings(body: AiSettingsForm):
    return global_settings.write_ai_settings_form(body.model_dump())


@router.get("/ai-resolved")
def get_ai_resolved(project_id: Optional[str] = Query(default=None)):
    """返回多模型 profile 与各任务实际使用的模型（含项目覆盖）。"""
    return global_settings.resolve_ai_settings(project_id)


@router.put("/global")
def update_global_yaml(body: TextContentRequest):
    """保存 config/global.yaml。"""
    return global_settings.write_global_yaml_text(body.content)
