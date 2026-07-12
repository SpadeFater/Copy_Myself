# Copy_Myself Development Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:writing-plans` before implementing each milestone, then use `superpowers:verification-before-completion` before marking it done.

**Goal:** Turn Copy_Myself from a runnable LangGraph foundation into a polished local-first PyQt personal butler agent that can chat, remember, plan, execute tools, and show how each agent run worked.

**Architecture:** Keep LangGraph as the orchestration center. Put model calls, memory storage, and external abilities behind narrow adapters. Keep PyQt widgets separate from the testable GUI view model so desktop behavior can be tested without launching a window.

**Tech Stack:** Python 3.11+, PyQt6, FastAPI, LangGraph, pytest, SQLite.

---

## Current Snapshot

- Python package exists under `src/copy_myself`.
- LangGraph flow exists: `load_memory -> classify_intent -> run_tool -> create_response`.
- CLI entry point exists through `copy-myself`.
- FastAPI exposes `/api/status` and `/api/chat` for integration surfaces.
- PyQt GUI package exists under `src/copy_myself/gui`.
- GUI state is tested through `WorkbenchViewModel`.
- PyQt6 dependency is declared and the desktop GUI launch has been verified locally.
- Real LLM, persistent memory, scheduler, packaging, and production deployment are not implemented yet.

## Working Rules

- Follow `AGENTS.md` as the project-level rule file.
- Every milestone starts with a focused spec or implementation plan.
- Every behavior change starts with a failing test where practical.
- Every task ends with local verification commands.
- Commit after each coherent milestone once tests pass.
- Keep external API calls out of unit tests.
- Prefer small adapters and protocols over hard-coded service calls.
- Do not build broad integrations before the first user workflow is excellent.

## Phase 0: Stabilize The Foundation

**Objective:** Make the scaffold clean, readable, testable, and safe to build on.

**Files likely touched:**
- `AGENTS.md`
- `README.md`
- `docs/architecture.md`
- `src/copy_myself/agent/`
- `src/copy_myself/gui/`
- `tests/`

### Task 0.1: Verify Baseline

- [x] Run `python -m pytest -v`.
- [x] Run `python -m compileall -q src tests`.
- [x] Install PyQt6 with `python -m pip install -e .[dev]`.
- [x] Launch `copy-myself-gui` once PyQt6 is installed.
- [x] Record failures in `项目复盘与踩坑日志.md`.

Expected result: we know exactly what is broken before changing behavior.

### Task 0.2: Clean Repository Hygiene

- [x] Decide whether `.idea/` should remain tracked. Recommendation: ignore editor workspace files and keep only project-agnostic config if truly needed.
- [x] Remove stale browser-interface references from docs and rules.
- [x] Make the first commit only after tests pass.
- [x] Add a short `CONTRIBUTING.md` with local setup, test commands, and commit rules.

Expected result: new work starts from a clean PyQt-oriented baseline.

## Phase 1: Define The First Real Butler Workflow

**Objective:** Choose one narrow workflow and make it excellent before adding many abilities.

**Recommended first workflow:** daily task planning.

**Why:** It needs chat, memory, tool execution, structured output, and GUI rendering, but does not require risky third-party integrations.

### Task 1.1: Product Decision

- [ ] Pick the first workflow: daily task planning, notes, reminders, or schedule review.
- [ ] Write the user story in one sentence.
- [ ] Define success criteria with concrete examples.

Recommended user story:

> As a user, I can tell Copy_Myself my goals for today, and it returns a prioritized plan with tasks, next actions, and follow-up questions.

### Task 1.2: Domain Model

- [ ] Create typed models for tasks, priorities, statuses, and plan summaries.
- [ ] Keep these models independent of FastAPI and PyQt.
- [ ] Add tests for validation and serialization.

Suggested backend files:
- `src/copy_myself/domain/tasks.py`
- `tests/domain/test_tasks.py`

### Task 1.3: Planning Tool

- [ ] Create a `DailyPlanTool`.
- [ ] Inputs: raw user request, known memory snippets, optional existing tasks.
- [ ] Output: structured plan with 3-7 tasks, priority, rationale, and next action.
- [ ] Unit test deterministic behavior without an LLM first.

Suggested backend files:
- `src/copy_myself/tools/daily_plan.py`
- `tests/tools/test_daily_plan.py`

### Task 1.4: PyQt Rendering

- [ ] Route planning requests through the graph.
- [ ] Return a human-readable response plus structured tool result.
- [ ] Render structured plans in the PyQt workbench as task rows or panels, not raw JSON.
- [ ] Keep rendering decisions outside graph nodes.

Expected result: CLI, API, and PyQt GUI can produce and display a structured daily plan.

## Phase 2: Persistent Memory

**Objective:** Replace session-only memory with durable local memory while keeping the memory protocol stable.

### Task 2.1: SQLite Memory Store

- [ ] Add `SQLiteMemoryStore`.
- [ ] Store role, content, timestamp, session id, tags, and metadata JSON.
- [ ] Add schema initialization code.
- [ ] Add tests using temporary databases.

Suggested backend files:
- `src/copy_myself/memory/sqlite_store.py`
- `tests/memory/test_sqlite_store.py`

### Task 2.2: Memory Configuration

- [ ] Add environment variables for memory backend and database path.
- [ ] Keep `InMemoryStore` available for tests.
- [ ] Wire CLI, API, and PyQt view model to the configured memory backend.

Expected result: conversations survive app restarts.

### Task 2.3: Memory UX

- [ ] Show relevant memories in the PyQt right inspector.
- [ ] Add a memory tab that lists saved facts and recent interactions.
- [ ] Add delete or archive behavior before memory grows unbounded.

Expected result: memory is visible and controllable, not mysterious.

## Phase 3: Real LLM Adapter

**Objective:** Add model-backed reasoning without spreading model API code across the graph.

### Task 3.1: Model Interface

- [ ] Define `ChatModel` protocol.
- [ ] Add `RuleBasedModel` for tests and local fallback.
- [ ] Add one real OpenAI-compatible model adapter behind environment configuration.
- [ ] Never require a real API key for tests.

Suggested backend files:
- `src/copy_myself/llm/base.py`
- `src/copy_myself/llm/rule_based.py`
- `src/copy_myself/llm/openai_adapter.py`
- `tests/llm/`

### Task 3.2: Prompt Contracts

- [ ] Create prompts for intent classification and response drafting.
- [ ] Require structured output for tool selection.
- [ ] Add tests for parser behavior and invalid model outputs.

### Task 3.3: Graph Integration

- [ ] Replace placeholder intent classification with model-assisted classification.
- [ ] Keep deterministic fallback for health checks and local tests.
- [ ] Add graceful error behavior when model configuration is missing.

Expected result: Copy_Myself can produce more natural, context-aware responses while staying testable.

## Phase 4: PyQt Workbench Product Quality

**Objective:** Make the desktop workbench feel like a real personal butler surface, not a scaffold.

### Task 4.1: Layout And Navigation

- [ ] Fix all copy and spacing.
- [ ] Use stable panel dimensions and sensible resizing behavior.
- [ ] Add empty, loading, error, and success states.
- [ ] Keep the first screen as the usable workbench.

### Task 4.2: Chat Experience

- [ ] Preserve conversation history per local session.
- [ ] Disable duplicate sends while a run is active.
- [ ] Show timestamps and run status.
- [ ] Keep slow agent runs off the UI thread.

### Task 4.3: Execution Inspector

- [ ] Return graph step details from the agent run boundary.
- [ ] Show each step, status, selected tool, tool result, and errors.
- [ ] Add tests for view model state produced by successful and failed runs.

### Task 4.4: GUI Verification

- [ ] Run `python -m pytest -v`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Launch `copy-myself-gui` after PyQt6 is installed.
- [ ] Manually verify health check, normal chat, blank input, and inspector updates.

Expected result: the desktop app is usable, inspectable, and pleasant.

## Phase 5: Reminders And Scheduling

**Objective:** Add the first background-like butler ability without relying on external calendar APIs.

### Task 5.1: Reminder Model

- [ ] Add reminder entity: title, due time, status, recurrence, source message.
- [ ] Store reminders in SQLite.
- [ ] Add tests for creation, listing, completion, and invalid dates.

### Task 5.2: Reminder Tool

- [ ] Add create, list, complete, and delete reminder tools.
- [ ] Route reminder requests through the graph.
- [ ] Return structured reminder results.

### Task 5.3: Local Scheduler

- [ ] Add a lightweight polling scheduler for due reminders.
- [ ] Surface due reminders in the PyQt workbench.
- [ ] Keep notification behavior local and explicit.

Expected result: Copy_Myself can remember and surface user-created reminders.

## Phase 6: Notes And Knowledge Capture

**Objective:** Let the butler save useful user knowledge and retrieve it later.

### Task 6.1: Notes Model

- [ ] Add notes with title, content, tags, created time, updated time.
- [ ] Store notes in SQLite.
- [ ] Add search by text and tag.

### Task 6.2: Note Tools

- [ ] Add create, update, search, and summarize note tools.
- [ ] Route note-taking requests through the graph.
- [ ] Show note results in the PyQt workbench.

Expected result: Copy_Myself becomes useful for lightweight personal knowledge management.

## Phase 7: Observability And Reliability

**Objective:** Make failures diagnosable and behavior measurable.

### Task 7.1: Structured Logging

- [ ] Add request id and session id to logs.
- [ ] Log graph steps, tool calls, model calls, and errors.
- [ ] Avoid logging secrets or full private content by default.

### Task 7.2: Error Handling

- [ ] Standardize error objects across tools, graph, API, and GUI view model.
- [ ] Add user-facing fallback messages.
- [ ] Add tests for tool failure, model failure, and malformed requests.

### Task 7.3: Test Matrix

- [ ] Keep unit tests fast and deterministic.
- [ ] Add API integration tests for chat, status, memory, and planning.
- [ ] Add GUI view model tests for every expected UI state.
- [ ] Add manual GUI smoke checklist after the main workflow stabilizes.

Expected result: regressions are caught early and errors are understandable.

## Phase 8: Packaging And Distribution

**Objective:** Make the app easy to run on a fresh machine.

### Task 8.1: Local Developer Experience

- [ ] Add `Makefile`, `justfile`, or PowerShell scripts for common commands.
- [ ] Add `.env.example` entries for all configurable behavior.
- [ ] Add README quickstart for CLI, API, and PyQt GUI.

### Task 8.2: Desktop Packaging

- [ ] Decide between source install, PyInstaller, or another Windows desktop packaging route.
- [ ] Add production launch instructions.
- [ ] Add an icon and app metadata once the GUI stabilizes.

### Task 8.3: CI

- [ ] Add GitHub Actions for Python tests.
- [ ] Add compile checks.
- [ ] Add lint/typecheck once the codebase is stable enough that they help more than they slow.

Expected result: anyone can clone, install, test, and run the desktop project predictably.

## Definition Of Perfect For This Project

The project is "perfect" for a serious first version when:

- A user can run the CLI, API, and PyQt GUI from the README without guessing.
- The Chinese UI and backend responses are readable and consistent.
- The first real workflow works from CLI, API, and PyQt GUI.
- Conversations and important facts persist across restarts.
- The PyQt inspector shows what happened during each agent run.
- Unit and integration tests pass locally.
- Python modules compile cleanly.
- External services are optional or fail gracefully when not configured.
- The architecture still has clear boundaries: graph, tools, memory, model, API, GUI.

## Recommended Immediate Next Step

Finish **Phase 0: Stabilize The Foundation**.

Exact next commands:

```powershell
python -m pytest -v
python -m compileall -q src tests
python -m pip install -e .[dev]
copy-myself-gui
```

If PyQt6 installation is blocked by network speed, continue backend and view-model work while recording that GUI launch remains unverified.
