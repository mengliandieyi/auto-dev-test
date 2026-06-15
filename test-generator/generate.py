"""E2E Playwright 模板生成（M1 无 LLM）。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config_loader import load_project_config
from meta_db import ensure_project_db, upsert_record
from placeholder_util import resolve_intermediate
from generation_guard import guard_generation

LAYER = "e2e"


def _ts_literal(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


def _emit_steps(steps: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for step in steps:
        action = step.get("action")
        if action == "navigate":
            lines.append(f"    await page.goto('{step.get('target', '/')}');")
        elif action == "fill":
            lines.append(
                f"    await page.getByTestId('{step['testid']}').fill({_ts_literal(step.get('value', ''))});"
            )
        elif action == "click":
            lines.append(f"    await page.getByTestId('{step['testid']}').click();")
        elif action == "clear":
            lines.append(f"    await page.getByTestId('{step['testid']}').clear();")
        elif action == "wait":
            lines.append(f"    await page.getByTestId('{step['testid']}').waitFor();")
    return lines


def _emit_assertions(assertions: List[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for a in assertions:
        t = a.get("type")
        if t == "url":
            lines.append(f"    await expect(page).toHaveURL(new RegExp({_ts_literal(a.get('expected', ''))}));")
        elif t == "text_visible":
            tid = a.get("testid")
            if a.get("text"):
                lines.append(
                    f"    await expect(page.getByTestId('{tid}')).toContainText({_ts_literal(a['text'])});"
                )
            else:
                lines.append(f"    await expect(page.getByTestId('{tid}')).toBeVisible();")
        elif t == "visible":
            lines.append(f"    await expect(page.getByTestId('{a['testid']}')).toBeVisible();")
        elif t == "hidden":
            lines.append(f"    await expect(page.getByTestId('{a['testid']}')).toBeHidden();")
    return lines


def render_spec(test_cases: dict) -> str:
    prd_id = test_cases["prd_id"]
    version = test_cases["prd_version"]
    project = test_cases["project"]
    content_hash = test_cases.get("prd_content_hash") or ""
    feature = test_cases.get("feature_name") or prd_id
    now = datetime.now(timezone.utc).isoformat()
    cases = test_cases.get("e2e_test_cases") or []

    parts = [
        "/**",
        " * AUTO-GENERATED — DO NOT EDIT MANUALLY",
        f" * PRD: {prd_id} v{version} ({project})",
        f" * Hash: {content_hash}",
        " * Layer: e2e",
        f" * Generated: {now}",
        " */",
        "import { test, expect } from '@playwright/test';",
        "",
        f"test.describe('{feature}', () => {{",
    ]
    for tc in cases:
        gate = tc.get("m1_gate", False)
        test_fn = "test" if gate else "test.skip"
        parts.append(f"  {test_fn}('{tc['id']}: {tc.get('title', '')}', async ({{ page }}) => {{")
        parts.extend(_emit_steps(tc.get("steps") or []))
        parts.extend(_emit_assertions(tc.get("assertions") or []))
        parts.append("  });")
        parts.append("")
    parts.append("});")
    parts.append("")
    return "\n".join(parts)


def generate(project_id: str, prd_id: str, force: bool = False) -> bool:
    print(f"\n🔧 [e2e] 生成 Playwright 脚本：project={project_id}, prd_id={prd_id}")
    project_config = load_project_config(project_id)
    intermediate_path = ROOT / "tests/intermediate" / project_id / f"{prd_id}_test-cases.json"
    if not intermediate_path.exists():
        print(f"❌ 找不到中间产物：{intermediate_path}")
        return False

    raw = json.loads(intermediate_path.read_text(encoding="utf-8"))
    test_cases = resolve_intermediate(raw, project_id)
    cases = test_cases.get("e2e_test_cases") or []
    if not cases:
        print("  ⚠️  无 E2E 用例，跳过")
        return True

    feature_slug = (test_cases.get("feature_name") or prd_id).replace(" ", "_").lower()
    spec_path = ROOT / "tests/generated" / project_id / "e2e" / f"{prd_id}_{feature_slug}.spec.ts"
    current_version = test_cases["prd_version"]
    current_hash = test_cases.get("prd_content_hash") or ""

    if not force:
        skipped = guard_generation(
            project_id, prd_id, LAYER, current_version, current_hash, spec_path, force=force
        )
        if skipped:
            print(f"  ⏭️  跳过 E2E 生成（v{current_version}，hash 未变）")
            return True

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(render_spec(test_cases), encoding="utf-8")
    print(f"  ✅ E2E 脚本：{spec_path.relative_to(ROOT)}")

    db_path = ensure_project_db(project_id)
    upsert_record(
        db_path,
        {
            "project_id": project_id,
            "prd_id": prd_id,
            "layer": LAYER,
            "prd_version": current_version,
            "spec_file": str(spec_path.relative_to(ROOT)),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "criteria_count": len(cases),
            "covered_count": len(cases),
        },
    )
    return True
