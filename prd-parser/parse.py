"""PRD 解析：M1 默认规则解析；设置 USE_LLM_PARSE=1 时可走 Claude。"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Union

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from validator import validate
from schema import validate_test_cases
from rule_parse import parse_rulebased
from component_path_resolver import resolve_in_test_cases_data


def parse(project_id: str, prd_path: Union[str, Path]) -> Path:
    prd_path = Path(prd_path)
    print(f"[parse] 开始解析：{prd_path}")

    result = validate(prd_path)
    print(result.report(str(prd_path)))
    if not result.valid:
        sys.exit(2)

    sys.path.insert(0, str(ROOT))
    from config_loader import load_project_config
    from content_fingerprint import prd_content_hash, scan_merge_conflicts, source_git_sha

    prd_id_guess = prd_path.stem.split("_")[0]
    inter_path = ROOT / "tests" / "intermediate" / project_id / f"{prd_id_guess}_test-cases.json"
    scan_paths = [prd_path]
    if inter_path.exists():
        scan_paths.append(inter_path)
    scan_merge_conflicts(scan_paths, label="parse")

    project_config = load_project_config(project_id)

    if os.getenv("USE_LLM_PARSE") == "1":
        data = _parse_llm(prd_path, project_id, project_config)
    else:
        print("[parse] 使用规则解析（M1 默认）")
        data = parse_rulebased(prd_path, project_id)

    if data.get("component_test_cases"):
        resolve_in_test_cases_data(data, project_config)

    validated = validate_test_cases(data)
    data = validated.to_dict()
    data["prd_content_hash"] = prd_content_hash(prd_path)
    data["source_git_sha"] = source_git_sha(prd_path)

    intermediate_dir = ROOT / project_config.get(
        "intermediate_dir", f"tests/intermediate/{project_id}"
    ).lstrip("./")
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    output_path = intermediate_dir / f"{data['prd_id']}_test-cases.json"
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    e2e_n = len(data.get("e2e_test_cases") or [])
    comp_n = len(data.get("component_test_cases") or [])
    print(f"[parse] ✅ E2E {e2e_n} 条 · 组件 {comp_n} 条 → {output_path}")
    return output_path


def _parse_llm(prd_path: Path, project_id: str, project_config: dict) -> dict:
    import anthropic
    import yaml

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("USE_LLM_PARSE=1 但未设置 ANTHROPIC_API_KEY")

    global_path = ROOT / "config" / "global.yaml"
    global_cfg = yaml.safe_load(global_path.read_text(encoding="utf-8")) if global_path.exists() else {}
    model = global_cfg.get("ai", {}).get("model", "claude-sonnet-4-5")
    prompt_path = Path(__file__).parent / "prompts" / "parse_prd.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"缺少 prompt：{prompt_path}")
    prd_content = prd_path.read_text(encoding="utf-8")
    prompt = prompt_path.read_text(encoding="utf-8").replace("{prd_content}", prd_content)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=global_cfg.get("ai", {}).get("max_tokens", 8096),
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1:
        raise ValueError("LLM 返回无 JSON")
    data = json.loads(raw[start : end + 1])
    data["project"] = project_id
    from rule_parse import _renumber_and_gate

    return _renumber_and_gate(data)
