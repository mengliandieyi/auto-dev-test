"""全局配置读写（config/global.yaml）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import yaml
from fastapi import HTTPException

from api.config import REPO_ROOT
from api.services.path_safety import (
    _check_write_size,
    _scan_content_conflicts,
    resolve_global_config_path,
    validate_project_id,
)

_SECRET_PATTERNS = ("sk-ant-", "ANTHROPIC_API_KEY=", "api_key:")


def _load_global_parsed() -> Dict[str, Any]:
    path = resolve_global_config_path()
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _save_global_parsed(parsed: Dict[str, Any]) -> Dict[str, str]:
    _validate_global_schema(parsed)
    text = yaml.safe_dump(parsed, allow_unicode=True, sort_keys=False)
    _check_write_size(text)
    path = resolve_global_config_path()
    path.write_text(text, encoding="utf-8")
    root = REPO_ROOT.resolve()
    return {"path": str(path.resolve().relative_to(root))}


def read_ai_settings_form() -> Dict[str, Any]:
    import env_store

    parsed = _load_global_parsed()
    ai = parsed.get("ai") if isinstance(parsed.get("ai"), dict) else {}
    provider = ai.get("provider", "anthropic")
    models = ai.get("models") if isinstance(ai.get("models"), dict) else {}
    if not models and ai.get("model"):
        models = {
            "default": {
                "model": ai["model"],
                "max_tokens": ai.get("max_tokens", 8096),
            },
        }
    profiles = []
    for pid, profile in models.items():
        if not isinstance(profile, dict):
            continue
        profile_id = str(pid)
        prof_provider = str(profile.get("provider", provider))
        key = env_store.read_profile_api_key(profile_id)
        profiles.append({
            "id": profile_id,
            "provider": prof_provider,
            "model": profile.get("model", ""),
            "max_tokens": int(profile.get("max_tokens", ai.get("max_tokens", 8096))),
            "base_url": str(profile.get("base_url") or ""),
            "api_key_set": bool(key),
            "api_key_preview": env_store._preview_key(key),
        })
    tasks = ai.get("tasks") if isinstance(ai.get("tasks"), dict) else {}
    default_profile = str(ai.get("default") or (profiles[0]["id"] if profiles else "sonnet"))
    return {
        "provider": provider,
        "default_profile": default_profile,
        "profiles": profiles,
        "tasks": {
            "parse": str(tasks.get("parse", default_profile)),
            "heal": str(tasks.get("heal", default_profile)),
            "dev_frontend": str(tasks.get("dev_frontend", default_profile)),
            "dev_backend": str(tasks.get("dev_backend", default_profile)),
        },
    }


def write_ai_settings_form(body: Dict[str, Any]) -> Dict[str, Any]:
    import env_store

    from api.models.schemas import AiSettingsForm

    form = AiSettingsForm.model_validate(body)
    profile_ids = {p.id for p in form.profiles}
    if form.default_profile not in profile_ids:
        raise HTTPException(status_code=400, detail="default_profile must exist in profiles")
    for task, ref in form.tasks.items():
        if ref not in profile_ids and not str(ref).startswith(("claude-", "gpt-")):
            raise HTTPException(status_code=400, detail=f"tasks.{task} must be a profile id or model id")

    previous = _load_global_parsed()
    prev_models = (
        previous.get("ai", {}).get("models", {})
        if isinstance(previous.get("ai"), dict) and isinstance(previous.get("ai", {}).get("models"), dict)
        else {}
    )
    removed_ids = [str(k) for k in prev_models if str(k) not in profile_ids]
    if removed_ids:
        env_store.clear_profile_api_keys(removed_ids)

    key_updates: Dict[str, Optional[str]] = {}
    providers: Dict[str, str] = {}
    for profile in form.profiles:
        providers[profile.id] = profile.provider
        if profile.clear_api_key:
            key_updates[profile.id] = ""
        elif profile.api_key is not None and profile.api_key.strip():
            key_updates[profile.id] = profile.api_key.strip()
    if key_updates:
        env_store.write_profile_api_keys(key_updates, providers=providers)

    parsed = _load_global_parsed()
    models: Dict[str, Any] = {}
    for profile in form.profiles:
        entry: Dict[str, Any] = {
            "model": profile.model,
            "max_tokens": profile.max_tokens,
            "provider": profile.provider,
        }
        url = (profile.base_url or "").strip()
        if url:
            entry["base_url"] = url.rstrip("/")
        models[profile.id] = entry

    parsed["ai"] = {
        "provider": form.provider,
        "default": form.default_profile,
        "models": models,
        "tasks": dict(form.tasks),
    }
    _save_global_parsed(parsed)
    return read_ai_settings_form()


def read_global_yaml_text() -> Dict[str, str]:
    path = resolve_global_config_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="global.yaml not found")
    return {"content": path.read_text(encoding="utf-8")}


def resolve_ai_settings(project_id: Optional[str] = None) -> Dict[str, Any]:
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from ai_resolver import ai_resolution_summary
    from config_loader import load_global_config, load_project_config

    if project_id:
        validate_project_id(project_id)
        config = load_project_config(project_id)
        scope = project_id
    else:
        config = load_global_config()
        scope = "global"
    summary = ai_resolution_summary(config)
    summary["scope"] = scope
    return summary


def write_global_yaml_text(content: str) -> Dict[str, str]:
    _check_write_size(content)
    _scan_content_conflicts(content, "global config")
    lowered = content.lower()
    for pattern in _SECRET_PATTERNS:
        if pattern.lower() in lowered:
            raise HTTPException(
                status_code=400,
                detail="Secrets must use environment variables, not global.yaml",
            )
    try:
        parsed = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="YAML root must be a mapping")
    _validate_global_schema(parsed)
    path = resolve_global_config_path()
    path.write_text(content, encoding="utf-8")
    root = REPO_ROOT.resolve()
    return {"path": str(path.resolve().relative_to(root))}


def _validate_global_schema(parsed: Dict[str, Any]) -> None:
    ai = parsed.get("ai")
    if ai is None:
        return
    if not isinstance(ai, dict):
        raise HTTPException(status_code=400, detail="ai must be a mapping")

    models = ai.get("models")
    if models is not None:
        if not isinstance(models, dict) or not models:
            raise HTTPException(status_code=400, detail="ai.models must be a non-empty mapping")
        for name, profile in models.items():
            if not isinstance(profile, dict) or not isinstance(profile.get("model"), str):
                raise HTTPException(status_code=400, detail=f"ai.models.{name} must include model string")

    tasks = ai.get("tasks")
    if tasks is not None and not isinstance(tasks, dict):
        raise HTTPException(status_code=400, detail="ai.tasks must be a mapping")

    if ai.get("default") is not None and not isinstance(ai.get("default"), str):
        raise HTTPException(status_code=400, detail="ai.default must be a string")

    # 兼容旧版单模型
    model = ai.get("model")
    if model is not None and not isinstance(model, str):
        raise HTTPException(status_code=400, detail="ai.model must be a string")
    provider = ai.get("provider")
    if provider is not None and not isinstance(provider, str):
        raise HTTPException(status_code=400, detail="ai.provider must be a string")
