"""
PRD 规范校验器
校验 Markdown PRD 文件是否符合框架要求，不通过则返回详细错误报告。
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from section_utils import is_section_heading, matches_section_heading

# 必填章节
# 注意：「页面交互」与「使用流程」二选一均可通过校验
# 业务 PRD 用「页面交互」（需包含 data-testid 标注）
# 框架类/CLI 工具 PRD 用「使用流程」
REQUIRED_SECTIONS = ["功能名称", "需求说明", "验收标准"]
INTERACTION_SECTIONS = ["页面交互", "使用流程"]  # 至少有其中一个

# 验收标准格式：- [ ] 或 - [x] 开头
AC_FORMAT = re.compile(r"^- \[[ x]\] .+", re.MULTILINE)

# 需求说明格式：必须包含 "作为"、"希望"、"以便"
REQUIREMENT_LINE_FORMAT = re.compile(r"作为.+希望.+以便")

# Frontmatter 必填字段
REQUIRED_FRONTMATTER = ["prd_id", "version", "project"]


@dataclass
class ValidationError:
    line: Optional[int]
    message: str


@dataclass
class ValidationResult:
    valid: bool
    errors: list = field(default_factory=list)

    def add_error(self, message: str, line: Optional[int] = None):
        self.errors.append(ValidationError(line=line, message=message))
        self.valid = False

    def report(self, prd_path: str) -> str:
        if self.valid:
            return f"✅ PRD 校验通过：{prd_path}"
        lines = [f"❌ PRD 校验失败：{prd_path}"]
        for err in self.errors:
            prefix = f"  - 第 {err.line} 行：" if err.line else "  - "
            lines.append(f"{prefix}{err.message}")
        return "\n".join(lines)


def _parse_frontmatter(content: str) -> tuple[dict, str, int]:
    """解析 YAML frontmatter，返回 (meta_dict, body, body_start_line)"""
    meta: dict = {}
    body = content
    body_start_line = 1

    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_block = content[3:end].strip()
            body = content[end + 4:].lstrip("\n")
            body_start_line = content[:end + 4].count("\n") + 2
            for raw_line in fm_block.splitlines():
                if ":" in raw_line:
                    k, _, v = raw_line.partition(":")
                    meta[k.strip()] = v.strip()
    return meta, body, body_start_line


def _find_section_line(lines: list, section_name: str) -> Optional[int]:
    """找到章节标题所在行号（1-based）；支持 `## 标题（可选）`。"""
    for i, line in enumerate(lines, 1):
        if matches_section_heading(line, section_name):
            return i
    return None


def _extract_section_body(lines: list, section_name: str) -> str:
    """提取章节内容（到下一个 ## 为止）。"""
    in_section = False
    body_lines = []
    for line in lines:
        if matches_section_heading(line, section_name):
            in_section = True
            continue
        if in_section:
            if is_section_heading(line):
                break
            body_lines.append(line)
    return "\n".join(body_lines)


def validate(prd_path) -> ValidationResult:
    """校验 PRD 文件，返回 ValidationResult"""
    path = Path(prd_path)
    result = ValidationResult(valid=True)

    if not path.exists():
        result.add_error(f"文件不存在：{prd_path}")
        return result

    content = path.read_text(encoding="utf-8")
    meta, body, body_offset = _parse_frontmatter(content)
    lines = body.splitlines()
    all_lines = content.splitlines()

    # 1. Frontmatter 必填字段
    for field_name in REQUIRED_FRONTMATTER:
        if field_name not in meta or not meta[field_name]:
            result.add_error(f"Frontmatter 缺少必填字段：{field_name}")

    # 2. 必填章节存在性
    for section in REQUIRED_SECTIONS:
        if _find_section_line(lines, section) is None:
            result.add_error(f"缺少必填章节：[{section}]")

    # 2b. 「页面交互」或「使用流程」至少有一个
    found_interaction = any(
        _find_section_line(lines, s) is not None for s in INTERACTION_SECTIONS
    )
    if not found_interaction:
        result.add_error("缺少必填章节：[页面交互] 或 [使用流程]（二选一）")

    # 3. 需求说明格式
    req_body = _extract_section_body(lines, "需求说明")
    req_lines = [(i + body_offset, l) for i, l in enumerate(lines, 1)
                 if l.strip().startswith("- 作为") or l.strip().startswith("- 作為")]
    for lineno, req_line in req_lines:
        if not REQUIREMENT_LINE_FORMAT.search(req_line):
            result.add_error('需求说明格式不符（需包含"作为/希望/以便"）',
                             line=lineno)
    if not req_lines and "需求说明" in REQUIRED_SECTIONS:
        req_sec_line = _find_section_line(lines, "需求说明")
        if req_sec_line:
            result.add_error("需求说明章节为空，至少需要一条",
                             line=req_sec_line + body_offset)

    # 4. 验收标准格式 & 数量
    ac_body = _extract_section_body(lines, "验收标准")
    ac_matches = AC_FORMAT.findall(ac_body)
    if not ac_matches and "验收标准" in REQUIRED_SECTIONS:
        ac_sec_line = _find_section_line(lines, "验收标准")
        if ac_sec_line:
            result.add_error("验收标准章节为空，至少需要一条（格式：- [ ] 描述）",
                             line=ac_sec_line + body_offset)

    # 5. 页面交互 / 使用流程步骤数量（检查存在的那个章节）
    active_interaction = next(
        (s for s in INTERACTION_SECTIONS if _find_section_line(lines, s) is not None),
        None
    )
    if active_interaction:
        interaction_body = _extract_section_body(lines, active_interaction)
        interaction_steps = [l for l in interaction_body.splitlines()
                             if re.match(r"^\d+\.", l.strip())]
        if len(interaction_steps) < 2:
            interaction_sec_line = _find_section_line(lines, active_interaction)
            if interaction_sec_line:
                result.add_error(
                    f"[{active_interaction}] 步骤少于 2 步（当前 {len(interaction_steps)} 步），无法生成有效测试",
                    line=interaction_sec_line + body_offset,
                )

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python validator.py <prd_file.md>")
        sys.exit(1)

    prd_file = sys.argv[1]
    res = validate(prd_file)
    print(res.report(prd_file))
    sys.exit(0 if res.valid else 1)
