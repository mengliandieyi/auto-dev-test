"""component_path_resolver 单元测试"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prd-parser"))

from component_path_resolver import find_component_path, resolve_in_test_cases_data  # noqa: E402

FIXTURE_FRONTEND = ROOT / "tests" / "fixtures" / "mock-frontend"
CFG = {"vitest": {"frontend_root": "tests/fixtures/mock-frontend"}}


class TestComponentPathResolver(unittest.TestCase):
    def test_find_direct_tsx(self):
        path = find_component_path("LoginForm", FIXTURE_FRONTEND)
        self.assertEqual(path, "src/components/LoginForm.tsx")

    def test_find_nested_index(self):
        path = find_component_path("SignIn", FIXTURE_FRONTEND)
        self.assertEqual(path, "src/components/auth/SignIn/index.tsx")

    def test_resolve_missing_path(self):
        data = {
            "component_test_cases": [
                {"id": "CTC-001", "component": "LoginForm", "component_path": ""},
            ],
        }
        out = resolve_in_test_cases_data(data, CFG)
        self.assertEqual(
            out["component_test_cases"][0]["component_path"],
            "src/components/LoginForm.tsx",
        )

    def test_resolve_invalid_path_fallback(self):
        data = {
            "component_test_cases": [{
                "id": "CTC-001",
                "component": "LoginForm",
                "component_path": "src/components/Missing.tsx",
            }],
        }
        out = resolve_in_test_cases_data(data, CFG)
        self.assertEqual(
            out["component_test_cases"][0]["component_path"],
            "src/components/LoginForm.tsx",
        )

    def test_resolve_not_found_raises(self):
        data = {
            "component_test_cases": [
                {"id": "CTC-001", "component": "NoSuchComponent", "component_path": ""},
            ],
        }
        with self.assertRaises(FileNotFoundError) as ctx:
            resolve_in_test_cases_data(data, CFG)
        self.assertIn("NoSuchComponent", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
