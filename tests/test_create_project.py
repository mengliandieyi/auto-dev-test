"""新建项目 API 单测。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestCreateProject(unittest.TestCase):
    def _isolate_repo(self, tmp: str):
        import api.config as api_config
        import api.services.path_safety as ps
        import api.services.projects as proj

        troot = Path(tmp)
        (troot / "config" / "projects").mkdir(parents=True)
        old = api_config.REPO_ROOT
        api_config.REPO_ROOT = troot
        ps.REPO_ROOT = troot
        proj.REPO_ROOT = troot
        return old, api_config, ps, proj

    def _restore_repo(self, old, api_config, ps, proj):
        api_config.REPO_ROOT = old
        ps.REPO_ROOT = old
        proj.REPO_ROOT = old

    def test_create_project_scaffold(self):
        from api.services.projects import create_project, list_projects

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            try:
                created = create_project("my-app", "我的应用", "http://127.0.0.1:3000")
                self.assertEqual(created["id"], "my-app")
                self.assertEqual(created["name"], "我的应用")
                self.assertTrue((Path(tmp) / "config" / "projects" / "my-app.yaml").is_file())
                self.assertTrue((Path(tmp) / "prds" / "my-app").is_dir())
                self.assertTrue((Path(tmp) / "reports" / "my-app").is_dir())
                names = [p["id"] for p in list_projects()]
                self.assertIn("my-app", names)
            finally:
                self._restore_repo(old, ac, ps, proj)

    def test_reject_duplicate_project(self):
        from api.services.projects import create_project

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            try:
                create_project("demo", "Demo", "http://127.0.0.1:4173")
                with self.assertRaises(HTTPException) as ctx:
                    create_project("demo", "Demo 2", "http://127.0.0.1:4174")
                self.assertEqual(ctx.exception.status_code, 409)
            finally:
                self._restore_repo(old, ac, ps, proj)

    def test_reject_invalid_project_id(self):
        from api.services.path_safety import validate_new_project_id

        with self.assertRaises(HTTPException) as ctx:
            validate_new_project_id("../evil")
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
