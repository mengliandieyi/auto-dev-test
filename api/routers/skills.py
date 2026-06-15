from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api.models.schemas import SkillImportPathRequest, SkillWriteRequest
from api.services import skills as skill_service

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def list_skills():
    return skill_service.list_skill_summaries()


@router.post("/import", status_code=201)
async def import_skill_file(
    file: UploadFile = File(...),
    skill_id: Optional[str] = Query(None, description="指定 ID，留空则从文件名推导"),
    overwrite: bool = Query(False),
):
    data = await file.read()
    return skill_service.import_skill_bytes(file.filename or "", data, skill_id, overwrite=overwrite)


@router.post("/import-path", status_code=201)
def import_skill_from_path(body: SkillImportPathRequest):
    return skill_service.import_skill_path(body.path, body.skill_id, overwrite=body.overwrite)


@router.get("/{skill_id}")
def get_skill(skill_id: str):
    return skill_service.get_skill(skill_id)


@router.post("/{skill_id}", status_code=201)
def create_skill(skill_id: str, body: SkillWriteRequest):
    return skill_service.create_skill(skill_id, body.content)


@router.put("/{skill_id}")
def update_skill(skill_id: str, body: SkillWriteRequest):
    return skill_service.update_skill(skill_id, body.content)


@router.delete("/{skill_id}")
def delete_skill(skill_id: str):
    return skill_service.remove_skill(skill_id)
