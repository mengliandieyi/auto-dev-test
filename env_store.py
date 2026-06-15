"""本地 .env 读写（API Key / Base URL），不进入 git。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Optional

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
_ENV_LOADED = False

_MANAGED_KEYS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "USE_LLM_PARSE",
)


def _parse_env_file(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        data[key] = value
    return data


def profile_env_key(profile_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", profile_id.strip().upper())
    return f"LLM_KEY_{safe}"


def _format_env_file(data: Dict[str, str]) -> str:
    lines = [
        "# auto-dev-test 本地密钥（勿提交 git）",
        "# 可在管理台「API 设置」编辑",
        "",
    ]
    written: set[str] = set()
    for key in _MANAGED_KEYS:
        if key in data and data[key] != "":
            lines.append(f"{key}={data[key]}")
            written.add(key)
    for key in sorted(data):
        if key.startswith("LLM_KEY_") and key not in written and data[key] != "":
            lines.append(f"{key}={data[key]}")
            written.add(key)
    lines.append("")
    return "\n".join(lines)


def _preview_key(api_key: str) -> str:
    if not api_key:
        return ""
    return f"{api_key[:7]}…{api_key[-4:]}" if len(api_key) > 12 else "已配置"


def _provider_block(api_key: str, base_url: str) -> Dict[str, object]:
    return {
        "api_key_set": bool(api_key),
        "api_key_preview": _preview_key(api_key),
        "base_url": base_url,
    }


def ensure_env_loaded() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if ENV_PATH.is_file():
        for key, value in _parse_env_file(ENV_PATH.read_text(encoding="utf-8")).items():
            os.environ.setdefault(key, value)
    _ENV_LOADED = True


def read_credentials() -> Dict[str, object]:
    ensure_env_loaded()
    file_data = _parse_env_file(ENV_PATH.read_text(encoding="utf-8")) if ENV_PATH.is_file() else {}
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or file_data.get("ANTHROPIC_API_KEY", "")
    anthropic_url = os.environ.get("ANTHROPIC_BASE_URL") or file_data.get("ANTHROPIC_BASE_URL", "")
    openai_key = os.environ.get("OPENAI_API_KEY") or file_data.get("OPENAI_API_KEY", "")
    openai_url = os.environ.get("OPENAI_BASE_URL") or file_data.get("OPENAI_BASE_URL", "")
    use_llm = (os.environ.get("USE_LLM_PARSE") or file_data.get("USE_LLM_PARSE", "0")) == "1"
    try:
        env_path = str(ENV_PATH.relative_to(ROOT))
    except ValueError:
        env_path = str(ENV_PATH)

    anthropic = _provider_block(anthropic_key, anthropic_url)
    openai = _provider_block(openai_key, openai_url)
    return {
        "anthropic": anthropic,
        "openai": openai,
        "use_llm_parse": use_llm,
        "env_path": env_path,
        # 兼容旧字段（Anthropic）
        "api_key_set": anthropic["api_key_set"],
        "api_key_preview": anthropic["api_key_preview"],
        "base_url": anthropic_url,
    }


def _validate_api_key(key: str, provider: str, *, allow_proxy: bool = False) -> None:
    if key.startswith("sk-"):
        return
    if allow_proxy and len(key) >= 8:
        return
    label = "OpenAI" if provider == "openai" else "Anthropic"
    raise HTTPException(status_code=400, detail=f"{label} API Key 格式不正确（应以 sk- 开头）")


def read_profile_api_key(profile_id: str) -> str:
    ensure_env_loaded()
    env_name = profile_env_key(profile_id)
    file_data = _parse_env_file(ENV_PATH.read_text(encoding="utf-8")) if ENV_PATH.is_file() else {}
    return os.environ.get(env_name) or file_data.get(env_name, "")


def write_profile_api_keys(
    updates: Dict[str, Optional[str]],
    *,
    providers: Optional[Dict[str, str]] = None,
) -> None:
    """按 profile id 写入独立 API Key；updates 值为空字符串表示清除。"""
    current = _parse_env_file(ENV_PATH.read_text(encoding="utf-8")) if ENV_PATH.is_file() else {}
    providers = providers or {}
    for profile_id, api_key in updates.items():
        env_name = profile_env_key(profile_id)
        provider = providers.get(profile_id, "anthropic")
        if api_key is None:
            continue
        key = api_key.strip()
        if not key:
            current.pop(env_name, None)
            os.environ.pop(env_name, None)
            continue
        _validate_api_key(key, provider, allow_proxy=True)
        current[env_name] = key
        os.environ[env_name] = key
    ENV_PATH.write_text(_format_env_file(current), encoding="utf-8")
    global _ENV_LOADED
    _ENV_LOADED = True


def clear_profile_api_keys(profile_ids: list[str]) -> None:
    write_profile_api_keys({pid: "" for pid in profile_ids})


def _validate_base_url(url: str) -> None:
    if url and not re.match(r"^https?://", url):
        raise HTTPException(status_code=400, detail="Base URL 需以 http:// 或 https:// 开头")


def write_credentials(
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    use_llm_parse: Optional[bool] = None,
    clear_api_key: bool = False,
    clear_openai_api_key: bool = False,
) -> Dict[str, object]:
    current = _parse_env_file(ENV_PATH.read_text(encoding="utf-8")) if ENV_PATH.is_file() else {}

    if clear_api_key:
        current.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
    elif api_key is not None and api_key.strip():
        key = api_key.strip()
        _validate_api_key(key, "anthropic")
        current["ANTHROPIC_API_KEY"] = key
        os.environ["ANTHROPIC_API_KEY"] = key

    if base_url is not None:
        url = base_url.strip()
        _validate_base_url(url)
        if url:
            current["ANTHROPIC_BASE_URL"] = url.rstrip("/")
            os.environ["ANTHROPIC_BASE_URL"] = url.rstrip("/")
        else:
            current.pop("ANTHROPIC_BASE_URL", None)
            os.environ.pop("ANTHROPIC_BASE_URL", None)

    if clear_openai_api_key:
        current.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
    elif openai_api_key is not None and openai_api_key.strip():
        key = openai_api_key.strip()
        _validate_api_key(key, "openai")
        current["OPENAI_API_KEY"] = key
        os.environ["OPENAI_API_KEY"] = key

    if openai_base_url is not None:
        url = openai_base_url.strip()
        _validate_base_url(url)
        if url:
            current["OPENAI_BASE_URL"] = url.rstrip("/")
            os.environ["OPENAI_BASE_URL"] = url.rstrip("/")
        else:
            current.pop("OPENAI_BASE_URL", None)
            os.environ.pop("OPENAI_BASE_URL", None)

    if use_llm_parse is not None:
        current["USE_LLM_PARSE"] = "1" if use_llm_parse else "0"
        os.environ["USE_LLM_PARSE"] = current["USE_LLM_PARSE"]

    ENV_PATH.write_text(_format_env_file(current), encoding="utf-8")
    global _ENV_LOADED
    _ENV_LOADED = True
    return read_credentials()
