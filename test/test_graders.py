from evals.graders import grade
from evals.schema import AgentTrace, EvalCase, EvalRun


def test_grader_scores_route_and_fact_coverage():
    case = EvalCase(id="x", category="network", prompt="x", expected_agents=["zhihu"], required_facts=["source"], forbidden_behavior=["fabricate"], grading_notes="x")
    run = EvalRun(case_id="x", prompt_version="v2", completed=True, traces=[AgentTrace(agent="zhihu", duration_ms=1)], answer="source https://example.invalid", duration_ms=1)

    assert grade(case, run).score == 5
