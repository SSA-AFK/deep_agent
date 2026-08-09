from pathlib import Path

import yaml

import asyncio

from evals.runner import run_cases, run_live_cases
from evals.schema import EvalRun
from evals.schema import EvalCase


def test_runner_resumes_without_duplicate_cases(tmp_path):
    cases = [EvalCase(id="n-1", category="network", prompt="x", expected_agents=["zhihu"], required_facts=["x"], forbidden_behavior=["y"], grading_notes="z")]
    output = tmp_path / "runs.jsonl"
    assert len(run_cases(cases, "v2", output)) == 1
    assert run_cases(cases, "v2", output) == []


def test_live_runner_uses_injected_executor_and_resumes(tmp_path):
    cases = [EvalCase(id="n-2", category="network", prompt="x", expected_agents=["zhihu"], required_facts=["x"], forbidden_behavior=["y"], grading_notes="z")]
    output = tmp_path / "live.jsonl"
    calls = []

    async def execute(case, version, timeout):
        calls.append((case.id, version, timeout))
        return EvalRun(case_id=case.id, prompt_version=version, completed=True, answer="x https://example.com", duration_ms=1)

    first = asyncio.run(run_live_cases(cases, "v1", output, 10, execute))
    second = asyncio.run(run_live_cases(cases, "v1", output, 10, execute))
    assert len(first) == 1
    assert second == []
    assert calls == [("n-2", "v1", 10)]


def test_versioned_prompt_snapshots_match_product_variants():
    root = Path(__file__).parents[1]
    v1 = yaml.safe_load((root / "evals/prompts/v1.yml").read_text(encoding="utf-8"))
    v2 = yaml.safe_load((root / "evals/prompts/v2.yml").read_text(encoding="utf-8"))
    current = yaml.safe_load((root / "prompt/prompts.yml").read_text(encoding="utf-8"))
    assert v2 == current
    assert "空调公司" in v1["main_agent"]["system_prompt"]
    assert "AI Agent 平台选型" in v2["main_agent"]["system_prompt"]
