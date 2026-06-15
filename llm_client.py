"""统一 LLM 客户端（Anthropic / OpenAI）。"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from env_store import ensure_env_loaded, read_profile_api_key

SUPPORTED_PROVIDERS = ("anthropic", "openai")


def provider_configured(provider: str) -> bool:
    ensure_env_loaded()
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def any_llm_configured() -> bool:
    return any(provider_configured(p) for p in SUPPORTED_PROVIDERS)


def ensure_provider_configured(provider: str) -> None:
    if provider not in SUPPORTED_PROVIDERS:
        raise EnvironmentError(f"不支持的 provider: {provider}")
    if not provider_configured(provider):
        env_key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        raise EnvironmentError(f"未配置 {env_key}，请在管理台「API 设置」填写")


def _resolve_credentials(ai_cfg: dict) -> tuple[str, str, str]:
    """返回 (provider, api_key, base_url)，优先 profile 级配置。"""
    ensure_env_loaded()
    provider = ai_cfg.get("provider", "anthropic")
    profile = str(ai_cfg.get("profile") or "")
    api_key = ""
    base_url = str(ai_cfg.get("base_url") or "").strip()

    if profile:
        api_key = read_profile_api_key(profile)

    if not api_key:
        env_key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        api_key = os.environ.get(env_key, "")

    if not base_url:
        env_url = "OPENAI_BASE_URL" if provider == "openai" else "ANTHROPIC_BASE_URL"
        base_url = os.environ.get(env_url, "").strip()

    return provider, api_key, base_url.rstrip("/")


def create_anthropic_client(*, api_key: Optional[str] = None, base_url: Optional[str] = None):
    import anthropic

    ensure_env_loaded()
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError("未配置 API Key，请在管理台「API 设置」填写")

    kwargs: Dict[str, Any] = {"api_key": key}
    url = (base_url if base_url is not None else os.environ.get("ANTHROPIC_BASE_URL", "")).strip()
    if url:
        kwargs["base_url"] = url.rstrip("/")
    return anthropic.Anthropic(**kwargs)


def create_openai_client(*, api_key: Optional[str] = None, base_url: Optional[str] = None):
    from openai import OpenAI

    ensure_env_loaded()
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("未配置 API Key，请在管理台「API 设置」填写")

    kwargs: Dict[str, Any] = {"api_key": key}
    url = (base_url if base_url is not None else os.environ.get("OPENAI_BASE_URL", "")).strip()
    if url:
        kwargs["base_url"] = url.rstrip("/")
    return OpenAI(**kwargs)


def llm_complete(ai_cfg: dict, prompt: str, *, max_tokens: Optional[int] = None) -> Tuple[str, float]:
    """按 profile 配置调用 LLM，返回 (text, token_cost)。"""
    provider, api_key, base_url = _resolve_credentials(ai_cfg)
    model = ai_cfg["model"]
    limit = int(max_tokens if max_tokens is not None else ai_cfg["max_tokens"])
    if not api_key:
        ensure_provider_configured(provider)

    if provider == "openai":
        client = create_openai_client(api_key=api_key or None, base_url=base_url or None)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=limit,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.choices[0].message.content or "") if resp.choices else ""
        usage = getattr(resp, "usage", None)
        tokens = float(getattr(usage, "total_tokens", 0) or 0)
        return text, tokens

    client = create_anthropic_client(api_key=api_key or None, base_url=base_url or None)
    msg = client.messages.create(
        model=model,
        max_tokens=limit,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    usage = getattr(msg, "usage", None)
    tokens = float((usage.input_tokens if usage else 0) + (usage.output_tokens if usage else 0))
    return text, tokens
