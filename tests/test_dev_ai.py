"""dev LLM 配置与 OpenHands 环境变量测试。"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from heal.dev import _dev_ai_task, _run_layer_dev, build_openhands_argv
from llm_client import subprocess_llm_env


class TestDevAiEnv(unittest.TestCase):
    def test_dev_ai_task_names(self):
        self.assertEqual(_dev_ai_task("frontend"), "dev_frontend")
        self.assertEqual(_dev_ai_task("backend"), "dev_backend")

    def test_subprocess_llm_env_maps_openhands_vars(self):
        with patch("llm_client._resolve_credentials", return_value=("anthropic", "sk-test", "https://api.example")):
            env = subprocess_llm_env(
                {
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 4096,
                    "profile": "sonnet",
                }
            )
        self.assertEqual(env["LLM_MODEL"], "claude-sonnet-4-5")
        self.assertEqual(env["LLM_API_KEY"], "sk-test")
        self.assertEqual(env["LLM_BASE_URL"], "https://api.example")
        self.assertEqual(env["AUTO_DEV_LLM_PROFILE"], "sonnet")

    def test_run_layer_dev_passes_override_with_envs(self):
        captured: dict = {}

        def fake_run(cmd, cwd=None, env=None):
            captured["cmd"] = cmd
            captured["env"] = env

            class Result:
                returncode = 0

            return Result()

        prd = Path("dummy.md")
        ai_cfg = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "max_tokens": 8096,
            "profile": "sonnet",
        }
        with patch("heal.dev.subprocess.run", side_effect=fake_run):
            with patch("heal.dev.build_openhands_argv", return_value=["/usr/bin/openhands", "--override-with-envs", "-t", "task"]):
                with patch("llm_client._resolve_credentials", return_value=("anthropic", "sk-x", "")):
                    rc = _run_layer_dev(
                    project_id="project-a",
                    prd=prd,
                    layer="frontend",
                    repo_path=Path("."),
                    skill_path=None,
                    openhands="/usr/bin/openhands",
                    ai_cfg=ai_cfg,
                )
        self.assertEqual(rc, 0)
        self.assertIn("--override-with-envs", captured["cmd"])
        self.assertTrue(
            "-t" in captured["cmd"] or "run" in captured["cmd"],
            captured["cmd"],
        )
        self.assertEqual(captured["env"]["LLM_MODEL"], "claude-sonnet-4-5")

    def test_build_openhands_argv_new_cli(self):
        def fake_help(cmd, **kwargs):
            class Result:
                returncode = 2
                stdout = ""
                stderr = "invalid choice: 'run'"

            return Result()

        with patch("heal.dev.subprocess.run", side_effect=fake_help):
            argv = build_openhands_argv("/usr/bin/openhands", "do thing")
        self.assertEqual(argv[:2], ["/usr/bin/openhands", "--override-with-envs"])
        self.assertIn("-t", argv)


if __name__ == "__main__":
    unittest.main()
