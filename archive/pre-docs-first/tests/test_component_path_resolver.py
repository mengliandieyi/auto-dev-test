"""component_path_resolver 单元测试"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "prd-parser"))

from component_path_resolver import (  # noqa: E402
    find_component_path,
    resolve_component_test_cases,
)

FIXTURE_FRONTEND = ROOT / "tests" / "fixtures" / "mock-frontend"


def test_find_direct_tsx():
    path = find_component_path("LoginForm", FIXTURE_FRONTEND)
    assert path == "src/components/LoginForm.tsx"


def test_find_nested_index():
    path = find_component_path("SignIn", FIXTURE_FRONTEND)
    assert path == "src/components/auth/SignIn/index.tsx"


def test_resolve_missing_path():
    cases = [{"id": "CTC-001", "component": "LoginForm", "component_path": ""}]
    cfg = {"repos": {"frontend": "tests/fixtures/mock-frontend"}}
    resolved, logs = resolve_component_test_cases(cases, cfg)
    assert resolved[0]["component_path"] == "src/components/LoginForm.tsx"
    assert any("自动解析" in line for line in logs)


def test_resolve_invalid_path_fallback():
    cases = [{
        "id": "CTC-001",
        "component": "LoginForm",
        "component_path": "src/components/Missing.tsx",
    }]
    cfg = {"repos": {"frontend": "tests/fixtures/mock-frontend"}}
    resolved, logs = resolve_component_test_cases(cases, cfg)
    assert resolved[0]["component_path"] == "src/components/LoginForm.tsx"
    assert any("已改用" in line for line in logs)


def test_resolve_not_found_raises():
    cases = [{"id": "CTC-001", "component": "NoSuchComponent", "component_path": ""}]
    cfg = {"repos": {"frontend": "tests/fixtures/mock-frontend"}}
    try:
        resolve_component_test_cases(cases, cfg)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError as exc:
        assert "NoSuchComponent" in str(exc)
