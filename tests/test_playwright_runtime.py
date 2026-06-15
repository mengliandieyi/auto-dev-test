"""Playwright 运行时配置导出。"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright_runtime import export_playwright_runtime


class TestPlaywrightRuntime(unittest.TestCase):
    def test_export_project_a_web_server(self):
        out = export_playwright_runtime(ROOT)
        self.assertTrue(out.is_file())
        data = json.loads(out.read_text(encoding="utf-8"))
        project_a = next(p for p in data["projects"] if p["name"] == "project-a")
        self.assertIn("webServer", project_a)
        self.assertIn("npx serve", project_a["webServer"]["command"])
        self.assertEqual(project_a["baseURL"], "http://127.0.0.1:4173")


if __name__ == "__main__":
    unittest.main()
