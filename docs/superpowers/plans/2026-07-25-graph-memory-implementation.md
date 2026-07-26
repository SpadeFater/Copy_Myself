# Graph Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace session-only string memory with a local-first SQLite graph memory system matching the project's `MemoryNode` and `MemoryEdge` rules.

**Architecture:** Keep memory behind a narrow protocol. Store each completed exchange as one durable `MemoryNode`, extract structured buckets deterministically, persist nodes and edges in SQLite, retrieve by keyword/tag scoring with optional relation expansion, and pass only compact ranked context to the model. Keep `InMemoryStore` as a test double and any legacy JSONL path display-only.

**Tech Stack:** Python 3, dataclasses, `sqlite3`, LangGraph, pytest.

---

### Task 1: Memory Models And Deterministic Extraction

**Files:**
- Create: `src/copy_myself/memory/models.py`
- Create: `src/copy_myself/memory/extraction.py`
- Create: `tests/memory/test_models.py`
- Create: `tests/memory/test_extraction.py`
- Modify: `src/copy_myself/memory/__init__.py`

- [ ] Define serializable `MemoryNode`, `MemoryEdge`, and four structured bucket types.
- [ ] Add failing tests for node creation, raw exchange preservation, bucket extraction, tags, and deterministic metadata.
- [ ] Verify the focused tests fail because the new API is absent.
- [ ] Implement minimal models and extraction.
- [ ] Run focused tests and compile the changed modules.

### Task 2: SQLite GraphMemoryStore

**Files:**
- Create: `src/copy_myself/memory/graph_store.py`
- Create: `tests/memory/test_graph_store.py`
- Modify: `src/copy_myself/memory/base.py`
- Modify: `src/copy_myself/memory/__init__.py`

- [ ] Add failing tests for schema initialization, exchange save, SQLite reload, edge creation, query-aware ranking, relation expansion, compact composition, and restart persistence.
- [ ] Verify the focused tests fail for the missing store behavior.
- [ ] Implement SQLite persistence without requiring API keys.
- [ ] Ensure raw nodes remain queryable while `retrieve_context` returns only ranked compact context.
- [ ] Run focused tests and compile the changed modules.

### Task 3: LangGraph, API, And PyQt Integration

**Files:**
- Modify: `src/copy_myself/agent/state.py`
- Modify: `src/copy_myself/agent/nodes.py`
- Modify: `src/copy_myself/agent/graph.py`
- Modify: `src/copy_myself/gui/view_model.py`
- Modify: `src/copy_myself/api/session_store.py`
- Modify: `src/copy_myself/gui/main_window.py`
- Create or modify: `tests/agent/test_graph_memory_integration.py`
- Modify: relevant existing agent, API, and GUI tests

- [ ] Add failing integration tests proving one exchange becomes one node and context is query-aware.
- [ ] Change the graph save node to persist one completed exchange.
- [ ] Make persistent product surfaces default to `GraphMemoryStore`; retain injectable `InMemoryStore` test doubles.
- [ ] Keep GUI display able to show durable raw records without leaking the entire database into model context.
- [ ] Run focused integration tests and compile the changed modules.

### Task 4: Legacy Display Boundary, Documentation, And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/development-roadmap.md`
- Modify: `AGENTS.md` only if implementation reality requires clarification
- Modify: `项目复盘与踩坑日志.md`
- Modify: `.gitignore` if generated database/cache rules are missing
- Modify or create: `tests/memory/test_legacy_display.py`

- [ ] Add failing coverage for display-only legacy memory behavior if a legacy implementation exists.
- [ ] Ensure no `brief_memory.md` model context is generated or loaded.
- [ ] Align setup, architecture, roadmap, and troubleshooting documentation with the implemented graph memory path.
- [ ] Run `python -m pytest -v`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Inspect the final diff and verify all Memory Graph Rules line by line.

