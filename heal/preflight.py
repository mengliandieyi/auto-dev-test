"""Preflight 探活（TECH §8.4）。"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


def run_preflight(config: dict) -> Tuple[bool, str]:
    base = (config.get("base_url") or "").rstrip("/")
    if not base:
        return False, "base_url 未配置"

    auth = config_auth_header(config)
    health_path = config.get("health_check_url") or "/health"
    ok, msg = _probe(f"{base}{health_path}", auth)
    if ok:
        return True, msg
    ok2, msg2 = _probe(base + "/", auth)
    if ok2:
        return True, f"health 失败，根路径可达：{msg2}"
    return False, f"探活失败：{msg}; fallback: {msg2}"


def _probe(url: str, auth: str = "") -> Tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        if auth:
            req.add_header("Authorization", auth)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 400, f"{url} -> {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, f"{url} -> 404"
        return 200 <= e.code < 400, f"{url} -> {e.code}"
    except Exception as e:
        return False, str(e)


def config_auth_header(config: dict) -> str:
    auth = config.get("auth") or {}
    if auth.get("type") == "token":
        env_key = auth.get("token_env", "")
        token = os.getenv(env_key, "") if env_key else ""
        return f"Bearer {token}" if token else ""
    return ""
