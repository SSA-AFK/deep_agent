# Desktop Research Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished ChatGPT-style desktop web interface for task creation, plan confirmation, multi-Agent progress, transparent sources, feedback, and report export.

**Architecture:** Create a React/TypeScript Vite application in `frontend/` with a small API client, normalized task store, and focused conversation components. The backend remains the source of truth; WebSocket events update local state and REST snapshots recover interrupted connections.

**Tech Stack:** React, TypeScript, Vite, Vitest, Testing Library, Lucide icons, native CSS variables, Playwright

---

## File Map

- Create `frontend/` with Vite configuration and scripts.
- Create `frontend/src/api/`: HTTP, WebSocket, and generated-by-hand contract types matching backend v1.
- Create `frontend/src/state/task-store.ts`: normalized task and reconnect state.
- Create `frontend/src/components/shell/`: sidebar, header, composer.
- Create `frontend/src/components/conversation/`: plan, Agent progress, sources, report, errors, feedback.
- Create `frontend/src/styles/`: tokens, layout, and component CSS.
- Create component tests beside components and `frontend/e2e/demo-flow.spec.ts`.

### Task 1: Scaffold a deterministic frontend toolchain

**Files:** Create `frontend/package.json`, Vite/TypeScript configs, `index.html`, `src/main.tsx`, `src/App.tsx`, and `src/test/setup.ts`.

- [ ] Add scripts `dev`, `build`, `test`, `test:run`, and `e2e`; pin dependencies and commit the lockfile.
- [ ] Write an initial test that renders the product name and fails before `App` exists.
- [ ] Implement the minimal app and run `npm run test:run` plus `npm run build`.
- [ ] Commit: `feat(frontend): scaffold desktop workbench`.

### Task 2: Define API contracts and recovery behavior

**Files:** Create `frontend/src/api/types.ts`, `client.ts`, `socket.ts`, `src/state/task-store.ts`, and tests.

- [ ] Encode the approved task states, health response, version-1 events, sources, public errors, and result types as TypeScript unions/interfaces.
- [ ] Test sequence deduplication, out-of-order rejection, reconnect backoff, REST snapshot merge, and no retry for terminal tasks.
- [ ] Implement `TaskStore` as a reducer with no component-specific DOM logic.
- [ ] Run focused tests and commit: `feat(frontend): add task API and recovery store`.

### Task 3: Build the ChatGPT-style application shell

**Files:** Create sidebar, header, composer, icon button, tooltip, and CSS token files.

- [ ] Test new-task action, history selection, attachment selection, multiline input, Enter-to-send, Shift+Enter newline, disabled submission, and stop state.
- [ ] Implement a fixed-width left history rail, restrained header, unframed conversation column, and bottom composer using Lucide icons with tooltips.
- [ ] Use neutral surfaces with a distinct green success color, amber degradation color, and red failure color; do not use gradients, nested cards, oversized headings, or viewport-scaled fonts.
- [ ] Verify at 1024x768, 1440x900, and 1920x1080; commit: `feat(frontend): build desktop conversation shell`.

### Task 4: Implement plan confirmation

**Files:** Create `PlanMessage.tsx`, `PlanStep.tsx`, and tests.

- [ ] Test planning skeleton, editable step labels, data-source badges, confirm, cancel, and validation for an empty plan.
- [ ] Implement the plan as an inline assistant message, not a modal or dashboard.
- [ ] Run tests and commit: `feat(frontend): add editable execution plans`.

### Task 5: Implement the multi-Agent execution message

**Files:** Create `AgentRunMessage.tsx`, `AgentRow.tsx`, `SourceList.tsx`, `ModeBadge.tsx`, and tests.

- [ ] Test all Agent states, stable row dimensions, live/demo labels, elapsed time, source expansion, retryable errors, and single-Agent failure while others continue.
- [ ] Implement one compact bordered execution surface with rows rather than nested cards. Do not expose chain-of-thought; show only declared actions and results.
- [ ] Ensure state changes do not shift surrounding layout; commit: `feat(frontend): visualize multi-agent execution`.

### Task 6: Implement results, citations, feedback, and export

**Files:** Create `ReportMessage.tsx`, `Citation.tsx`, `FeedbackBar.tsx`, `ExportButton.tsx`, and tests.

- [ ] Test summary-first rendering, citation/source mode, missing URL behavior, fact/opinion labels, follow-up composer, positive/negative feedback reasons, PDF download, and export retry.
- [ ] Implement citations as accessible links or non-link source references, never raw server paths.
- [ ] Run tests and commit: `feat(frontend): add sourced reports and feedback`.

### Task 7: Implement health and failure UX

**Files:** Create `ServiceStatusMenu.tsx`, `InlineError.tsx`, `DegradationNotice.tsx`, and tests.

- [ ] Test blocked model, degraded source, reconnecting, cancelled, needs-input, all-sources-failed, and retry states using exact public error fields.
- [ ] Show detailed service status in a menu; keep the main conversation notice concise and actionable.
- [ ] Verify no raw stack, key, connection string, or absolute path renders; commit: `feat(frontend): add transparent recovery states`.

### Task 8: Complete browser-level verification

**Files:** Create `frontend/e2e/demo-flow.spec.ts`; update `AGENTS.md` with actual results only.

- [ ] Run `npm run test:run` and `npm run build`; expected zero failures.
- [ ] Start backend and frontend on verified free ports and run Playwright through input, upload, plan confirmation, Agent progress, degradation, report, feedback, and export.
- [ ] Capture desktop screenshots at the three approved viewports and inspect for overlap, clipping, blank states, unstable controls, and unreadable text.
- [ ] Check browser console and failed network requests; expected no unhandled errors.
- [ ] Commit: `test(frontend): verify desktop research workflow`.
