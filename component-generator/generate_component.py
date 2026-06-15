"""Vitest + RTL 组件测试模板生成（M1 无 LLM）。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "prd-parser"))

from component_path_resolver import resolve_in_test_cases_data
from config_loader import load_project_config
from meta_db import ensure_project_db, upsert_record
from placeholder_util import resolve_intermediate
from generation_guard import guard_generation

LAYER = "component"


def _ts(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


def _component_import(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("src/"):
        p = p[4:]
    return p.replace(".tsx", "").replace(".jsx", "")


def _import_line(tc: Dict[str, Any]) -> str:
    name = tc["component"]
    path = (tc.get("component_path") or f"src/components/{name}.tsx").replace("\\", "/")
    mod = path.replace("src/", "").replace(".tsx", "").replace(".jsx", "")
    return f"import {name} from '@/{mod}';"


def _emit_mock(m: Dict[str, Any]) -> List[str]:
    body = json.dumps(m.get("body") or {}, ensure_ascii=False)
    method = (m.get("method") or "POST").lower()
    path = m.get("path", "/api/auth/login")
    status = int(m.get("status", 200))
    return [
        "    server.use(",
        f"      http.{method}({_ts(path)}, () =>",
        f"        HttpResponse.json({body}, {{ status: {status} }})",
        "      )",
        "    );",
    ]


def render_spec(test_cases: dict, project_config: dict) -> str:
    prd_id = test_cases["prd_id"]
    version = test_cases["prd_version"]
    project = test_cases["project"]
    content_hash = test_cases.get("prd_content_hash") or ""
    now = datetime.now(timezone.utc).isoformat()
    cases = test_cases.get("component_test_cases") or []

    parts = [
        "/**",
        " * AUTO-GENERATED — DO NOT EDIT MANUALLY",
        f" * PRD: {prd_id} v{version} ({project})",
        f" * Hash: {content_hash}",
        " * Layer: component",
        f" * Generated: {now}",
        " */",
        "import { describe, it, expect } from 'vitest';",
        "import { render, screen } from '@testing-library/react';",
        "import userEvent from '@testing-library/user-event';",
        "import { http, HttpResponse } from 'msw';",
        "import { server } from '../../../msw/server';",
    ]

    imports: List[str] = []
    seen = set()
    for tc in cases:
        line = _import_line(tc)
        if line not in seen:
            seen.add(line)
            imports.append(line)
    parts.extend(imports)

    parts.append("")
    parts.append(f"describe('{test_cases.get('feature_name') or prd_id}', () => {{")
    for tc in cases:
        comp = tc["component"]
        gate = tc.get("m1_gate", False)
        test_fn = "it" if gate else "it.skip"
        parts.append(f"  {test_fn}('{tc['id']}: {tc.get('title', '')}', async () => {{")
        parts.append("    const user = userEvent.setup();")
        if tc.get("mocks"):
            parts.extend(_emit_mock(tc["mocks"][0]))
        parts.append(f"    render(<{comp} />);")
        for act in tc.get("actions") or []:
            tid = act.get("testid")
            if act.get("type") == "fill":
                parts.append(f"    await user.clear(screen.getByTestId('{tid}'));")
                parts.append(
                    f"    await user.type(screen.getByTestId('{tid}'), {_ts(act.get('value', ''))});"
                )
            elif act.get("type") == "click":
                parts.append(f"    await user.click(screen.getByTestId('{act['testid']}'));")
        for a in tc.get("assertions") or []:
            if a.get("type") == "text_visible":
                parts.append(
                    f"    expect(await screen.findByTestId('{a['testid']}')).toHaveTextContent({_ts(a.get('text', ''))});"
                )
            elif a.get("type") == "disabled":
                parts.append(f"    expect(screen.getByTestId('{a['testid']}')).toBeDisabled();")
            elif a.get("type") == "enabled":
                parts.append(f"    expect(screen.getByTestId('{a['testid']}')).toBeEnabled();")
        parts.append("  });")
        parts.append("")
    parts.append("});")
    parts.append("")
    return "\n".join(parts)


def _basename(imp: str) -> str:
    return imp.split("/")[-1]


def generate_component(project_id: str, prd_id: str, force: bool = False) -> bool:
    print(f"\n🔧 [component] 生成 Vitest 脚本：project={project_id}, prd_id={prd_id}")
    project_config = load_project_config(project_id)
    if not (project_config.get("vitest") or {}).get("enabled", True):
        print("  ⚠️  vitest.enabled=false，跳过")
        return True

    intermediate_path = ROOT / "tests/intermediate" / project_id / f"{prd_id}_test-cases.json"
    if not intermediate_path.exists():
        print(f"❌ 找不到中间产物：{intermediate_path}")
        return False

    raw = json.loads(intermediate_path.read_text(encoding="utf-8"))
    test_cases = resolve_intermediate(raw, project_id)
    resolve_in_test_cases_data(test_cases, project_config)
    intermediate_path.write_text(json.dumps(test_cases, ensure_ascii=False, indent=2), encoding="utf-8")

    cases = test_cases.get("component_test_cases") or []
    if not cases:
        print("  ⚠️  无组件用例，跳过")
        return True

    feature_slug = (test_cases.get("feature_name") or prd_id).replace(" ", "_").lower()
    spec_path = ROOT / "tests/generated" / project_id / "component" / f"{prd_id}_{feature_slug}.test.tsx"
    current_version = test_cases["prd_version"]
    current_hash = test_cases.get("prd_content_hash") or ""

    if not force:
        skipped = guard_generation(
            project_id, prd_id, LAYER, current_version, current_hash, spec_path, force=force
        )
        if skipped:
            print(f"  ⏭️  跳过组件生成（v{current_version}，hash 未变）")
            return True

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(render_spec(test_cases, project_config), encoding="utf-8")
    print(f"  ✅ 组件测试：{spec_path.relative_to(ROOT)}")

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
