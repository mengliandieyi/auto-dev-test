"""多模型 ai 配置解析单测。"""

import unittest


from ai_resolver import (  # noqa: E402
    ai_resolution_summary,
    merge_project_config,
    resolve_ai_for_task,
)


GLOBAL_AI = {
    "ai": {
        "provider": "anthropic",
        "default": "sonnet",
        "models": {
            "sonnet": {"model": "claude-sonnet-4-5", "max_tokens": 8096},
            "haiku": {"model": "claude-haiku-3-5", "max_tokens": 4096},
        },
        "tasks": {"parse": "haiku", "heal": "sonnet"},
    },
}


class TestAiResolver(unittest.TestCase):
    def test_task_uses_different_models(self):
        parse_cfg = resolve_ai_for_task(GLOBAL_AI, "parse")
        heal_cfg = resolve_ai_for_task(GLOBAL_AI, "heal")
        self.assertEqual(parse_cfg["model"], "claude-haiku-3-5")
        self.assertEqual(heal_cfg["model"], "claude-sonnet-4-5")

    def test_project_override_tasks(self):
        merged = merge_project_config(
            GLOBAL_AI,
            {"ai": {"tasks": {"parse": "sonnet"}}},
        )
        self.assertEqual(resolve_ai_for_task(merged, "parse")["profile"], "sonnet")
        self.assertEqual(resolve_ai_for_task(merged, "heal")["profile"], "sonnet")

    def test_legacy_single_model(self):
        legacy = {"ai": {"provider": "anthropic", "model": "claude-sonnet-4-5", "max_tokens": 2048}}
        cfg = resolve_ai_for_task(legacy, "parse")
        self.assertEqual(cfg["model"], "claude-sonnet-4-5")
        self.assertEqual(cfg["max_tokens"], 2048)

    def test_summary_lists_profiles(self):
        summary = ai_resolution_summary(GLOBAL_AI)
        self.assertEqual(len(summary["profiles"]), 2)
        self.assertIn("parse", summary["tasks"])
        self.assertIn("dev_frontend", summary["tasks"])
        self.assertIn("dev_backend", summary["tasks"])

    def test_openai_model_ref(self):
        cfg = {"ai": {"provider": "openai", "default": "gpt", "models": {"gpt": {"model": "gpt-4o", "provider": "openai"}}}}
        resolved = resolve_ai_for_task(cfg, "parse")
        self.assertEqual(resolved["provider"], "openai")
        self.assertEqual(resolved["model"], "gpt-4o")

    def test_gpt_model_id_fallback(self):
        ai = {
            "ai": {
                "provider": "anthropic",
                "default": "sonnet",
                "models": {"sonnet": {"model": "claude-sonnet-4-5"}},
                "tasks": {"parse": "gpt-4o-mini"},
            }
        }
        resolved = resolve_ai_for_task(ai, "parse")
        self.assertEqual(resolved["provider"], "openai")
        self.assertEqual(resolved["model"], "gpt-4o-mini")


if __name__ == "__main__":
    unittest.main()
