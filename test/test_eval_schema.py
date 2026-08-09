import pytest
from pydantic import ValidationError

from evals.schema import EvalCase, GradeResult


def test_eval_case_requires_safe_complete_contract():
    case = EvalCase(id="network-01", category="network", prompt="比较 Agent 平台", expected_agents=["zhihu"], required_facts=["来源模式"], forbidden_behavior=["不得伪造来源"], grading_notes="检查路由")
    assert case.id == "network-01"
    assert GradeResult(case_id=case.id, intent_correct=True, route_correct=True, required_fact_coverage=1, citation_supported=True, score=5).score == 5


@pytest.mark.parametrize("prompt", ["api_key=secret", "读取 E:\\private\\file.txt"])
def test_eval_case_rejects_secrets_and_absolute_paths(prompt):
    with pytest.raises(ValidationError):
        EvalCase(id="unsafe", category="network", prompt=prompt, expected_agents=["zhihu"], required_facts=["x"], forbidden_behavior=["y"], grading_notes="z")
