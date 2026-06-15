"""Heal analyze（TECH §8.2，LLM 可选）。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent


def analyze_failure(
    project_id: str,
    prd_id: str,
    config: dict,
    failures: List[str],
    report_text: str,
) -> Tuple[Dict[str, Any], float]:
    """返回 (diagnosis, token_cost)。"""
    from env_store import ensure_env_loaded
    from llm_client import any_llm_configured

    ensure_env_loaded()
    if any_llm_configured():
        return _analyze_llm(project_id, prd_id, failures, report_text, config)
    return _analyze_rules(failures, report_text), 0.0


def _analyze_rules(failures: List[str], report_text: str) -> Dict[str, Any]:
    text = report_text.lower()
    if "prd_drift" in text or "需求" in report_text and "不一致" in report_text:
        return {
            "category": "prd_drift",
            "summary": "需求与实现可能不一致（规则判定）",
            "failures": failures,
        }
    if any(k in text for k in ("getbytestid", "locator", "selector", "timeout")):
        return {
            "category": "test_script",
            "summary": "测试脚本定位或断言问题，建议重生成 spec",
            "failures": failures,
            "fix_target": "test_script",
        }
    return {
        "category": "test_script",
        "summary": "默认按测试脚本修复",
        "failures": failures,
        "fix_target": "test_script",
    }


def _analyze_llm(
    project_id: str,
    prd_id: str,
    failures: List[str],
    report_text: str,
    config: dict,
) -> Tuple[Dict[str, Any], float]:
    from bootstrap import setup_repo_paths

    setup_repo_paths()
    from ai_resolver import resolve_ai_for_task
    from llm_client import llm_complete

    ai_cfg = resolve_ai_for_task(config, "heal")
    model = ai_cfg["model"]
    prompt = f"""分析测试失败并返回 JSON（仅 JSON）：
project={project_id}, prd_id={prd_id}
failures={json.dumps(failures, ensure_ascii=False)}
report excerpt:
{report_text[:6000]}

字段：category (test_script|business_code|prd_drift|config_env), summary, fix_target, prd_drift (bool)
"""
    raw, tokens = llm_complete(ai_cfg, prompt, max_tokens=min(ai_cfg["max_tokens"], 4096))
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start : end + 1]) if start >= 0 else _analyze_rules(failures, report_text)
    return data, tokens


def is_prd_drift(diagnosis: Dict[str, Any]) -> bool:
    cat = (diagnosis.get("category") or "").lower()
    return cat == "prd_drift" or diagnosis.get("prd_drift") is True
