"""M5 写接口安全单测。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestM5WriteSecurity(unittest.TestCase):
    def _isolate_repo(self, tmp: str):
        import api.config as api_config
        import api.services.path_safety as ps
        import api.services.projects as proj

        troot = Path(tmp)
        cfg_dir = troot / "config" / "projects"
        cfg_dir.mkdir(parents=True)
        prd_dir = troot / "prds" / "project-a"
        prd_dir.mkdir(parents=True)
        (cfg_dir / "project-a.yaml").write_text(
            "project_id: project-a\nprd_dir: ./prds/project-a/\n",
            encoding="utf-8",
        )
        (prd_dir / "PROJ-001_login.md").write_text(
            "---\nprd_id: PROJ-001\n---\n\nbody\n",
            encoding="utf-8",
        )
        old = api_config.REPO_ROOT
        api_config.REPO_ROOT = troot
        ps.REPO_ROOT = troot
        proj.REPO_ROOT = troot
        return old, api_config, ps, proj

    def _restore_repo(self, old, api_config, ps, proj):
        api_config.REPO_ROOT = old
        ps.REPO_ROOT = old
        proj.REPO_ROOT = old

    def test_reject_invalid_project_id(self):
        from api.services.path_safety import validate_project_id

        with self.assertRaises(HTTPException) as ctx:
            validate_project_id("../evil")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_reject_prd_path_traversal(self):
        from api.services.path_safety import resolve_prd_file

        with self.assertRaises(HTTPException):
            resolve_prd_file("project-a", "../secrets.md")

    def test_reject_merge_conflict_in_prd_write(self):
        from api.services.projects import write_prd_content

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            try:
                with self.assertRaises(HTTPException) as ctx:
                    write_prd_content("project-a", "PROJ-001_login.md", "<<<<<<< HEAD\n")
                self.assertIn("MERGE_CONFLICT", ctx.exception.detail)
            finally:
                self._restore_repo(old, ac, ps, proj)

    def test_reject_oversized_upload(self):
        from api.services.projects import upload_prd_file

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            try:
                with self.assertRaises(HTTPException) as ctx:
                    upload_prd_file("project-a", "big.md", b"x" * (1_048_576 + 1))
                self.assertIn("1MB", ctx.exception.detail)
            finally:
                self._restore_repo(old, ac, ps, proj)

    def test_upload_and_write_prd_roundtrip(self):
        from api.services.projects import upload_prd_file, write_prd_content

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            try:
                content = "---\nprd_id: PROJ-099\nversion: 0.0.1\n---\n\n## 功能名称\n\ntest\n"
                upload_prd_file("project-a", "PROJ-099_test.md", content.encode())
                updated = content + "\n## 验收标准\n\n- [ ] ok\n"
                write_prd_content("project-a", "PROJ-099_test.md", updated)
                path = Path(tmp) / "prds/project-a/PROJ-099_test.md"
                self.assertEqual(path.read_text(encoding="utf-8"), updated)
            finally:
                self._restore_repo(old, ac, ps, proj)

    def test_project_yaml_project_id_mismatch(self):
        from api.services.projects import write_project_yaml_text

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            try:
                with self.assertRaises(HTTPException) as ctx:
                    write_project_yaml_text("project-a", "project_id: project-b\n")
                self.assertIn("project_id", ctx.exception.detail)
            finally:
                self._restore_repo(old, ac, ps, proj)


if __name__ == "__main__":
    unittest.main()
