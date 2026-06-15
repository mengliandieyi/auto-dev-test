"""项目配置表单读写（合并进 config/projects/*.yaml）。"""

from __future__ import annotations

from typing import Any, Dict

import yaml
from fastapi import HTTPException

from api.config import REPO_ROOT
from api.models.schemas import ProjectSettingsForm
from api.services.path_safety import resolve_project_config_path, validate_project_id
from api.services.projects import write_project_yaml_text


def _load_cfg(project_id: str) -> Dict[str, Any]:
    validate_project_id(project_id)
    path = resolve_project_config_path(project_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Project config not found")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_project_settings_form(project_id: str) -> Dict[str, Any]:
    cfg = _load_cfg(project_id)
    repos = cfg.get("repos") if isinstance(cfg.get("repos"), dict) else {}
    vitest = cfg.get("vitest") if isinstance(cfg.get("vitest"), dict) else {}
    pw = cfg.get("playwright") if isinstance(cfg.get("playwright"), dict) else {}
    ws = pw.get("web_server") if isinstance(pw.get("web_server"), dict) else {}
    auth = cfg.get("auth") if isinstance(cfg.get("auth"), dict) else {}
    ai_fields = _read_ai_fields(cfg)
    dev = cfg.get("dev") if isinstance(cfg.get("dev"), dict) else {}
    return {
        "project_id": project_id,
        "project_name": str(cfg.get("project_name") or cfg.get("name") or project_id),
        "base_url": str(cfg.get("base_url") or ""),
        "health_check_url": str(cfg.get("health_check_url") or "/health"),
        "repos_frontend": str(repos.get("frontend") or ""),
        "repos_backend": str(repos.get("backend") or ""),
        "dev_skill_frontend": str(dev.get("frontend_skill") or ""),
        "dev_skill_backend": str(dev.get("backend_skill") or ""),
        "vitest_enabled": bool(vitest.get("enabled", False)),
        "vitest_frontend_root": str(vitest.get("frontend_root") or ""),
        "web_server_command": str(ws.get("command") or ""),
        "web_server_url": str(ws.get("url") or ""),
        "auth_login_url": str(auth.get("login_url") or "/login"),
        **ai_fields,
    }


def _read_ai_fields(cfg: Dict[str, Any]) -> Dict[str, Any]:
    from ai_resolver import KNOWN_TASKS
    from api.services.global_settings import resolve_ai_settings

    global_summary = resolve_ai_settings(None)
    g_tasks = global_summary.get("tasks") or {}

    def _global_default(task: str) -> str:
        return str((g_tasks.get(task) or {}).get("profile") or "sonnet")

    ai = cfg.get("ai") if isinstance(cfg.get("ai"), dict) else {}
    tasks = ai.get("tasks") if isinstance(ai.get("tasks"), dict) else {}
    fields: Dict[str, Any] = {"ai_use_global": not bool(tasks)}
    for task in KNOWN_TASKS:
        fields[f"ai_task_{task}"] = str(tasks.get(task) or _global_default(task))
    return fields


def _validate_ai_task_refs(project_cfg: Dict[str, Any], task_refs: Dict[str, str]) -> None:
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from ai_resolver import list_ai_profiles, merge_project_config
    from config_loader import load_global_config

    merged = merge_project_config(load_global_config(), project_cfg)
    ai = dict(merged.get("ai") or {})
    ai["tasks"] = task_refs
    merged["ai"] = ai
    names = {p["name"] for p in list_ai_profiles(merged)}
    for task, ref in task_refs.items():
        if ref not in names and not ref.startswith(("claude-", "gpt-")):
            raise HTTPException(status_code=400, detail=f"tasks.{task}: unknown profile '{ref}'")


def _apply_ai_settings(cfg: Dict[str, Any], form: ProjectSettingsForm) -> None:
    from ai_resolver import KNOWN_TASKS

    ai = dict(cfg.get("ai") or {})
    if form.ai_use_global:
        ai.pop("tasks", None)
    else:
        task_refs = {task: getattr(form, f"ai_task_{task}").strip() for task in KNOWN_TASKS}
        _validate_ai_task_refs(cfg, task_refs)
        ai["tasks"] = task_refs
    if ai:
        cfg["ai"] = ai
    elif "ai" in cfg:
        del cfg["ai"]


def write_project_settings_form(project_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    form = ProjectSettingsForm.model_validate(body)
    if form.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id mismatch")

    cfg = _load_cfg(project_id)
    cfg["project_id"] = project_id
    cfg["project_name"] = form.project_name.strip() or project_id
    cfg["base_url"] = form.base_url.strip()
    if form.health_check_url.strip():
        cfg["health_check_url"] = form.health_check_url.strip()
    elif "health_check_url" in cfg:
        del cfg["health_check_url"]

    repos = dict(cfg.get("repos") or {})
    if form.repos_frontend.strip():
        repos["frontend"] = form.repos_frontend.strip()
    elif "frontend" in repos:
        del repos["frontend"]
    if form.repos_backend.strip():
        repos["backend"] = form.repos_backend.strip()
    elif "backend" in repos:
        del repos["backend"]
    if repos:
        cfg["repos"] = repos
    elif "repos" in cfg:
        del cfg["repos"]

    dev = dict(cfg.get("dev") or {})
    if form.dev_skill_frontend.strip():
        dev["frontend_skill"] = form.dev_skill_frontend.strip()
    elif "frontend_skill" in dev:
        del dev["frontend_skill"]
    if form.dev_skill_backend.strip():
        dev["backend_skill"] = form.dev_skill_backend.strip()
    elif "backend_skill" in dev:
        del dev["backend_skill"]
    if dev:
        cfg["dev"] = dev
    elif "dev" in cfg:
        del cfg["dev"]

    vitest = dict(cfg.get("vitest") or {})
    vitest["enabled"] = form.vitest_enabled
    if form.vitest_frontend_root.strip():
        vitest["frontend_root"] = form.vitest_frontend_root.strip()
    elif not form.vitest_enabled:
        pass
    else:
        vitest.pop("frontend_root", None)
    cfg["vitest"] = vitest

    pw = dict(cfg.get("playwright") or {})
    if form.web_server_command.strip() or form.web_server_url.strip():
        ws = dict(pw.get("web_server") or {})
        if form.web_server_command.strip():
            ws["command"] = form.web_server_command.strip()
        if form.web_server_url.strip():
            ws["url"] = form.web_server_url.strip()
        pw["web_server"] = ws
    elif "web_server" in pw:
        pw.pop("web_server", None)
    if pw:
        cfg["playwright"] = pw

    auth = dict(cfg.get("auth") or {})
    if form.auth_login_url.strip():
        auth["login_url"] = form.auth_login_url.strip()
        cfg["auth"] = auth

    _apply_ai_settings(cfg, form)

    text = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)
    write_project_yaml_text(project_id, text)
    return read_project_settings_form(project_id)
