"""路径安全单测（M3）。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import HTTPException

from api.services.path_safety import resolve_prd_file, validate_project_id


class TestPathSafety(unittest.TestCase):
    def test_invalid_project_id(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_project_id("../evil")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_traversal_filename_rejected(self):
        with self.assertRaises(HTTPException):
            resolve_prd_file("project-a", "../secrets.md")

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            prd_dir = Path(tmp) / "prds" / "project-a"
            prd_dir.mkdir(parents=True)
            target = prd_dir / "real.md"
            target.write_text("---\nprd_id: X\n---\n", encoding="utf-8")
            link = prd_dir / "link.md"
            link.symlink_to(target)
            cfg_dir = Path(tmp) / "config" / "projects"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "project-a.yaml").write_text(
                f'prd_dir: "{prd_dir}"\n', encoding="utf-8"
            )
            import api.config as api_config
            import api.services.path_safety as ps

            old_root = api_config.REPO_ROOT
            api_config.REPO_ROOT = Path(tmp)
            ps.REPO_ROOT = Path(tmp)
            try:
                with self.assertRaises(HTTPException) as ctx:
                    resolve_prd_file("project-a", "link.md")
                self.assertEqual(ctx.exception.status_code, 400)
            finally:
                api_config.REPO_ROOT = old_root
                ps.REPO_ROOT = old_root


if __name__ == "__main__":
    unittest.main()
