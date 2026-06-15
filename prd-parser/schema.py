"""test-cases.json Pydantic 校验（兼容 Python 3.9+）"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class Step(BaseModel):
    action: str
    testid: Optional[str] = None
    target: Optional[str] = None
    value: Optional[str] = None
    type: Optional[str] = None


class Assertion(BaseModel):
    type: str
    expected: Optional[str] = None
    testid: Optional[str] = None
    text: Optional[str] = None


class E2ETestCase(BaseModel):
    id: str
    source_criterion: str
    title: str
    m1_gate: bool = False
    steps: List[Step] = Field(default_factory=list)
    assertions: List[Assertion] = Field(default_factory=list)
    type: Optional[str] = None


class ComponentAction(BaseModel):
    type: str
    testid: Optional[str] = None
    value: Optional[str] = None


class ComponentMock(BaseModel):
    method: str
    path: str
    status: int = 200
    body: Dict[str, Any] = Field(default_factory=dict)


class ComponentTestCase(BaseModel):
    id: str
    source_criterion: str
    title: str
    m1_gate: bool = False
    component: str
    component_path: str
    props: Dict[str, Any] = Field(default_factory=dict)
    actions: List[ComponentAction] = Field(default_factory=list)
    assertions: List[Assertion] = Field(default_factory=list)
    mocks: List[ComponentMock] = Field(default_factory=list)


class TestCasesOutput(BaseModel):
    prd_id: str
    prd_version: str
    project: str
    parsed_at: Optional[str] = None
    generated_at: Optional[str] = None
    prd_content_hash: Optional[str] = None
    source_git_sha: Optional[str] = None
    feature_name: Optional[str] = None
    feature: Optional[str] = None
    test_data: Dict[str, Any] = Field(default_factory=dict)
    e2e_test_cases: List[E2ETestCase] = Field(default_factory=list)
    component_test_cases: List[ComponentTestCase] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def absorb_legacy_test_cases(cls, data: Any) -> Any:
        """读取旧 JSON 时把 test_cases 并入 e2e_test_cases，输出不再写 test_cases。"""
        if isinstance(data, dict):
            legacy = data.get("test_cases")
            if legacy and not data.get("e2e_test_cases"):
                data["e2e_test_cases"] = legacy
            data.pop("test_cases", None)
        return data

    def to_dict(self) -> dict:
        d = self.model_dump()
        d["e2e_test_cases"] = [c.model_dump() for c in self.e2e_test_cases]
        d["component_test_cases"] = [c.model_dump() for c in self.component_test_cases]
        return d


def validate_test_cases(data: dict) -> TestCasesOutput:
    return TestCasesOutput.model_validate(data)
