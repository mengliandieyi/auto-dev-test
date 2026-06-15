"""规则解析 PRD Markdown → test-cases.json（M1 默认，不依赖 LLM）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from section_utils import is_section_heading, matches_section_heading


def _parse_frontmatter(content: str) -> Tuple[dict, str]:
    meta: dict = {}
    body = content
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            for line in content[3:end].strip().splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
            body = content[end + 4 :].lstrip("\n")
    return meta, body


def _section(body: str, name: str) -> str:
    lines = body.splitlines()
    out: List[str] = []
    in_sec = False
    for line in lines:
        if matches_section_heading(line, name):
            in_sec = True
            continue
        if in_sec:
            if is_section_heading(line):
                break
            out.append(line)
    return "\n".join(out).strip()


def _acceptance_criteria(body: str) -> List[str]:
    sec = _section(body, "验收标准")
    items = []
    for line in sec.splitlines():
        m = re.match(r"^- \[[ x]\]\s+(.+)$", line.strip())
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_component_blocks(body: str) -> List[Dict[str, Any]]:
    sec = _section(body, "组件测试")
    if not sec:
        return []
    chunks = re.split(r"\n(?=\d+\.\s)", sec)
    cases: List[Dict[str, Any]] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        title_m = re.match(r"^\d+\.\s*(.+)", chunk)
        title = title_m.group(1).split("\n")[0].strip() if title_m else "组件用例"
        comp_m = re.search(r"^\s*component:\s*(\S+)\s*$", chunk, re.M)
        if not comp_m:
            continue
        path_m = re.search(r"^\s*component_path:\s*(\S+)\s*$", chunk, re.M)

        actions: List[Dict[str, Any]] = []
        for block in re.finditer(
            r"-\s*type:\s*(\w+)\s*\n\s*testid:\s*(\S+)(?:\s*\n\s*value:\s*(.+))?",
            chunk,
        ):
            act: Dict[str, Any] = {"type": block.group(1), "testid": block.group(2)}
            if block.group(3):
                act["value"] = block.group(3).strip()
            actions.append(act)

        assertions: List[Dict[str, Any]] = []
        for block in re.finditer(
            r"-\s*type:\s*(\w+)\s*\n\s*testid:\s*(\S+)(?:\s*\n\s*text:\s*(.+))?",
            chunk.split("assertions:")[-1] if "assertions:" in chunk else "",
        ):
            a: Dict[str, Any] = {"type": block.group(1), "testid": block.group(2)}
            if block.group(3):
                a["text"] = block.group(3).strip()
            assertions.append(a)

        mocks: List[Dict[str, Any]] = []
        if "mocks:" in chunk:
            mock_sec = chunk.split("mocks:")[-1]
            method_m = re.search(r"method:\s*(\w+)", mock_sec)
            path_api = re.search(r"^\s*path:\s*(\S+)", mock_sec, re.M)
            status_m = re.search(r"status:\s*(\d+)", mock_sec)
            if method_m and path_api:
                mocks.append(
                    {
                        "method": method_m.group(1).upper(),
                        "path": path_api.group(1),
                        "status": int(status_m.group(1)) if status_m else 200,
                        "body": {"message": "账号或密码错误"},
                    }
                )

        cases.append(
            {
                "title": title,
                "component": comp_m.group(1),
                "component_path": path_m.group(1) if path_m else "",
                "actions": actions,
                "assertions": assertions,
                "mocks": mocks,
            }
        )
    return cases


def _build_e2e_cases(criteria: List[str]) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    if not criteria:
        return cases

    cases.append(
        {
            "source_criterion": criteria[0],
            "title": "正向登录",
            "steps": [
                {"action": "navigate", "target": "/login"},
                {"action": "fill", "testid": "username-input", "value": "{{valid.username}}"},
                {"action": "fill", "testid": "password-input", "value": "{{valid.password}}"},
                {"action": "click", "testid": "login-btn"},
            ],
            "assertions": [
                {"type": "url", "expected": "/dashboard"},
                {"type": "text_visible", "testid": "user-name"},
            ],
        }
    )

    if len(criteria) > 1:
        cases.append(
            {
                "source_criterion": criteria[1],
                "title": "错误密码",
                "steps": [
                    {"action": "navigate", "target": "/login"},
                    {"action": "fill", "testid": "username-input", "value": "{{valid.username}}"},
                    {"action": "fill", "testid": "password-input", "value": "{{invalid.password}}"},
                    {"action": "click", "testid": "login-btn"},
                ],
                "assertions": [
                    {"type": "text_visible", "testid": "error-message", "text": "账号或密码错误"},
                ],
            }
        )
    return cases


def _renumber_and_gate(data: dict) -> dict:
    for i, tc in enumerate(data.get("e2e_test_cases") or [], 1):
        tc["id"] = f"ETC-{i:03d}"
        tc["m1_gate"] = i == 1
    for i, tc in enumerate(data.get("component_test_cases") or [], 1):
        tc["id"] = f"CTC-{i:03d}"
        tc["m1_gate"] = i == 1
        if not tc.get("source_criterion"):
            tc["source_criterion"] = tc.get("title", "")
    return data


def parse_rulebased(prd_path: Path, project_id: str) -> dict:
    content = prd_path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(content)
    criteria = _acceptance_criteria(body)
    feature_sec = _section(body, "功能名称")
    feature = feature_sec.splitlines()[0].strip() if feature_sec else meta.get("prd_id", "")

    comp_raw = _parse_component_blocks(body)
    component_cases: List[Dict[str, Any]] = []
    for raw in comp_raw:
        component_cases.append(
            {
                "source_criterion": raw.get("title", ""),
                "title": raw.get("title", ""),
                "component": raw["component"],
                "component_path": raw.get("component_path") or "",
                "actions": raw.get("actions") or [],
                "assertions": raw.get("assertions") or [],
                "mocks": raw.get("mocks") or [],
            }
        )

    data = {
        "prd_id": meta.get("prd_id", prd_path.stem.split("_")[0]),
        "prd_version": meta.get("version", "1.0.0"),
        "project": project_id,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "feature_name": feature,
        "e2e_test_cases": _build_e2e_cases(criteria),
        "component_test_cases": component_cases,
    }
    return _renumber_and_gate(data)
