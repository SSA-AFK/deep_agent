import json
from collections import Counter
from pathlib import Path

from evals.schema import EvalCase


def test_dataset_has_24_unique_cases_without_knowledge_base_routing():
    cases = [EvalCase.model_validate(json.loads(line)) for path in (Path("evals/cases")).glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(cases) == len({case.id for case in cases}) == 24
    assert Counter(case.category for case in cases) == {"network": 6, "database": 6, "multi_agent": 8, "ambiguous_error": 4}
    assert all("ragflow" not in case.expected_agents for case in cases)
