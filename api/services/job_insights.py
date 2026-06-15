"""任务日志洞察：失败分类等。"""

from __future__ import annotations

import re
from typing import Optional

_PATTERNS = (
    (re.compile(r"CONTENT_DRIFT", re.I), "PRD 正文变更未 bump version（CI 阻断）"),
    (re.compile(r"MERGE_CONFLICT", re.I), "文件含 Git 合并冲突标记"),
    (re.compile(r"VERSION_DRIFT", re.I), "仅 version 变更，已跳过生成"),
    (re.compile(r"AMBIGUOUS_COMPONENT_PATH", re.I), "组件路径歧义，无法生成"),
    (re.compile(r"PRD 路径无效|Path traversal|outside configured prd_dir", re.I), "PRD 路径非法或跨项目"),
    (re.compile(r"Frontmatter project=.*不一致", re.I), "PRD frontmatter project 与当前项目不匹配"),
    (re.compile(r"ANTHROPIC_API_KEY|OPENAI_API_KEY|API Key", re.I), "缺少或无效的 LLM API Key"),
    (re.compile(r"\[cancelled\]", re.I), "用户取消"),
    (re.compile(r"OpenHands|openhands", re.I), "OpenHands 未安装或 dev 执行失败"),
    (re.compile(r"❌ PRD 校验失败|校验失败", re.I), "PRD 校验未通过"),
    (re.compile(r"Timeout|ETIMEDOUT|ECONNRESET", re.I), "网络超时或环境不可达"),
)


def classify_job_failure(log_tail: str, *, status: str = "", exit_code: Optional[int] = None) -> Optional[str]:
    if status == "CANCELLED":
        return "用户取消"
    if status != "FAILED" and exit_code in (None, 0):
        return None
    text = log_tail or ""
    for pattern, label in _PATTERNS:
        if pattern.search(text):
            return label
    if status == "FAILED" or (exit_code is not None and exit_code != 0):
        return "子进程异常退出，请查看完整日志"
    return None
