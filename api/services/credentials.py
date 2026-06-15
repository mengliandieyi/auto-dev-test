"""API Key / Base URL 管理（写入本地 .env）。"""

from __future__ import annotations

from typing import Optional

from bootstrap import setup_repo_paths

setup_repo_paths()
from env_store import read_credentials, write_credentials  # noqa: E402


def get_credentials() -> dict:
    return read_credentials()


def update_credentials(
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    use_llm_parse: Optional[bool] = None,
    clear_api_key: bool = False,
    clear_openai_api_key: bool = False,
) -> dict:
    return write_credentials(
        api_key=api_key,
        base_url=base_url,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        use_llm_parse=use_llm_parse,
        clear_api_key=clear_api_key,
        clear_openai_api_key=clear_openai_api_key,
    )
