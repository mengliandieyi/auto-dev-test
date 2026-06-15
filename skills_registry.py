"""Skill 注册表（skills/*.md，供 dev 与 API 共用）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT / "skills"
SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
VALID_LAYERS = frozenset({"frontend", "backend", "fullstack"})


def validate_skill_id(skill_id: str) -> str:
    if not SKILL_ID_RE.match(skill_id):
        raise ValueError(f"Invalid skill id: {skill_id}")
    return skill_id


def _parse_front_matter(text: str) -> Dict[str, Any]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _skill_path(skill_id: str) -> Path:
    validate_skill_id(skill_id)
    path = (SKILLS_DIR / f"{skill_id}.md").resolve()
    if SKILLS_DIR.resolve() not in path.parents:
        raise ValueError("Invalid skill path")
    return path


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def list_skills() -> List[Dict[str, Any]]:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    items: List[Dict[str, Any]] = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        if path.is_symlink():
            continue
        skill_id = path.stem
        if not SKILL_ID_RE.match(skill_id):
            continue
        text = path.read_text(encoding="utf-8")
        meta = _parse_front_matter(text)
        layer = str(meta.get("layer") or "fullstack")
        if layer not in VALID_LAYERS:
            layer = "fullstack"
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        items.append({
            "id": skill_id,
            "name": str(meta.get("name") or skill_id),
            "layer": layer,
            "description": str(meta.get("description") or ""),
            "path": _display_path(path),
            "updated_at": mtime,
        })
    return items


def read_skill(skill_id: str) -> Dict[str, Any]:
    path = _skill_path(skill_id)
    if not path.is_file():
        raise FileNotFoundError(skill_id)
    content = path.read_text(encoding="utf-8")
    meta = _parse_front_matter(content)
    layer = str(meta.get("layer") or "fullstack")
    if layer not in VALID_LAYERS:
        layer = "fullstack"
    return {
        "id": skill_id,
        "name": str(meta.get("name") or skill_id),
        "layer": layer,
        "description": str(meta.get("description") or ""),
        "content": content,
        "path": _display_path(path),
    }


def write_skill(skill_id: str, content: str) -> Dict[str, Any]:
    validate_skill_id(skill_id)
    if len(content.encode("utf-8")) > 1_048_576:
        raise ValueError("Skill content exceeds 1MB")
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = _skill_path(skill_id)
    path.write_text(content, encoding="utf-8")
    return read_skill(skill_id)


def delete_skill(skill_id: str) -> None:
    path = _skill_path(skill_id)
    if not path.is_file():
        raise FileNotFoundError(skill_id)
    path.unlink()


def derive_skill_id(filename: str) -> str:
    raw = Path(filename.replace("\\", "/").split("/")[-1]).stem.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    if not normalized:
        raise ValueError(f"Cannot derive skill id from filename: {filename}")
    if not normalized[0].isalpha():
        normalized = f"skill-{normalized}"
    validate_skill_id(normalized)
    return normalized


def import_skill_content(
    content: str,
    skill_id: str,
    *,
    overwrite: bool = False,
) -> Dict[str, Any]:
    validate_skill_id(skill_id)
    path = _skill_path(skill_id)
    if path.exists() and not overwrite:
        raise FileExistsError(skill_id)
    if not content.strip():
        raise ValueError("Skill content is empty")
    return write_skill(skill_id, content)


def read_skill_file_from_repo(rel_path: str) -> str:
    path = (ROOT / rel_path).resolve()
    if ROOT.resolve() not in path.parents:
        raise ValueError("Path outside repository")
    if path.suffix.lower() != ".md":
        raise ValueError("Only .md files allowed")
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    return path.read_text(encoding="utf-8")


def resolve_skill_path(skill_id: Optional[str]) -> Optional[Path]:
    if not skill_id or not str(skill_id).strip():
        return None
    path = _skill_path(str(skill_id).strip())
    return path if path.is_file() else None
