"""PRD 列表 API 回归测试。"""

import unittest

from api.services.projects import list_prds


class TestListPrds(unittest.TestCase):
    def test_list_project_a(self):
        items = list_prds("project-a")
        self.assertGreaterEqual(len(items), 1)
        self.assertIn("filename", items[0])
        self.assertIn("prd_id", items[0])


if __name__ == "__main__":
    unittest.main()
