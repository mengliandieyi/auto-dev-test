"""M2 单元测试：内容指纹与 generate 判定。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


from content_fingerprint import prd_content_hash, scan_merge_conflicts
from spec_idempotency import decide_generation, is_version_upgrade


class TestContentFingerprint(unittest.TestCase):
    def test_hash_strips_front_matter_and_trailing_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.md"
            p.write_text(
                "---\nversion: 1.0.0\n---\n\n## 标题  \n\n正文\n",
                encoding="utf-8",
            )
            h1 = prd_content_hash(p)
            p.write_text(
                "---\nversion: 9.9.9\n---\n\n## 标题\n\n正文\n",
                encoding="utf-8",
            )
            h2 = prd_content_hash(p)
            self.assertEqual(h1, h2)

    def test_merge_conflict_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.md"
            p.write_text("<<<<<<< HEAD\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                scan_merge_conflicts([p])
            self.assertEqual(ctx.exception.code, 1)


class TestGenerationDecision(unittest.TestCase):
    def test_same_hash_same_version_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "spec.ts"
            spec.write_text(
                "/** PRD: PROJ-001 v1.0.0 (p) */\n/** Hash: abc */\n",
                encoding="utf-8",
            )
            decision = decide_generation(
                "p",
                "PROJ-001",
                "e2e",
                "1.0.0",
                "abc",
                spec,
            )
            self.assertEqual(decision.action, "skip")

    def test_content_drift_ci_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "spec.ts"
            spec.write_text(
                "/** PRD: PROJ-001 v1.0.0 (p) */\n/** Hash: old */\n",
                encoding="utf-8",
            )
            os.environ["CI"] = "true"
            try:
                with self.assertRaises(SystemExit) as ctx:
                    decide_generation(
                        "p",
                        "PROJ-001",
                        "e2e",
                        "1.0.0",
                        "new",
                        spec,
                    )
                self.assertEqual(ctx.exception.code, 1)
            finally:
                os.environ.pop("CI", None)

    def test_version_upgrade_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "spec.ts"
            spec.write_text(
                "/** PRD: PROJ-001 v1.0.0 (p) */\n/** Hash: old */\n",
                encoding="utf-8",
            )
            decision = decide_generation(
                "p",
                "PROJ-001",
                "e2e",
                "1.1.0",
                "new",
                spec,
            )
            self.assertEqual(decision.action, "archive")
            self.assertTrue(is_version_upgrade("1.0.0", "1.1.0"))


if __name__ == "__main__":
    unittest.main()
