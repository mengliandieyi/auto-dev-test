"""dev 分层逻辑测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from heal.dev import run_dev


def test_run_dev_invalid_layer():
    assert run_dev("project-a", "missing.md", layer="invalid") == 1


def test_run_dev_no_repos_returns_error(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    cfg = {"repos": {}}
    prd = Path("prds/project-a/dummy.md")
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text("# x", encoding="utf-8")
    try:
        with patch("config_loader.load_project_config", return_value=cfg):
            with patch("heal.dev.which_tool", return_value="/usr/bin/openhands"):
                rc = run_dev("project-a", str(prd), layer="frontend")
                assert rc == 1
    finally:
        prd.unlink(missing_ok=True)


def test_run_dev_dry_run_without_openhands(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    cfg = {
        "repos": {"frontend": "."},
        "dev": {"frontend_skill": "clean-ui"},
    }
    prd = Path("prds/project-a/dummy2.md")
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text("# x", encoding="utf-8")
    try:
        with patch("config_loader.load_project_config", return_value=cfg):
            with patch("heal.dev.which_tool", return_value=None):
                rc = run_dev("project-a", str(prd), layer="frontend")
                assert rc == 0
    finally:
        prd.unlink(missing_ok=True)
