"""PRD 路径与项目绑定校验。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


from fastapi import HTTPException

from api.services.path_safety import resolve_prd_path
from validator import validate


class TestPrdProjectBinding(unittest.TestCase):
    def test_validator_rejects_wrong_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "bad.md"
            prd.write_text(
                "---\nprd_id: X\nversion: 1.0.0\nproject: project-b\n---\n\n"
                "## 功能名称\n\n登录\n\n## 需求说明\n\n"
                "- 作为 用户，我希望 登录，以便 使用系统\n\n"
                "## 验收标准\n\n- [ ] 一条\n\n"
                "## 页面交互\n\n1. 打开\n2. 提交\n",
                encoding="utf-8",
            )
            result = validate(prd, expected_project="project-a")
            self.assertFalse(result.valid)
            self.assertTrue(any("project-b" in e.message for e in result.errors))

    def test_resolve_prd_path_rejects_outside_prd_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            prd_dir = troot / "prds" / "project-a"
            prd_dir.mkdir(parents=True)
            (prd_dir / "ok.md").write_text("---\nprd_id: X\n---\n", encoding="utf-8")
            other = troot / "prds" / "project-b" / "evil.md"
            other.parent.mkdir(parents=True)
            other.write_text("---\nprd_id: X\n---\n", encoding="utf-8")
            cfg_dir = troot / "config" / "projects"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "project-a.yaml").write_text(
                f'project_id: project-a\nprd_dir: "{prd_dir}"\n',
                encoding="utf-8",
            )
            import api.config as api_config
            import api.services.path_safety as ps

            old = api_config.REPO_ROOT
            api_config.REPO_ROOT = troot
            ps.REPO_ROOT = troot
            try:
                with self.assertRaises(HTTPException) as ctx:
                    resolve_prd_path("project-a", "prds/project-b/evil.md")
                self.assertEqual(ctx.exception.status_code, 400)
            finally:
                api_config.REPO_ROOT = old
                ps.REPO_ROOT = old

    def test_resolve_prd_path_accepts_in_project_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            prd_dir = troot / "prds" / "project-a"
            prd_dir.mkdir(parents=True)
            prd = prd_dir / "PROJ-001_login.md"
            prd.write_text("---\nprd_id: PROJ-001\n---\n", encoding="utf-8")
            cfg_dir = troot / "config" / "projects"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "project-a.yaml").write_text(
                f'project_id: project-a\nprd_dir: "{prd_dir}"\n',
                encoding="utf-8",
            )
            import api.config as api_config
            import api.services.path_safety as ps

            old = api_config.REPO_ROOT
            api_config.REPO_ROOT = troot
            ps.REPO_ROOT = troot
            try:
                resolved = resolve_prd_path("project-a", "prds/project-a/PROJ-001_login.md")
                self.assertEqual(resolved.name, "PROJ-001_login.md")
            finally:
                api_config.REPO_ROOT = old
                ps.REPO_ROOT = old


if __name__ == "__main__":
    unittest.main()
