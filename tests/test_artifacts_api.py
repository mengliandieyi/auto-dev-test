"""产物读取与安全测试"""

import unittest

from fastapi import HTTPException

from api.services import artifacts as artifact_service
from api.services.path_safety import validate_project_id


class TestArtifactsService(unittest.TestCase):
    def test_read_test_cases_project_a(self):
        res = artifact_service.read_test_cases("project-a", "PROJ-001")
        self.assertEqual(res["data"]["prd_id"], "PROJ-001")
        self.assertGreater(len(res["data"].get("e2e_test_cases", [])), 0)

    def test_list_generated_files(self):
        files = artifact_service.list_generated_files("project-a", "PROJ-001")
        self.assertGreaterEqual(len(files), 1)

    def test_read_generated_file(self):
        files = artifact_service.list_generated_files("project-a", "PROJ-001")
        content = artifact_service.read_generated_file("project-a", files[0]["path"])
        self.assertIn("test", content["content"].lower())

    def test_path_traversal_blocked(self):
        with self.assertRaises(HTTPException):
            artifact_service.read_generated_file(
                "project-a",
                "tests/generated/project-a/e2e/../../secrets",
            )

    def test_invalid_prd_id(self):
        with self.assertRaises(HTTPException):
            artifact_service.read_test_cases("project-a", "../evil")

    def test_list_changes_empty_ok(self):
        res = artifact_service.list_changes("project-a", "PROJ-001")
        self.assertIn("diffs", res)
        self.assertIn("heal_patches", res)


if __name__ == "__main__":
    unittest.main()
