"""PRD Markdown 章节标题匹配（支持 `（可选）` 后缀）。"""

from __future__ import annotations

import re

OPTIONAL_SUFFIX = r"(?:\s*（可选）)?"


def section_heading_pattern(name: str) -> re.Pattern[str]:
    return re.compile(rf"^##\s+{re.escape(name)}{OPTIONAL_SUFFIX}\s*$")


def matches_section_heading(line: str, name: str) -> bool:
    return bool(section_heading_pattern(name).match(line.strip()))


def is_section_heading(line: str) -> bool:
    return bool(re.match(r"^##\s+", line.strip()))
