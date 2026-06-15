"""Skill 库与安全测试。"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from api.services import skills as skill_service


class TestSkillsService(unittest.TestCase):
    def test_list_includes_builtins(self):
        items = skill_service.list_skill_summaries()
        ids = {s["id"] for s in items}
        self.assertIn("clean-ui", ids)
        self.assertIn("go-api", ids)

    def test_crud_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            with mock.patch("skills_registry.SKILLS_DIR", skills_dir):
                content = """---
name: Test Skill
layer: frontend
description: demo
---

body
"""
                created = skill_service.create_skill("test-skill", content)
                self.assertEqual(created["id"], "test-skill")

                got = skill_service.get_skill("test-skill")
                self.assertIn("body", got["content"])

                updated = skill_service.update_skill("test-skill", content.replace("demo", "updated"))
                self.assertIn("updated", updated["description"])

                deleted = skill_service.remove_skill("test-skill")
                self.assertEqual(deleted["deleted"], "test-skill")

                with self.assertRaises(HTTPException) as ctx:
                    skill_service.get_skill("test-skill")
                self.assertEqual(ctx.exception.status_code, 404)

    def test_invalid_skill_id_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            skill_service.create_skill("BAD_ID", "# x")
        self.assertEqual(ctx.exception.status_code, 400)


class TestSkillImport(unittest.TestCase):
    def test_derive_skill_id(self):
        import skills_registry as sr

        self.assertEqual(sr.derive_skill_id("Clean-UI.md"), "clean-ui")
        self.assertEqual(sr.derive_skill_id("My_Skill.md"), "my-skill")

    def test_import_bytes_creates_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            with mock.patch("skills_registry.SKILLS_DIR", skills_dir):
                content = b"---\nname: Imported\nlayer: backend\n---\n\nbody\n"
                created = skill_service.import_skill_bytes("api-style.md", content)
                self.assertEqual(created["id"], "api-style")
                self.assertEqual(created["layer"], "backend")

    def test_import_path_from_design(self):
        design = Path(__file__).resolve().parent.parent / "design" / "SKILL.md"
        if not design.is_file():
            self.skipTest("design/SKILL.md missing")
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            with mock.patch("skills_registry.SKILLS_DIR", skills_dir):
                created = skill_service.import_skill_path("design/SKILL.md", "legacy-ui")
                self.assertEqual(created["id"], "legacy-ui")
                self.assertIn("Overview", created["content"])


class TestDevPipelineArgs(unittest.TestCase):
    def test_build_argv_dev_layer(self):
        from api.services.job_runner import build_argv

        argv = build_argv(
            "dev",
            "project-a",
            {
                "prd": "prds/project-a/foo.md",
                "layer": "frontend",
                "skill_frontend": "clean-ui",
            },
        )
        self.assertIn("dev", argv)
        self.assertIn("--layer", argv)
        self.assertEqual(argv[argv.index("--layer") + 1], "frontend")
        self.assertIn("--skill-frontend", argv)
        self.assertEqual(argv[argv.index("--skill-frontend") + 1], "clean-ui")


if __name__ == "__main__":
    unittest.main()
