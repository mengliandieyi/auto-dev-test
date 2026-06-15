"""业务仓 git 变更 API 单测。"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from api.services import repo_changes as rc
from api.services import path_safety


class TestRepoChanges(unittest.TestCase):
    def _init_git(self, path: Path) -> None:
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"],
            cwd=path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "test"],
            cwd=path,
            check=True,
            capture_output=True,
        )

    def test_describe_clean_repo(self):
        import api.config as api_config

        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            repo = troot / "acme-web"
            repo.mkdir()
            self._init_git(repo)
            (repo / "README.md").write_text("hi\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            cfg_dir = troot / "config" / "projects"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "demo.yaml").write_text(
                "project_id: demo\nrepos:\n  frontend: acme-web\n",
                encoding="utf-8",
            )
            old = api_config.REPO_ROOT
            api_config.REPO_ROOT = troot
            try:
                with patch.object(rc, "REPO_ROOT", troot), patch.object(path_safety, "REPO_ROOT", troot):
                    item = rc.describe_repo("demo", "frontend")
                self.assertTrue(item["is_git_repo"])
                self.assertIn("干净", item["summary"])
            finally:
                api_config.REPO_ROOT = old

    def test_describe_detects_modified_file(self):
        import api.config as api_config

        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            repo = troot / "acme-web"
            repo.mkdir()
            self._init_git(repo)
            f = repo / "app.ts"
            f.write_text("v1\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
            f.write_text("v2\n", encoding="utf-8")

            cfg_dir = troot / "config" / "projects"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "demo.yaml").write_text(
                "project_id: demo\nrepos:\n  frontend: acme-web\n",
                encoding="utf-8",
            )
            old = api_config.REPO_ROOT
            api_config.REPO_ROOT = troot
            try:
                with patch.object(rc, "REPO_ROOT", troot), patch.object(path_safety, "REPO_ROOT", troot):
                    item = rc.describe_repo("demo", "frontend")
                self.assertTrue(item["status_lines"])
                self.assertIn("变更", item["summary"])
                self.assertIn("app.ts", item["diff"])
            finally:
                api_config.REPO_ROOT = old

    def test_missing_repo_path(self):
        import api.config as api_config

        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            cfg_dir = troot / "config" / "projects"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "demo.yaml").write_text(
                "project_id: demo\nrepos:\n  backend: missing-dir\n",
                encoding="utf-8",
            )
            old = api_config.REPO_ROOT
            api_config.REPO_ROOT = troot
            try:
                with patch.object(rc, "REPO_ROOT", troot), patch.object(path_safety, "REPO_ROOT", troot):
                    item = rc.describe_repo("demo", "backend")
                self.assertFalse(item["exists"])
                self.assertIn("不存在", item["summary"])
            finally:
                api_config.REPO_ROOT = old

    def test_invalid_layer(self):
        with self.assertRaises(HTTPException):
            rc.list_repo_changes("project-a", "invalid")


if __name__ == "__main__":
    unittest.main()
