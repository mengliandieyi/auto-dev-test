"""Skill 库 API 服务。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException

from api.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT))
from skills_registry import (  # noqa: E402
    delete_skill,
    derive_skill_id,
    import_skill_content,
    list_skills,
    read_skill,
    read_skill_file_from_repo,
    validate_skill_id,
    write_skill,
)


def list_skill_summaries() -> list:
    return list_skills()


def get_skill(skill_id: str) -> Dict[str, Any]:
    validate_skill_id(skill_id)
    try:
        return read_skill(skill_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def create_skill(skill_id: str, content: str) -> Dict[str, Any]:
    try:
        validate_skill_id(skill_id)
        from skills_registry import _skill_path
        if _skill_path(skill_id).exists():
            raise HTTPException(status_code=409, detail=f"Skill already exists: {skill_id}")
        return write_skill(skill_id, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def update_skill(skill_id: str, content: str) -> Dict[str, Any]:
    try:
        return write_skill(skill_id, content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def remove_skill(skill_id: str) -> Dict[str, str]:
    try:
        delete_skill(skill_id)
        return {"deleted": skill_id}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def import_skill_bytes(
    filename: str,
    data: bytes,
    skill_id: str | None = None,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]:
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if len(data) > 1_048_576:
        raise HTTPException(status_code=400, detail="File exceeds 1MB")
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text") from exc

    try:
        sid = validate_skill_id(skill_id.strip()) if skill_id and skill_id.strip() else derive_skill_id(filename)
        return import_skill_content(content, sid, overwrite=overwrite)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=f"Skill already exists: {exc.args[0]}") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def import_skill_path(
    rel_path: str,
    skill_id: str | None = None,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]:
    rel_path = rel_path.strip().replace("\\", "/")
    if not rel_path or ".." in rel_path.split("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    try:
        content = read_skill_file_from_repo(rel_path)
        sid = validate_skill_id(skill_id.strip()) if skill_id and skill_id.strip() else derive_skill_id(Path(rel_path).name)
        return import_skill_content(content, sid, overwrite=overwrite)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=f"Skill already exists: {exc.args[0]}") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"File not found: {rel_path}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
