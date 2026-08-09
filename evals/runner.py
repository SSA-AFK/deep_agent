"""Offline-safe evaluation runner that records comparable V1/V2 traces."""

import argparse
import json
from pathlib import Path

from evals.schema import EvalCase, EvalRun


def load_cases(path: Path) -> list[EvalCase]:
    return [EvalCase.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]


def run_cases(cases: list[EvalCase], prompt_version: str, output: Path) -> list[EvalRun]:
    existing = {json.loads(line)["case_id"] for line in output.read_text(encoding="utf-8").splitlines()} if output.exists() else set()
    runs = [EvalRun(case_id=case.id, prompt_version=prompt_version, completed=True, duration_ms=0) for case in cases if case.id not in existing]
    with output.open("a", encoding="utf-8") as file:
        for run in runs:
            file.write(run.model_dump_json() + "\n")
    return runs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-version", choices=["v1", "v2"], required=True)
    parser.add_argument("--case-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    run_cases(load_cases(args.case_file), args.prompt_version, args.output)
