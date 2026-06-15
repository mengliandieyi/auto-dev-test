"""
PRD 解析器
读取 PRD Markdown → 调用 Claude API → 输出结构化 test-cases.json
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import anthropic
import yaml

# 项目根目录
ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(Path(__file__).parent))
from validator import validate
from schema import validate_test_cases


def _load_project_config(project_id: str) -> dict:
    config_path = ROOT / "config" / "projects" / f"{project_id}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"项目配置不存在：{config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_global_config() -> dict:
    global_path = ROOT / "config" / "global.yaml"
    if not global_path.exists():
        return {}
    with open(global_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_frontmatter(content: str) -> dict:
    """提取 YAML frontmatter"""
    meta: dict = {}
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_block = content[3:end].strip()
            for line in fm_block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
    return meta


def _load_prompt_template() -> str:
    prompt_path = Path(__file__).parent / "prompts" / "parse_prd.txt"
    return prompt_path.read_text(encoding="utf-8")


def _call_claude(prd_content: str, global_config: dict) -> str:
    """调用 Claude API，返回 JSON 字符串"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("未设置环境变量 ANTHROPIC_API_KEY")

    model = global_config.get("ai", {}).get("model", "claude-sonnet-4-5")
    max_tokens = global_config.get("ai", {}).get("max_tokens", 4096)

    prompt_template = _load_prompt_template()
    prompt = prompt_template.replace("{prd_content}", prd_content)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _extract_json(raw: str) -> dict:
    """从 Claude 返回内容中提取 JSON（兼容 markdown 代码块包裹）"""
    # 移除 ```json ... ``` 包裹
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    # 尝试找到第一个 { 到最后一个 }
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Claude 返回内容中未找到 JSON：\n{raw[:500]}")
    return json.loads(raw[start : end + 1])


def parse(project_id: str, prd_path: Union[str, Path]) -> Path:
    """
    解析 PRD 文件，输出 test-cases.json。
    返回输出文件路径。
    """
    prd_path = Path(prd_path)
    print(f"[parse] 开始解析：{prd_path}")

    # 1. 校验
    result = validate(prd_path)
    print(result.report(str(prd_path)))
    if not result.valid:
        sys.exit(1)

    # 2. 加载配置
    project_config = _load_project_config(project_id)
    global_config = _load_global_config()

    # 3. 读取 PRD
    prd_content = prd_path.read_text(encoding="utf-8")
    meta = _parse_frontmatter(prd_content)

    prd_id = meta.get("prd_id", prd_path.stem)
    prd_version = meta.get("version", "1.0.0")

    # 4. 调用 Claude
    print(f"[parse] 调用 Claude API 解析 PRD...")
    raw_response = _call_claude(prd_content, global_config)

    # 5. 提取 JSON
    data = _extract_json(raw_response)

    # 6. 注入追溯字段
    data["prd_id"] = prd_id
    data["prd_version"] = prd_version
    data["project"] = project_id
    data["generated_at"] = datetime.now(timezone.utc).isoformat()

    # 7. 组件路径自动检索（v1.1）
    if data.get("component_test_cases"):
        from component_path_resolver import resolve_in_test_cases_data

        try:
            resolve_in_test_cases_data(data, project_config)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[parse] ❌ 组件路径解析失败：{exc}")
            sys.exit(1)

    validated = validate_test_cases(data)
    data = validated.to_dict()

    # 8. 输出路径
    intermediate_dir = ROOT / project_config.get(
        "intermediate_dir", f"tests/intermediate/{project_id}"
    ).lstrip("./")
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    output_path = intermediate_dir / f"{prd_id}_test-cases.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    e2e_count = len(data.get("e2e_test_cases") or [])
    comp_count = len(data.get("component_test_cases") or [])
    print(f"[parse] ✅ E2E {e2e_count} 条 · 组件 {comp_count} 条 → {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PRD 解析器")
    parser.add_argument("--project", required=True, help="项目 ID")
    parser.add_argument("--prd", required=True, help="PRD 文件路径")
    args = parser.parse_args()

    parse(args.project, args.prd)
