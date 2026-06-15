"""从 config/projects/*.yaml 导出 Playwright 运行时配置（供 playwright.config.ts 读取）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from config_loader import load_project_config, resolve_reuse_existing_server

ROOT = Path(__file__).parent
RUNTIME_PATH = ROOT / "test-generator" / "playwright.runtime.json"


def _project_playwright_entry(project_id: str) -> Dict[str, Any]:
    cfg = load_project_config(project_id)
    pw = cfg.get("playwright") if isinstance(cfg.get("playwright"), dict) else {}
    ws = pw.get("web_server") if isinstance(pw.get("web_server"), dict) else {}
    base_url = str(cfg.get("base_url") or "http://127.0.0.1:4173").rstrip("/")
    entry: Dict[str, Any] = {
        "name": project_id,
        "testDir": f"tests/generated/{project_id}/e2e",
        "baseURL": base_url,
    }
    command = str(ws.get("command") or "").strip()
    if command:
        url = str(ws.get("url") or base_url).rstrip("/")
        reuse = pw.get("reuse_existing_server", ws.get("reuse_existing_server", "auto"))
        entry["webServer"] = {
            "command": command,
            "url": f"{url}/",
            "reuseExistingServer": resolve_reuse_existing_server(reuse),
        }
    return entry


def export_playwright_runtime(repo_root: Path | None = None) -> Path:
    root = repo_root or ROOT
    projects_dir = root / "config" / "projects"
    projects: List[Dict[str, Any]] = []
    for yaml_path in sorted(projects_dir.glob("*.yaml")):
        projects.append(_project_playwright_entry(yaml_path.stem))
    payload = {"projects": projects}
    out = root / "test-generator" / "playwright.runtime.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    path = export_playwright_runtime()
    print(f"Wrote {path}")
