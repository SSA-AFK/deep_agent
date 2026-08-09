"""Comparable V1/V2 evaluation runner with an explicit live execution boundary."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from evals.schema import EvalCase, EvalRun

LiveExecutor = Callable[[EvalCase, str, float], Awaitable[EvalRun]]
EVALUATION_HARNESS_RULES = """
这是一个受控评测运行。只调用与用户问题直接相关的研究角色；每个角色最多调用一次。
获得足够证据或任一来源发生降级后，立即返回简洁结论，不要重复调度角色或工具。
保留来源和 live/demo 模式，不展示私有思维过程。
"""


def load_cases(path: Path) -> list[EvalCase]:
    return [EvalCase.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _finished_case_ids(output: Path) -> set[str]:
    if not output.exists():
        return set()
    return _recorded_case_ids(output)


def _recorded_case_ids(output: Path) -> set[str]:
    if not output.exists():
        return set()
    return {json.loads(line)["case_id"] for line in output.read_text(encoding="utf-8").splitlines()}


def _append_runs(output: Path, runs: list[EvalRun]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as file:
        for run in runs:
            file.write(run.model_dump_json() + "\n")


def run_cases(cases: list[EvalCase], prompt_version: str, output: Path) -> list[EvalRun]:
    """Create explicit incomplete dry-run records; never masquerade as model output."""
    existing = _recorded_case_ids(output)
    runs = [EvalRun(case_id=case.id, prompt_version=prompt_version, completed=False, duration_ms=0) for case in cases if case.id not in existing]
    _append_runs(output, runs)
    return runs


async def run_live_cases(
    cases: list[EvalCase],
    prompt_version: str,
    output: Path,
    timeout_seconds: float,
    executor: LiveExecutor | None = None,
) -> list[EvalRun]:
    """Run unfinished cases through one executor and append each durable result."""
    execute = executor or execute_live_case
    runs: list[EvalRun] = []
    for case in cases:
        if case.id in _finished_case_ids(output):
            continue
        started = time.perf_counter()
        try:
            run = await asyncio.wait_for(execute(case, prompt_version, timeout_seconds), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            run = EvalRun(
                case_id=case.id,
                prompt_version=prompt_version,
                completed=False,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_code="EVAL_TIMEOUT",
                error_message="The evaluation case exceeded its execution timeout.",
            )
        except Exception:
            run = EvalRun(
                case_id=case.id,
                prompt_version=prompt_version,
                completed=False,
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_code="EVAL_EXECUTION_FAILED",
                error_message="The evaluation case could not complete.",
            )
        _append_runs(output, [run])
        runs.append(run)
    return runs


async def execute_live_case(case: EvalCase, prompt_version: str, timeout_seconds: float) -> EvalRun:
    """Build the selected prompt variant lazily; model auth is required here only."""
    import time
    import yaml
    from deepagents import create_deep_agent
    from langgraph.checkpoint.memory import InMemorySaver

    from agent.llm import get_model
    from tools.db_tools import execute_sql_query, get_table_data, list_sql_tables
    from tools.markdown_tools import generate_markdown
    from tools.pdf_tools import convert_md_to_pdf
    from tools.ragflow_tools import create_ask_delete, get_assistant_list
    from tools.upload_file_read_tool import read_file_content
    from tools.zhihu_search_tool import internet_search

    prompt_path = Path(__file__).parent / "prompts" / f"{prompt_version}.yml"
    prompts = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    tools_by_role = {
        "zhihu": [internet_search],
        "db": [list_sql_tables, get_table_data, execute_sql_query],
        "ragflow": [get_assistant_list, create_ask_delete],
    }
    subagents = [
        {"name": role, "description": config["description"], "system_prompt": config["system_prompt"], "tools": tools_by_role[role]}
        for role, config in prompts["sub_agents"].items()
    ]
    agent = create_deep_agent(
        model=get_model(),
        system_prompt=prompts["main_agent"]["system_prompt"] + EVALUATION_HARNESS_RULES,
        tools=[generate_markdown, convert_md_to_pdf, read_file_content],
        checkpointer=InMemorySaver(),
        subagents=subagents,
    )
    started = time.perf_counter()
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": case.prompt}]},
        config={"recursion_limit": 16, "configurable": {"thread_id": f"eval-{prompt_version}-{case.id}"}},
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    messages = result.get("messages", [])
    answer = str(messages[-1].content) if messages else ""
    traces = []
    for message in messages:
        for call in getattr(message, "tool_calls", []) or []:
            if call.get("name") == "task":
                role = call.get("args", {}).get("subagent_type", "unknown")
                traces.append({"agent": role, "tool": "task", "duration_ms": 0})
    return EvalRun(case_id=case.id, prompt_version=prompt_version, completed=bool(answer), traces=traces, answer=answer, duration_ms=duration_ms)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-version", choices=["v1", "v2"], required=True)
    parser.add_argument("--case-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=180)
    args = parser.parse_args()
    cases = load_cases(args.case_file)
    if args.live:
        asyncio.run(run_live_cases(cases, args.prompt_version, args.output, args.timeout_seconds))
    else:
        run_cases(cases, args.prompt_version, args.output)
