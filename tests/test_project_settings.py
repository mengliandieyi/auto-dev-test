"""项目配置表单读写测试"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from api.services import project_settings as ps


class TestProjectSettings(unittest.TestCase):
    def test_read_project_a(self):
        form = ps.read_project_settings_form("project-a")
        self.assertEqual(form["project_id"], "project-a")
        self.assertIn("127.0.0.1", form["base_url"])
        self.assertEqual(form["repos_frontend"], "../acme-web")
        self.assertTrue(form["ai_use_global"])

    def test_roundtrip_preserves_extra_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_dir = root / "config" / "projects"
            cfg_dir.mkdir(parents=True)
            path = cfg_dir / "demo.yaml"
            original = {
                "project_id": "demo",
                "project_name": "Demo",
                "base_url": "http://localhost:3000",
                "custom_flag": True,
                "report": {"format": "text"},
            }
            path.write_text(yaml.safe_dump(original, allow_unicode=True), encoding="utf-8")

            with mock.patch("api.services.project_settings.resolve_project_config_path", return_value=path), \
                 mock.patch("api.services.project_settings.validate_project_id"), \
                 mock.patch("api.services.project_settings.write_project_yaml_text") as mock_write:
                body = {
                    "project_id": "demo",
                    "project_name": "Demo Updated",
                    "base_url": "https://staging.example.com",
                    "health_check_url": "/health",
                    "repos_frontend": "../web",
                    "repos_backend": "",
                    "vitest_enabled": True,
                    "vitest_frontend_root": "",
                    "web_server_command": "",
                    "web_server_url": "",
                    "auth_login_url": "/login",
                    "ai_use_global": False,
                    "ai_task_parse": "sonnet",
                    "ai_task_heal": "sonnet",
                    "ai_task_dev_frontend": "sonnet",
                    "ai_task_dev_backend": "sonnet",
                }
                ps.write_project_settings_form("demo", body)
                written = mock_write.call_args[0][1]
                parsed = yaml.safe_load(written)
                self.assertEqual(parsed["base_url"], "https://staging.example.com")
                self.assertEqual(parsed["repos"]["frontend"], "../web")
                self.assertTrue(parsed["custom_flag"])
                self.assertEqual(parsed["ai"]["tasks"]["parse"], "sonnet")
                self.assertEqual(parsed["report"]["format"], "text")


if __name__ == "__main__":
    unittest.main()
