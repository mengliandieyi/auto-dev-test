"""解析 ai 配置：多模型 profile + 按任务（parse / heal）分配。"""

from __future__ import annotations

from typing import Any, Dict, List

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_PROVIDER = "anthropic"
DEFAULT_MAX_TOKENS = 8096
KNOWN_TASKS = ("parse", "heal", "dev_frontend", "dev_backend")


def _deep_merge_dict(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def merge_project_config(global_cfg: dict, project_cfg: dict) -> dict:
    """合并全局与项目配置；`ai` 段深度合并，项目可覆盖 tasks。"""
    merged = {**global_cfg, **project_cfg}
    if isinstance(global_cfg.get("ai"), dict) and isinstance(project_cfg.get("ai"), dict):
        merged["ai"] = _deep_merge_dict(global_cfg["ai"], project_cfg["ai"])
    return merged


def _legacy_profile(ai: dict) -> Dict[str, Any]:
    return {
        "provider": ai.get("provider", DEFAULT_PROVIDER),
        "model": ai.get("model", DEFAULT_MODEL),
        "max_tokens": int(ai.get("max_tokens", DEFAULT_MAX_TOKENS)),
    }


def _normalize_profile(ai: dict, profile: dict) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "provider": profile.get("provider", ai.get("provider", DEFAULT_PROVIDER)),
        "model": profile["model"],
        "max_tokens": int(profile.get("max_tokens", ai.get("max_tokens", DEFAULT_MAX_TOKENS))),
    }
    base_url = profile.get("base_url")
    if isinstance(base_url, str) and base_url.strip():
        out["base_url"] = base_url.strip().rstrip("/")
    return out


def list_ai_profiles(config: dict) -> List[Dict[str, Any]]:
    ai = config.get("ai") or {}
    if not isinstance(ai, dict):
        return []
    models = ai.get("models")
    if not isinstance(models, dict) or not models:
        legacy = _legacy_profile(ai)
        return [{"name": "default", **legacy}]
    items: List[Dict[str, Any]] = []
    for name, profile in models.items():
        if not isinstance(profile, dict) or "model" not in profile:
            continue
        items.append({"name": str(name), **_normalize_profile(ai, profile)})
    return items


def resolve_ai_for_task(config: dict, task: str) -> Dict[str, Any]:
    """按任务返回 {provider, model, max_tokens, profile}。"""
    ai = config.get("ai") or {}
    if not isinstance(ai, dict):
        return {**_legacy_profile({}), "profile": "default"}

    models = ai.get("models")
    if not isinstance(models, dict) or not models:
        return {**_legacy_profile(ai), "profile": "default"}

    profiles = {str(k): _normalize_profile(ai, v) for k, v in models.items() if isinstance(v, dict) and v.get("model")}
    default_name = str(ai.get("default") or next(iter(profiles), "default"))
    tasks = ai.get("tasks") if isinstance(ai.get("tasks"), dict) else {}
    ref = str(tasks.get(task) or default_name)

    if ref in profiles:
        return {**profiles[ref], "profile": ref}

    if ref.startswith("claude-") or ref.startswith("gpt-"):
        provider = DEFAULT_PROVIDER if ref.startswith("claude-") else "openai"
        return {
            "provider": provider,
            "model": ref,
            "max_tokens": int(ai.get("max_tokens", DEFAULT_MAX_TOKENS)),
            "profile": ref,
        }

    if default_name in profiles:
        return {**profiles[default_name], "profile": default_name}

    first_name, first_profile = next(iter(profiles.items()))
    return {**first_profile, "profile": first_name}


def ai_resolution_summary(config: dict) -> Dict[str, Any]:
    return {
        "profiles": list_ai_profiles(config),
        "tasks": {
            task: resolve_ai_for_task(config, task)
            for task in KNOWN_TASKS
        },
    }
