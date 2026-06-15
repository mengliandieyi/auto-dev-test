"""API 请求/响应模型"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PipelineRequest(BaseModel):
    project_id: str
    prd_path: Optional[str] = None
    prd_id: Optional[str] = None
    type: str = "all"
    layer: str = "all"


class JobResponse(BaseModel):
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
    log: str = ""


class ProjectSummary(BaseModel):
    id: str
    base_url: str = ""
    prd_dir: str = ""


class PrdSummary(BaseModel):
    filename: str
    path: str
    size: int = 0


class ReportSummary(BaseModel):
    prd_id: str
    filename: str
    path: str
