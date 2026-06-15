"""
test-generator/generate.py — E2E Playwright 测试生成器
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import anthropic
import yaml

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from meta_db import archive_old_spec, ensure_project_db, get_existing_record, upsert_record
from spec_idempotency import check_generation_idempotency

LAYER = "e2e"


def load_project_config(project_id: str) -> dict:
    config_path = ROOT / "config" / "projects" / f"{project_id}.yaml"
    if not config_path.exists():
        print(f"❌ 找不到项目配置：{config_path}")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_global_config() -> dict:
    path = ROOT / "config" / "global.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _e2e_cases(data: dict) -> list:
    return data.get("e2e_test_cases") or []


def build_prompt(test_cases: dict, project_config: dict, base_url: str) -> str:
    payload = {**test_cases, "e2e_test_cases": _e2e_cases(test_cases)}
    tc_json = json.dumps(payload, ensure_ascii=False, indent=2)
    prd_id = test_cases["prd_id"]
    prd_version = test_cases["prd_version"]
    project_id = test_cases["project"]
    generated_at = datetime.now(timezone.utc).isoformat()
    criteria_count = len(_e2e_cases(test_cases))
    selector_strategy = project_config.get("playwright", {}).get(
        "selector_strategy", "data-testid"
    )

    return f"""你是一个 Playwright TypeScript 测试工程师。
根据以下测试用例 JSON，生成完整的 Playwright .spec.ts 文件。

## 要求

1. 使用 TypeScript，引入 @playwright/test
2. 元素定位：统一使用 page.getByTestId()（data-testid）
3. 每个 e2e test_case 对应一个 test()，标题包含用例 id（ETC-001 格式）
4. 文件头部注释：
/**
 * AUTO-GENERATED — DO NOT EDIT MANUALLY
 * PRD: {prd_id} v{prd_version} ({project_id})
 * Layer: e2e
 * Generated: {generated_at}
 * Criteria Coverage: {criteria_count}/{criteria_count}
 */
5. 使用 test.describe 分组；断言使用 expect()
6. base_url 默认：{base_url}（可用 process.env.BASE_URL 覆盖）
7. 只输出 TypeScript，不要 markdown 代码块

## 测试用例数据

{tc_json}
"""


def generate_spec(test_cases: dict, project_config: dict, output_path: Path, global_config: dict):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 缺少环境变量：ANTHROPIC_API_KEY")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    model = global_config.get("ai", {}).get("model", "claude-sonnet-4-5")
    max_tokens = global_config.get("ai", {}).get("max_tokens", 8096)
    base_url = project_config.get("base_url", "http://localhost:3000")

    prompt = build_prompt(test_cases, project_config, base_url)
    print(f"  🤖 调用 Claude API（{model}）生成 E2E 脚本...")
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    spec_content = message.content[0].text.strip()
    if spec_content.startswith("```"):
        lines = spec_content.split("\n")
        spec_content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(spec_content, encoding="utf-8")
    print(f"  ✅ E2E 脚本：{output_path.relative_to(ROOT)}")


def generate(project_id: str, prd_id: str) -> bool:
    print(f"\n🔧 [e2e] 生成 Playwright 脚本：project={project_id}, prd_id={prd_id}")

    project_config = load_project_config(project_id)
    global_config = load_global_config()

    intermediate_path = ROOT / "tests" / "intermediate" / project_id / f"{prd_id}_test-cases.json"
    if not intermediate_path.exists():
        print(f"❌ 找不到中间产物：{intermediate_path}")
        return False

    with open(intermediate_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    cases = _e2e_cases(test_cases)
    if not cases:
        print("  ⚠️  无 E2E 用例，跳过")
        return True

    current_version = test_cases["prd_version"]
    criteria_count = len(cases)
    feature_slug = (
        (test_cases.get("feature") or test_cases.get("feature_name") or prd_id)
        .replace(" ", "_").lower()
    )
    spec_filename = f"{prd_id}_{feature_slug}.spec.ts"
    spec_output_path = ROOT / "tests" / "generated" / project_id / "e2e" / spec_filename

    action, existing_ver, existing_path = check_generation_idempotency(
        project_id, prd_id, LAYER, current_version, spec_output_path
    )
    db_path = ensure_project_db(project_id)

    if action == "skip":
        print(f"  ⏭️  版本未变（v{current_version}），跳过 E2E 生成（spec 文件头）")
        _sync_meta_record(
            db_path, project_id, prd_id, LAYER, current_version,
            spec_output_path if spec_output_path.exists() else existing_path,
            criteria_count,
        )
        return True

    if action == "archive" and existing_path and existing_ver:
        print(f"  📋 E2E 版本升级：v{existing_ver} → v{current_version}")
        archive_old_spec(
            db_path,
            {
                "project_id": project_id,
                "prd_id": prd_id,
                "layer": LAYER,
                "prd_version": existing_ver,
            },
            existing_path,
            ".spec.ts",
        )
    else:
        existing = get_existing_record(db_path, project_id, prd_id, LAYER)
        if existing and existing["prd_version"] == current_version:
            print(f"  ⏭️  版本未变（v{current_version}），跳过 E2E 生成（meta.db）")
            return True
        if existing and existing["prd_version"] != current_version:
            print(f"  📋 E2E 版本升级：v{existing['prd_version']} → v{current_version}")
            archive_old_spec(db_path, existing, ROOT / existing["spec_file"], ".spec.ts")

    generate_spec(test_cases, project_config, spec_output_path, global_config)
    now = datetime.now(timezone.utc).isoformat()
    upsert_record(db_path, {
        "project_id": project_id,
        "prd_id": prd_id,
        "layer": LAYER,
        "prd_version": current_version,
        "spec_file": str(spec_output_path.relative_to(ROOT)),
        "generated_at": now,
        "criteria_count": criteria_count,
        "covered_count": criteria_count,
    })
    return True


def _sync_meta_record(
    db_path: Path,
    project_id: str,
    prd_id: str,
    layer: str,
    version: str,
    spec_path: Optional[Path],
    criteria_count: int,
) -> None:
    if not spec_path or not spec_path.exists():
        return
    upsert_record(db_path, {
        "project_id": project_id,
        "prd_id": prd_id,
        "layer": layer,
        "prd_version": version,
        "spec_file": str(spec_path.relative_to(ROOT)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "criteria_count": criteria_count,
        "covered_count": criteria_count,
    })


def main():
    parser = argparse.ArgumentParser(description="生成 Playwright E2E 测试")
    parser.add_argument("--project", required=True)
    parser.add_argument("--prd-id", required=True, dest="prd_id")
    args = parser.parse_args()
    sys.exit(0 if generate(args.project, args.prd_id) else 1)


if __name__ == "__main__":
    main()
