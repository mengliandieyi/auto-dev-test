from fastapi import APIRouter, File, HTTPException, UploadFile

from api.models.schemas import TextContentRequest
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


@router.put("/{project_id}/prds/{filename}")
def update_prd(project_id: str, filename: str, body: TextContentRequest):
    validate_project_id(project_id)
    return project_service.write_prd_content(project_id, filename, body.content)


@router.post("/{project_id}/prds/upload")
async def upload_prd(project_id: str, file: UploadFile = File(...)):
    validate_project_id(project_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    filename = file.filename.replace("\\", "/").split("/")[-1]
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files allowed")
    data = await file.read()
    return project_service.upload_prd_file(project_id, filename, data)
