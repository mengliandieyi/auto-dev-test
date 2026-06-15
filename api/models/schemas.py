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
