"""
component-generator/generate_component.py — Vitest + RTL 组件测试生成器
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

LAYER = "component"


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


def build_prompt(test_cases: dict, project_config: dict) -> str:
    template_path = Path(__file__).parent / "prompts" / "gen_component_test.txt"
    template = template_path.read_text(encoding="utf-8")
    cases = test_cases.get("component_test_cases") or []
    alias = project_config.get("vitest", {}).get("frontend_src_alias", "@/")
    payload = json.dumps(cases, ensure_ascii=False, indent=2)
    return (
        template.replace("{component_test_cases_json}", payload)
        .replace("{prd_id}", test_cases["prd_id"])
        .replace("{prd_version}", test_cases["prd_version"])
        .replace("{project_id}", test_cases["project"])
        .replace("{generated_at}", datetime.now(timezone.utc).isoformat())
        .replace("{criteria_count}", str(len(cases)))
        + f"\n\n组件 import 别名：{alias}（如 @/components/LoginForm）\n"
    )


def generate_spec(test_cases: dict, project_config: dict, output_path: Path, global_config: dict):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 缺少环境变量：ANTHROPIC_API_KEY")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    model = global_config.get("ai", {}).get("model", "claude-sonnet-4-5")
    max_tokens = global_config.get("ai", {}).get("max_tokens", 8096)
    prompt = build_prompt(test_cases, project_config)

    print(f"  🤖 调用 Claude API（{model}）生成组件测试...")
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    content = message.content[0].text.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"  ✅ 组件测试：{output_path.relative_to(ROOT)}")


def generate_component(project_id: str, prd_id: str) -> bool:
    print(f"\n🔧 [component] 生成 Vitest 脚本：project={project_id}, prd_id={prd_id}")

    vitest_cfg = load_project_config(project_id).get("vitest", {})
    if not vitest_cfg.get("enabled", True):
        print("  ⚠️  vitest.enabled=false，跳过")
        return True

    project_config = load_project_config(project_id)
    global_config = load_global_config()

    intermediate_path = ROOT / "tests" / "intermediate" / project_id / f"{prd_id}_test-cases.json"
    if not intermediate_path.exists():
        print(f"❌ 找不到中间产物：{intermediate_path}")
        return False

    with open(intermediate_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    cases = test_cases.get("component_test_cases") or []
    if not cases:
        print("  ⚠️  无组件测试用例（PRD 未含「组件测试」章节），跳过")
        return True

    # v1.1：生成前补全缺失的 component_path
    sys.path.insert(0, str(ROOT / "prd-parser"))
    from component_path_resolver import resolve_in_test_cases_data

    try:
        resolve_in_test_cases_data(test_cases, project_config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"  ❌ 组件路径解析失败：{exc}")
        return False

    cases = test_cases.get("component_test_cases") or []
    current_version = test_cases["prd_version"]
    criteria_count = len(cases)
    feature_slug = (
        (test_cases.get("feature") or test_cases.get("feature_name") or prd_id)
        .replace(" ", "_").lower()
    )
    out_name = f"{prd_id}_{feature_slug}.test.tsx"
    spec_output_path = ROOT / "tests" / "generated" / project_id / "component" / out_name

    action, existing_ver, existing_path = check_generation_idempotency(
        project_id, prd_id, LAYER, current_version, spec_output_path
    )
    db_path = ensure_project_db(project_id)

    if action == "skip":
        print(f"  ⏭️  版本未变（v{current_version}），跳过组件生成（spec 文件头）")
        _sync_meta_record(
            db_path, project_id, prd_id, LAYER, current_version,
            spec_output_path if spec_output_path.exists() else existing_path,
            criteria_count,
        )
        return True

    if action == "archive" and existing_path and existing_ver:
        print(f"  📋 组件版本升级：v{existing_ver} → v{current_version}")
        archive_old_spec(
            db_path,
            {
                "project_id": project_id,
                "prd_id": prd_id,
                "layer": LAYER,
                "prd_version": existing_ver,
            },
            existing_path,
            ".test.tsx",
        )
    else:
        existing = get_existing_record(db_path, project_id, prd_id, LAYER)
        if existing and existing["prd_version"] == current_version:
            print(f"  ⏭️  版本未变（v{current_version}），跳过组件生成（meta.db）")
            return True
        if existing and existing["prd_version"] != current_version:
            print(f"  📋 组件版本升级：v{existing['prd_version']} → v{current_version}")
            archive_old_spec(db_path, existing, ROOT / existing["spec_file"], ".test.tsx")

    generate_spec(test_cases, project_config, spec_output_path, global_config)
    # 回写补全后的 component_path 到 intermediate
    with open(intermediate_path, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=2)
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
    parser = argparse.ArgumentParser(description="生成 Vitest 组件测试")
    parser.add_argument("--project", required=True)
    parser.add_argument("--prd-id", required=True, dest="prd_id")
    args = parser.parse_args()
    sys.exit(0 if generate_component(args.project, args.prd_id) else 1)


if __name__ == "__main__":
    main()
