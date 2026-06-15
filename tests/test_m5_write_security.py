"""M5 写接口安全单测。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException



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

    def test_global_yaml_roundtrip(self):
        import api.services.global_settings as gs

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            gs.REPO_ROOT = Path(tmp)
            (Path(tmp) / "config").mkdir(parents=True, exist_ok=True)
            try:
                yaml_text = (
                    "ai:\n  provider: anthropic\n  model: claude-sonnet-4-5\n"
                    "  max_tokens: 4096\n"
                )
                gs.write_global_yaml_text(yaml_text)
                self.assertEqual(gs.read_global_yaml_text()["content"], yaml_text)
            finally:
                gs.REPO_ROOT = old
                self._restore_repo(old, ac, ps, proj)

    def test_reject_secret_in_global_yaml(self):
        import api.services.global_settings as gs

        with tempfile.TemporaryDirectory() as tmp:
            old, ac, ps, proj = self._isolate_repo(tmp)
            gs.REPO_ROOT = Path(tmp)
            (Path(tmp) / "config").mkdir(parents=True, exist_ok=True)
            try:
                with self.assertRaises(HTTPException) as ctx:
                    gs.write_global_yaml_text("ai:\n  api_key: sk-ant-secret\n")
                self.assertIn("environment", ctx.exception.detail.lower())
            finally:
                gs.REPO_ROOT = old
                self._restore_repo(old, ac, ps, proj)

    def test_ai_settings_form_roundtrip(self):
        import api.config as api_config
        import api.services.global_settings as gs
        import api.services.path_safety as ps
        import env_store as es

        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            (troot / "config").mkdir(parents=True)
            (troot / "config" / "global.yaml").write_text(
                "heal:\n  max_iterations: 3\nai:\n  provider: anthropic\n  default: sonnet\n"
                "  models:\n    sonnet:\n      model: claude-sonnet-4-5\n      max_tokens: 8096\n"
                "  tasks:\n    parse: sonnet\n    heal: sonnet\n",
                encoding="utf-8",
            )
            old = api_config.REPO_ROOT
            old_env = es.ENV_PATH
            api_config.REPO_ROOT = troot
            ps.REPO_ROOT = troot
            gs.REPO_ROOT = troot
            es.ENV_PATH = troot / ".env"
            try:
                body = {
                    "provider": "anthropic",
                    "default_profile": "haiku",
                    "profiles": [
                        {
                            "id": "sonnet",
                            "provider": "anthropic",
                            "model": "claude-sonnet-4-5",
                            "max_tokens": 8096,
                            "base_url": "https://proxy.example.com",
                            "api_key": "sk-ant-sonnet-key-1234",
                        },
                        {
                            "id": "haiku",
                            "provider": "anthropic",
                            "model": "claude-haiku-3-5",
                            "max_tokens": 4096,
                            "base_url": "",
                        },
                    ],
                    "tasks": {
                        "parse": "haiku",
                        "heal": "sonnet",
                        "dev_frontend": "sonnet",
                        "dev_backend": "haiku",
                    },
                }
                saved = gs.write_ai_settings_form(body)
                self.assertEqual(saved["tasks"]["parse"], "haiku")
                self.assertEqual(saved["tasks"]["dev_backend"], "haiku")
                parsed = gs._load_global_parsed()
                self.assertEqual(parsed["heal"]["max_iterations"], 3)
                self.assertEqual(parsed["ai"]["models"]["haiku"]["model"], "claude-haiku-3-5")
                self.assertEqual(
                    parsed["ai"]["models"]["sonnet"]["base_url"],
                    "https://proxy.example.com",
                )
                self.assertNotIn("base_url", parsed["ai"]["models"]["haiku"])
                self.assertTrue(saved["profiles"][0]["api_key_set"])
                self.assertEqual(es.read_profile_api_key("sonnet"), "sk-ant-sonnet-key-1234")

                reread = gs.read_ai_settings_form()
                sonnet = next(p for p in reread["profiles"] if p["id"] == "sonnet")
                self.assertEqual(sonnet["base_url"], "https://proxy.example.com")
                self.assertTrue(sonnet["api_key_set"])
                self.assertIn("…", sonnet["api_key_preview"])
            finally:
                api_config.REPO_ROOT = old
                ps.REPO_ROOT = old
                gs.REPO_ROOT = old
                es.ENV_PATH = old_env


if __name__ == "__main__":
    unittest.main()
