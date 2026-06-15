"""Heal analyze（TECH §8.2，LLM 可选）。"""

from __future__ import annotations

import json
import os
import re
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
    if os.getenv("ANTHROPIC_API_KEY"):
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
    import anthropic
    import yaml

    global_path = ROOT / "config" / "global.yaml"
    global_cfg = yaml.safe_load(global_path.read_text(encoding="utf-8")) if global_path.exists() else {}
    model = global_cfg.get("ai", {}).get("model", "claude-sonnet-4-5")
    prompt = f"""分析测试失败并返回 JSON（仅 JSON）：
project={project_id}, prd_id={prd_id}
failures={json.dumps(failures, ensure_ascii=False)}
report excerpt:
{report_text[:6000]}

字段：category (test_script|business_code|prd_drift|config_env), summary, fix_target, prd_drift (bool)
"""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start : end + 1]) if start >= 0 else _analyze_rules(failures, report_text)
    usage = getattr(msg, "usage", None)
    tokens = float((usage.input_tokens if usage else 0) + (usage.output_tokens if usage else 0))
    return data, tokens


def is_prd_drift(diagnosis: Dict[str, Any]) -> bool:
    cat = (diagnosis.get("category") or "").lower()
    return cat == "prd_drift" or diagnosis.get("prd_drift") is True
