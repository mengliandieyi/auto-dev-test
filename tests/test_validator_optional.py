"""validator 章节匹配（含 `（可选）` 后缀）。"""

import tempfile
import unittest
from pathlib import Path


from validator import validate  # noqa: E402


class TestValidatorOptionalSections(unittest.TestCase):
    def _write_prd(self, body: str) -> Path:
        content = f"""---
prd_id: TEST-001
version: 1.0.0
project: project-a
---

{body}
"""
        tmp = Path(tempfile.mkdtemp()) / "test.md"
        tmp.write_text(content, encoding="utf-8")
        return tmp

    def test_optional_component_section_parses(self):
        prd = self._write_prd(
            """## 功能名称
登录

## 需求说明
- 作为用户，我希望登录，以便访问系统

## 页面交互
1. 打开登录页
2. 输入账号密码

## 组件测试（可选）
1. LoginForm
   - 输入用户名

## 验收标准
- [ ] 能登录
"""
        )
        result = validate(prd)
        self.assertTrue(result.valid, result.errors)

    def test_missing_required_section_fails(self):
        prd = self._write_prd(
            """## 功能名称
登录

## 需求说明
- 作为用户，我希望登录，以便访问系统

## 验收标准
- [ ] 能登录
"""
        )
        result = validate(prd)
        self.assertFalse(result.valid)
        self.assertTrue(any("页面交互" in e.message or "使用流程" in e.message for e in result.errors))


if __name__ == "__main__":
    unittest.main()
