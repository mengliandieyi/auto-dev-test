"""env_store 凭证读写单测。"""

import os
import tempfile
import unittest
from pathlib import Path


import env_store as es  # noqa: E402


class TestEnvStore(unittest.TestCase):
    def setUp(self):
        self._old_path = es.ENV_PATH
        self._old_loaded = es._ENV_LOADED
        es._ENV_LOADED = False

    def tearDown(self):
        es.ENV_PATH = self._old_path
        es._ENV_LOADED = self._old_loaded
        for key in (
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_BASE_URL",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "LLM_KEY_SONNET",
            "LLM_KEY_HAIKU",
        ):
            os.environ.pop(key, None)

    def test_profile_api_keys_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            es.ENV_PATH = Path(tmp) / ".env"
            es.write_profile_api_keys(
                {"sonnet": "sk-ant-sonnet-key", "haiku": "sk-ant-haiku-key"},
                providers={"sonnet": "anthropic", "haiku": "anthropic"},
            )
            self.assertEqual(es.read_profile_api_key("sonnet"), "sk-ant-sonnet-key")
            self.assertEqual(es.read_profile_api_key("haiku"), "sk-ant-haiku-key")
            text = es.ENV_PATH.read_text(encoding="utf-8")
            self.assertIn("LLM_KEY_SONNET=", text)
            self.assertIn("LLM_KEY_HAIKU=", text)

    def test_write_and_read_anthropic(self):
        with tempfile.TemporaryDirectory() as tmp:
            es.ENV_PATH = Path(tmp) / ".env"
            es.write_credentials(api_key="sk-ant-test-key-1234", base_url="https://proxy.example.com")
            info = es.read_credentials()
            self.assertTrue(info["anthropic"]["api_key_set"])
            self.assertEqual(info["anthropic"]["base_url"], "https://proxy.example.com")

    def test_write_and_read_openai(self):
        with tempfile.TemporaryDirectory() as tmp:
            es.ENV_PATH = Path(tmp) / ".env"
            es.write_credentials(openai_api_key="sk-openai-test-key-99", openai_base_url="https://api.openai.com/v1")
            info = es.read_credentials()
            self.assertTrue(info["openai"]["api_key_set"])
            self.assertEqual(info["openai"]["base_url"], "https://api.openai.com/v1")


if __name__ == "__main__":
    unittest.main()
