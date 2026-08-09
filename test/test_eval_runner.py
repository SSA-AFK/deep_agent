from evals.runner import run_cases
from evals.schema import EvalCase


def test_runner_resumes_without_duplicate_cases(tmp_path):
    cases = [EvalCase(id="n-1", category="network", prompt="x", expected_agents=["zhihu"], required_facts=["x"], forbidden_behavior=["y"], grading_notes="z")]
    output = tmp_path / "runs.jsonl"
    assert len(run_cases(cases, "v2", output)) == 1
    assert run_cases(cases, "v2", output) == []
