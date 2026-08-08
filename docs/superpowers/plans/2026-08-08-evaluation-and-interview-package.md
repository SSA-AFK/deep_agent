# Agent Evaluation and Interview Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce reproducible V1/V2 Agent evaluation results, product analytics evidence, polished design artifacts, and a five-minute interview narrative.

**Architecture:** Store versioned evaluation cases and run records as JSONL, execute both prompt variants through the same runner, combine deterministic checks with blinded human rubrics, and generate Markdown/HTML reports from measured data. Product events use the approved names and are analyzed offline rather than through an admin dashboard.

**Tech Stack:** Python, Pydantic, pytest, JSONL/CSV, pandas, Jinja2, Figma for final key screens

---

## File Map

- Create `evals/schema.py`, `runner.py`, `graders.py`, `report.py`.
- Create `evals/cases/*.jsonl` with exactly 30 reviewed cases.
- Create `evals/prompts/v1.yml` and `v2.yml` snapshots.
- Create ignored `evals/runs/` outputs and committed aggregate examples without private content.
- Create `analytics/events.py` and `analytics/report.py`.
- Create `docs/interview/evaluation-report.md`, `product-metrics.md`, `demo-script.md`, and `project-retrospective.md` from real results.

### Task 1: Define the evaluation schema and validators

**Files:** Create `evals/schema.py`, `evals/__init__.py`, and `test/test_eval_schema.py`.

- [ ] Test unique IDs, allowed categories, non-empty expected agents, required facts, forbidden behavior, rubric range, and rejection of secrets/absolute paths.
- [ ] Implement `EvalCase`, `AgentTrace`, `EvalRun`, and `GradeResult` Pydantic models with version fields.
- [ ] Run tests and commit: `feat(evals): define evaluation contracts`.

### Task 2: Build and review the 30-case dataset

**Files:** Create five JSONL files for network, knowledge, database, multi-Agent, and ambiguous/error categories.

- [ ] Add exactly 6 network, 6 knowledge, 6 database, 8 multi-Agent, and 4 ambiguity/error cases.
- [ ] Give every case a specific expected route, output type, required facts, forbidden behavior, and grading notes.
- [ ] Add a dataset validation test asserting 30 total unique cases and the exact category distribution.
- [ ] Run validation and commit: `test(evals): add representative agent dataset`.

### Task 3: Version prompts and build a common runner

**Files:** Create prompt snapshots, `evals/runner.py`, and `test/test_eval_runner.py`.

- [ ] Copy the actual V1 and approved V2 prompts into immutable eval snapshots.
- [ ] Test that the runner uses the same case, model settings, timeout, and data fixtures for both variants, records tool order/source mode/duration, and resumes without duplicating finished case IDs.
- [ ] Implement CLI arguments `--prompt-version`, `--case-file`, `--output`, and `--live`.
- [ ] Run offline tests and commit: `feat(evals): add reproducible prompt runner`.

### Task 4: Implement deterministic and human grading

**Files:** Create `evals/graders.py`, `evals/human_rubric.md`, and tests.

- [ ] Deterministically grade intent label, route precision/recall, required fact coverage, forbidden behavior, citation presence/support mapping, degradation labeling, invalid tool calls, and latency.
- [ ] Define a blinded 1-5 human rubric for correctness, completeness, plan quality, actionability, and trust.
- [ ] Test score aggregation and missing-review handling; do not treat missing human grades as zero.
- [ ] Commit: `feat(evals): add agent quality graders`.

### Task 5: Run V1/V2 and generate the evaluation report

**Files:** Create `evals/report.py` and generated `docs/interview/evaluation-report.md`.

- [ ] Run all 30 cases for V1 and V2 after the model key is valid; preserve raw run IDs and timestamps in ignored outputs.
- [ ] Complete blinded human scoring before revealing prompt version.
- [ ] Generate measured intent accuracy, routing accuracy, task completion, citation support, invalid tool calls, degradation accuracy, latency, and confidence intervals or sample counts.
- [ ] Explicitly include regressions and failure cases; never invent uplift.
- [ ] Commit only sanitized aggregate results: `docs: add measured agent evaluation report`.

### Task 6: Add product event instrumentation and analysis

**Files:** Create `analytics/events.py`, `analytics/report.py`, `test/test_analytics.py`, and `docs/interview/product-metrics.md`.

- [ ] Validate the approved event names, required task/session fields, timestamps, source modes, and absence of prompt/file content.
- [ ] Instrument backend and frontend event boundaries without double-counting reconnect replays.
- [ ] Generate funnel, effective complex task completion, degradation, retry, source click, follow-up, export, and feedback metrics from a fixture event file.
- [ ] Explain which metrics are product hypotheses versus measured interview-demo data.
- [ ] Commit: `feat: add privacy-safe product analytics`.

### Task 7: Produce final visual and interview artifacts

**Files:** Create `docs/interview/demo-script.md`, `project-retrospective.md`, and final screenshots under `docs/interview/assets/`.

- [ ] Capture the approved desktop screens from the running product: task input, plan confirmation, active multi-Agent run, transparent degradation, and sourced report.
- [ ] Recreate the three most important screens as a small Figma prototype using the final code as source of truth; do not design a separate mobile flow.
- [ ] Write a five-minute script covering user problem, product decision, live flow, evaluation evidence, one failure, and next iteration.
- [ ] Write a retrospective separating personal product decisions, engineering implementation, measured results, limitations, and rejected scope.
- [ ] Verify every claim maps to code, test output, screenshot, or evaluation result.
- [ ] Commit: `docs: add Coze interview presentation package`.

### Task 8: Final portfolio acceptance

**Files:** Modify only `AGENTS.md` for ongoing status; update `README.md` as the public project entry point.

- [ ] Run backend tests, frontend tests/build, eval validation, and the fixed live scenario three times.
- [ ] Verify no secret, absolute local path, private uploaded content, fabricated metric, stale air-conditioning/pharma narrative, or unmarked demo source appears in committed files.
- [ ] Update README with product problem, architecture, screenshots, measured results, setup, demo mode, security limits, and five-minute demo path.
- [ ] Update `AGENTS.md` with exact final commands, results, current external service state, and remaining risks.
- [ ] Commit: `docs: finalize Coze interview portfolio`.
