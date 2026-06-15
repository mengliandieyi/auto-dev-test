"""API 请求/响应模型"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PipelineRequest(BaseModel):
    project_id: str
    prd: Optional[str] = Field(None, description="PRD 相对路径")
    prd_path: Optional[str] = None
    prd_id: Optional[str] = None
    type: str = "all"
    layer: str = "all"
    skill_frontend: Optional[str] = None
    skill_backend: Optional[str] = None
    force: bool = False

    def resolved_prd(self) -> Optional[str]:
        return self.prd or self.prd_path


class JobResponse(BaseModel):
    job_id: str
    id: str
    project_id: str
    command: str
    args: Dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None


class JobDetailResponse(JobResponse):
    log_tail: str = ""


class TextContentRequest(BaseModel):
    content: str


class AiProfileForm(BaseModel):
    id: str = Field(..., min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9-]*$")
    model: str = Field(..., min_length=1)
    max_tokens: int = Field(default=8096, ge=256, le=200000)
    provider: str = Field(default="anthropic", pattern=r"^(anthropic|openai)$")
    base_url: str = Field(default="", max_length=512)
    api_key: Optional[str] = Field(default=None, description="API Key，留空表示不修改")
    clear_api_key: bool = False
    api_key_set: bool = False
    api_key_preview: str = ""


class AiSettingsForm(BaseModel):
    provider: str = "anthropic"
    default_profile: str = Field(..., min_length=1)
    profiles: list[AiProfileForm] = Field(..., min_length=1)
    tasks: Dict[str, str] = Field(default_factory=dict)


class CredentialsForm(BaseModel):
    api_key: Optional[str] = Field(default=None, description="Anthropic API Key，留空表示不修改")
    base_url: Optional[str] = Field(default=None, description="Anthropic Base URL")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key，留空表示不修改")
    openai_base_url: Optional[str] = Field(default=None, description="OpenAI Base URL")
    use_llm_parse: bool = False
    clear_api_key: bool = False
    clear_openai_api_key: bool = False


class SkillWriteRequest(BaseModel):
    content: str = Field(..., min_length=1)


class SkillImportPathRequest(BaseModel):
    path: str = Field(..., min_length=1, description="仓库内相对路径，如 design/SKILL.md")
    skill_id: Optional[str] = Field(None, description="指定 ID，留空则从文件名推导")
    overwrite: bool = False


class ProjectSettingsForm(BaseModel):
    project_id: str
    project_name: str = ""
    base_url: str = Field(..., min_length=1, description="被测应用根地址")
    health_check_url: str = "/health"
    repos_frontend: str = ""
    repos_backend: str = ""
    dev_skill_frontend: str = ""
    dev_skill_backend: str = ""
    vitest_enabled: bool = False
    vitest_frontend_root: str = ""
    web_server_command: str = ""
    web_server_url: str = ""
    auth_login_url: str = "/login"
    ai_use_global: bool = True
    ai_task_parse: str = "haiku"
    ai_task_heal: str = "sonnet"
    ai_task_dev_frontend: str = "sonnet"
    ai_task_dev_backend: str = "sonnet"


class CreateProjectRequest(BaseModel):
    project_id: str = Field(..., min_length=2, max_length=32, pattern=r"^[a-z0-9][a-z0-9-]*$")
    project_name: str = Field(default="", max_length=64)
    base_url: str = Field(..., min_length=4, description="被测应用根地址")
