"""Heal 修复进展判定。"""

from __future__ import annotations

from typing import List


def healing_improved(before: List[str], after: List[str]) -> bool:
    """上一轮修复后，失败用例是否减少。"""
    if not before:
        return False
    b, a = set(before), set(after)
    if len(a) < len(b):
        return True
    if a < b:
        return True
    return False


def healing_stalled(before: List[str], after: List[str]) -> bool:
    """失败集合未缩小：相同、变多或横向替换。"""
    if not before:
        return False
    return not healing_improved(before, after)
