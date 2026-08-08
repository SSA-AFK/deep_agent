# Backend Demo Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a secure, testable FastAPI and DeepAgents baseline that uses a real model and Zhihu search while transparently degrading MySQL and RAGFlow to deterministic demo data.

**Architecture:** Keep the existing FastAPI, DeepAgents, and tool modules, but introduce typed settings, tool results, health checks, and task state at their current ownership boundaries. The LLM remains required; Zhihu, MySQL, and RAGFlow expose the same structured result contract and may return explicit demo-mode data.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, DeepAgents, LangGraph/LangChain, httpx, MySQL Connector, RAGFlow SDK, pytest

---

## File Map

- Create `requirements-dev.txt`: test-only dependencies.
- Create `api/settings.py`: typed environment settings without import-time network calls.
- Create `api/errors.py`: stable public error codes and payloads.
- Create `api/task_manager.py`: in-process task state, cancellation, and event buffer.
- Create `tools/contracts.py`: common `ToolResult`, `SourceItem`, and live/demo enums.
- Create `tools/zhihu_search_tool.py`: real Zhihu global search and demo fallback.
- Create `tools/demo_sources.py`: validated loader for deterministic fixtures.
- Create `data/demo/search_results.json`, `data/demo/products.json`, `data/demo/knowledge.md`: interview-safe fixtures.
- Modify `agent/llm.py`: lazy model creation and authentication probe.
- Modify `agent/main_agent.py`: task manager integration and lazy agent creation.
- Modify `agent/subagents/network_search_agent.py`: use Zhihu instead of Tavily.
- Modify `tools/db_tools.py`: read-only enforcement and demo fallback.
- Modify `tools/ragflow_tools.py`: lazy client, cleanup, timeout, and fallback.
- Modify `utils/path_utils.py`, `tools/markdown_tools.py`, `api/server.py`, `api/monitor.py`: safety and stable events.
- Modify `prompt/prompts.yml`: one product-selection scenario and V2 routing rules.
- Test under `test/` with unit and integration files named below.

### Task 1: Establish the test and settings baseline

**Files:**
- Create: `requirements-dev.txt`
- Create: `api/settings.py`
- Modify: `test/test_01.py`
- Create: `test/test_settings.py`

- [ ] **Step 1: Add the development dependency file**

```text
-r requirements.txt
pytest==9.1.1
pytest-asyncio==1.3.0
```

- [ ] **Step 2: Install and prove the previous test gap is closed**

Run: `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`

Expected: installation succeeds and `.\.venv\Scripts\python.exe -m pytest --version` prints pytest 9.1.1.

- [ ] **Step 3: Write failing settings tests**

`test/test_settings.py` must verify that `Settings(_env_file=None)` accepts explicit values, treats the model key as required for readiness, and never includes secret values in `public_summary()`.

```python
from api.settings import Settings


def test_public_summary_never_exposes_secrets():
    settings = Settings(
        _env_file=None,
        llm_qwen_max="qwen-max",
        openai_api_key="model-secret",
        openai_base_url="https://example.invalid/v1",
        zhihu_access_secret="search-secret",
    )
    summary = str(settings.public_summary())
    assert "model-secret" not in summary
    assert "search-secret" not in summary
    assert settings.model_configured is True


def test_missing_model_key_is_not_ready():
    settings = Settings(_env_file=None, llm_qwen_max="qwen-max")
    assert settings.model_configured is False
```

- [ ] **Step 4: Run the tests and confirm the missing module failure**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_settings.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'api.settings'`.

- [ ] **Step 5: Implement `api/settings.py`**

Define one `Settings(BaseSettings)` with lowercase fields and uppercase aliases for model, Zhihu, MySQL, RAGFlow, CORS, upload limits, and request timeouts. Add `model_configured`, `public_summary()`, and a cached `get_settings()`; `public_summary()` returns booleans and endpoint hostnames only.

- [ ] **Step 6: Replace the empty smoke test**

Make `test/test_01.py` assert that `api.server.app.title == "DeepAgents API"` without making external network requests. This requires later tasks to preserve import safety.

- [ ] **Step 7: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_settings.py -q`

Expected: 2 passed.

Commit: `test: establish settings and pytest baseline`

### Task 2: Define stable tool and error contracts

**Files:**
- Create: `tools/contracts.py`
- Create: `api/errors.py`
- Create: `test/test_contracts.py`

- [ ] **Step 1: Write contract tests**

Test exact enum values `success/failed/degraded` and `live/demo`, JSON serialization, and public error serialization. Include a test that a failed result has no items and contains a retryable flag.

- [ ] **Step 2: Verify the tests fail because contracts do not exist**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_contracts.py -q`

Expected: collection fails on missing imports.

- [ ] **Step 3: Implement the contracts**

Create Pydantic models:

```python
class ToolStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"


class DataMode(StrEnum):
    LIVE = "live"
    DEMO = "demo"


class PublicError(BaseModel):
    code: str
    message: str
    user_action: str | None = None
    retryable: bool = False
    source: str


class SourceItem(BaseModel):
    title: str
    url: str | None = None
    snippet: str = ""
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    status: ToolStatus
    source: str
    mode: DataMode
    duration_ms: int = Field(ge=0)
    items: list[SourceItem] = Field(default_factory=list)
    error: PublicError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_contracts.py -q`

Expected: all contract tests pass.

Commit: `feat: add typed tool and error contracts`

### Task 3: Replace Tavily with Zhihu global search

**Files:**
- Create: `tools/zhihu_search_tool.py`
- Create: `data/demo/search_results.json`
- Create: `tools/demo_sources.py`
- Modify: `agent/subagents/network_search_agent.py`
- Create: `test/test_zhihu_search_tool.py`

- [ ] **Step 1: Write failing tests for request and normalization**

Mock `httpx.Client.get` and assert exact URL, `Query`, bounded `Count`, `SearchDB`, Bearer header, integer timestamp, timeout, `<em>` removal, and safe defaults when `ContentType` is empty or absent.

- [ ] **Step 2: Write failing degradation tests**

Parameterize timeout, HTTP 401, HTTP 429, HTTP 502, API Code non-zero, and invalid JSON. Each result must be `degraded/demo`, preserve a public error code, and return deterministic fixture items.

- [ ] **Step 3: Run the focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_zhihu_search_tool.py -q`

Expected: FAIL because the module is missing.

- [ ] **Step 4: Implement the fixture loader and Zhihu adapter**

Use `html.unescape` plus an HTML parser or a constrained tag remover for `<em>`. Clamp count to 1-20. Retry only 429 and 5xx twice with bounded backoff; never retry 401/403. Return normalized `SourceItem` metadata for author, authority, engagement, content type, and edit time.

- [ ] **Step 5: Expose the LangChain tool**

The decorated `internet_search` function keeps the existing Agent-facing name but calls `ZhihuSearchClient.search()` and returns `ToolResult.model_dump_json()` so the subagent migration stays narrow.

- [ ] **Step 6: Run live test only when explicitly enabled**

Run: `$env:RUN_LIVE_API_TESTS='1'; .\.venv\Scripts\python.exe -m pytest test/test_zhihu_search_tool.py -m live -q`

Expected: one live result, HTTP success, no secret in output. Remove the process environment variable afterward.

- [ ] **Step 7: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_zhihu_search_tool.py -q`

Expected: all offline tests pass.

Commit: `feat: replace Tavily with Zhihu search`

### Task 4: Add service health and lazy model initialization

**Files:**
- Create: `api/health.py`
- Modify: `agent/llm.py`
- Modify: `api/server.py`
- Create: `test/test_health.py`

- [ ] **Step 1: Write health tests**

Cover model configured/unconfigured, cached check results, Zhihu live/demo, MySQL live/demo, RAGFlow live/demo, Word availability, and `overall=blocked` when the model is unavailable.

- [ ] **Step 2: Verify red**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_health.py -q`

Expected: missing `api.health` failure.

- [ ] **Step 3: Implement lazy model creation**

Replace the module-level `model` with cached `get_model(settings=None)`. No network request occurs during import. Add `probe_model()` that makes the smallest completion request and maps 401 to `LLM_AUTH_FAILED` without exposing provider payloads.

- [ ] **Step 4: Implement `ServiceRegistry`**

Each probe has a short timeout and returns a typed public status. Cache for 30 seconds and provide `refresh=True` for explicit checks. Add `GET /api/health`.

- [ ] **Step 5: Run import and health tests**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_health.py test/test_01.py -q`

Expected: imports make no network calls; all tests pass.

- [ ] **Step 6: Commit**

Commit: `feat: add service health and lazy model loading`

### Task 5: Enforce file, upload, and Windows encoding safety

**Files:**
- Modify: `utils/path_utils.py`
- Modify: `tools/markdown_tools.py`
- Modify: `api/server.py`
- Create: `test/test_path_security.py`
- Create: `test/test_upload_api.py`

- [ ] **Step 1: Write traversal tests**

Cover `../`, absolute paths, Windows drive paths, repeated session names, encoded separators, unsafe `thread_id`, and filenames such as `../../outside.txt`. Assert all rejected paths remain outside neither `output/session_*` nor `updated/session_*`.

- [ ] **Step 2: Reproduce current failures**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_path_security.py test/test_upload_api.py -q`

Expected: traversal cases fail against current implementation.

- [ ] **Step 3: Implement strict resolution**

`resolve_session_path(filename, session_dir)` resolves the candidate and raises `PathBoundaryError` unless `candidate.is_relative_to(session_dir.resolve())`. Remove the current special allowance for absolute paths and embedded `updated/` paths.

- [ ] **Step 4: Validate upload identifiers**

Accept server UUID thread IDs plus the documented test prefix only. Use `Path(file.filename).name`, reject changed basenames, enforce configured count/size/type limits, and never return absolute server paths.

- [ ] **Step 5: Remove console-dependent Unicode output**

Replace the warning emoji print in `tools/markdown_tools.py` with ASCII logging. Add a subprocess test with `PYTHONUTF8` unset that generates Markdown successfully.

- [ ] **Step 6: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_path_security.py test/test_upload_api.py -q`

Expected: all boundary and encoding tests pass.

Commit: `fix: secure session files and Windows output`

### Task 6: Make MySQL read-only with demo fallback

**Files:**
- Modify: `tools/db_tools.py`
- Create: `data/demo/products.json`
- Create: `test/test_db_tools.py`

- [ ] **Step 1: Write SQL policy tests**

Accept one `SELECT` or `WITH ... SELECT`; reject comments hiding mutations, semicolon-separated statements, `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CALL`, and `LOAD`. Verify table names must come from discovered metadata.

- [ ] **Step 2: Verify current arbitrary SQL behavior fails policy tests**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_db_tools.py -q`

Expected: mutation-rejection tests fail.

- [ ] **Step 3: Implement read-only execution and limits**

Use a dedicated validator, remove autocommit for query tools, configure connection/read timeouts, cap rows and serialized bytes, and return `ToolResult`. Connection/authentication failures load `products.json` and return `degraded/demo`.

- [ ] **Step 4: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_db_tools.py -q`

Expected: policy, limits, live mocks, and fallback tests pass.

Commit: `fix: enforce read-only database tools`

### Task 7: Make RAGFlow lazy and safely degradable

**Files:**
- Modify: `tools/ragflow_tools.py`
- Create: `data/demo/knowledge.md`
- Create: `test/test_ragflow_tools.py`

- [ ] **Step 1: Write tests for lazy creation and cleanup**

Assert import does not instantiate `RAGFlow`; session deletion occurs on success and on ask failure; 502, timeout, invalid JSON, and empty assistant lists return demo knowledge with a public degradation error.

- [ ] **Step 2: Verify red and implement**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_ragflow_tools.py -q`

Expected before implementation: current import-time client and cleanup tests fail.

Implement cached client creation inside functions, bounded calls, `try/finally` session cleanup, normalized source items, and Markdown demo loading.

- [ ] **Step 3: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_ragflow_tools.py -q`

Expected: all tests pass without a live RAGFlow server.

Commit: `feat: add safe RAGFlow degradation`

### Task 8: Add task lifecycle and versioned events

**Files:**
- Create: `api/task_manager.py`
- Modify: `api/monitor.py`
- Modify: `api/server.py`
- Modify: `agent/main_agent.py`
- Create: `test/test_task_manager.py`
- Create: `test/test_task_api.py`

- [ ] **Step 1: Write lifecycle tests**

Test allowed transitions, cancellation, terminal-state immutability, monotonic event sequence, bounded event buffer, reconnect snapshot, and one task reference per ID.

- [ ] **Step 2: Implement the in-process task manager**

Use typed states from the approved design, an `asyncio.Lock`, stored task references, last result/error, and a bounded deque of version-1 events. This is explicitly single-process MVP state.

- [ ] **Step 3: Integrate endpoints**

Implement `GET /api/tasks/{id}`, `POST /api/tasks/{id}/confirm`, `POST /api/tasks/{id}/cancel`, and feedback persistence to a local ignored runtime file. Reject task creation with a structured 503 when model health is blocked.

- [ ] **Step 4: Update monitoring**

Emit `version`, `sequence`, `type`, `thread_id`, timestamp, and data. Keep ping/pong separate. Never place raw provider exceptions or secrets in user events.

- [ ] **Step 5: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_task_manager.py test/test_task_api.py -q`

Expected: lifecycle, API, cancellation, and reconnect tests pass.

Commit: `feat: add task lifecycle and recoverable events`

### Task 9: Align Agent prompts and orchestration

**Files:**
- Modify: `prompt/prompts.yml`
- Modify: `agent/prompts.py`
- Modify: `agent/main_agent.py`
- Modify: `agent/subagents/database_query_agent.py`
- Modify: `agent/subagents/knowledge_base_agent.py`
- Modify: `agent/subagents/network_search_agent.py`
- Create: `test/test_agent_configuration.py`

- [ ] **Step 1: Write configuration tests**

Assert there are exactly three named research roles, no air-conditioning or pharmaceutical narrative remains, Zhihu is the network provider, prompts require source/mode preservation, and prompt import prints nothing.

- [ ] **Step 2: Verify stale narrative failures**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_agent_configuration.py -q`

Expected: stale narrative and import-output assertions fail.

- [ ] **Step 3: Implement V2 prompts**

Use the fixed AI Agent platform selection and job-research scenario. Require intent/constraint extraction, plan generation, relevant-only routing, fact/opinion/inference separation, source support, conflict disclosure, transparent degradation, and no private chain-of-thought output.

- [ ] **Step 4: Remove import-time prompt printing and lazily build the Agent**

Create `get_main_agent()` after model readiness. Preserve LangGraph checkpointer configuration while ensuring API import is network-free.

- [ ] **Step 5: Run and commit**

Run: `.\.venv\Scripts\python.exe -m pytest test/test_agent_configuration.py test/test_health.py -q`

Expected: all tests pass with no stdout prompt dump.

Commit: `feat: align agents with the interview scenario`

### Task 10: Prove the backend demo baseline

**Files:**
- Create: `test/test_backend_e2e.py`
- Modify: `AGENTS.md`

- [ ] **Step 1: Add offline end-to-end tests**

Use a deterministic fake chat model and mocked Zhihu live response plus demo DB/RAG. Assert task creation, plan event, multiple Agent status events, source modes, terminal result, feedback, file list, and PDF-export failure isolation.

- [ ] **Step 2: Run the complete offline suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: all tests pass, zero warnings caused by application code, no external calls.

- [ ] **Step 3: Run fresh quality gates**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q agent api tools utils rawflow test
```

Expected: no broken requirements and no compile errors.

- [ ] **Step 4: Run the live smoke test after the user supplies a valid DashScope key**

Start the server on a free local port, verify `/docs`, `/api/health`, WebSocket, upload, and one fixed task. Expected: model live, Zhihu live, MySQL/RAGFlow demo, terminal `succeeded`, report available. Stop only the verified test-server PID.

- [ ] **Step 5: Run the fixed case three times**

Expected: 3/3 terminal success, no secret or absolute path in responses, at least two Agent roles used, one live and one demo source visible.

- [ ] **Step 6: Update the unique iterative document and commit**

Update only `AGENTS.md` with actual commands, results, remaining risks, and current service states.

Commit: `test: verify backend demo baseline`
