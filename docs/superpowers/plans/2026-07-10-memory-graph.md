# Memory Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local SQLite-backed memory graph where each completed user-assistant turn becomes a structured, retrievable memory node.

**Architecture:** Keep `MemoryStore` as the agent boundary and add `GraphMemoryStore` beside the existing JSONL store. The new store saves turn nodes, creates lightweight relation edges, retrieves relevant nodes with local scoring, and composes compact model context for LangGraph. The old JSONL store is display-only and does not contribute model context.

**Tech Stack:** Python dataclasses, sqlite3, json, pathlib, pytest, LangGraph integration through existing node functions.

---

### Task 1: Graph Memory Core

**Files:**
- Modify: `src/copy_myself/memory/base.py`
- Create: `src/copy_myself/memory/graph.py`
- Modify: `src/copy_myself/memory/__init__.py`
- Test: `tests/memory/test_graph_memory.py`

- [ ] Write failing tests for saving a turn node, loading it from SQLite, extracting memory buckets, listing recent nodes, and returning compact context.
- [ ] Implement `MemoryNode`, `MemoryEdge`, deterministic extraction, SQLite schema creation, `save_turn()`, `retrieve_nodes()`, `list_recent()`, and `get_brief_context()`.
- [ ] Run `python -m pytest tests/memory/test_graph_memory.py -v`.

### Task 2: Agent Turn Persistence

**Files:**
- Modify: `src/copy_myself/agent/graph.py`
- Test: `tests/agent/test_graph.py`

- [ ] Write a failing test proving completed agent runs call `save_turn()` when the memory store supports it.
- [ ] Add a small helper that prefers `save_turn(user_input, response, metadata)` and falls back to the existing two-message `save()` behavior.
- [ ] Run `python -m pytest tests/agent/test_graph.py -v`.

### Task 3: Graph Retrieval In LangGraph

**Files:**
- Modify: `src/copy_myself/agent/nodes.py`
- Test: `tests/agent/test_nodes.py`

- [ ] Write a failing test proving `load_memory_context()` can pass the current query to graph memory context composition.
- [ ] Update `load_memory_context()` to call `get_brief_context(query)` when supported, while preserving old zero-argument stores.
- [ ] Run `python -m pytest tests/agent/test_nodes.py -v`.

### Task 4: View Model Compatibility

**Files:**
- Test: `tests/gui/test_view_model.py`

- [ ] Write a failing test showing `WorkbenchViewModel.complete_memory_items()` lists graph node summaries.
- [ ] Keep the existing view-model interface unchanged if `GraphMemoryStore.list_recent()` already satisfies it.
- [ ] Run `python -m pytest tests/gui/test_view_model.py -v`.

### Task 5: Documentation And Verification

**Files:**
- Modify: `docs/architecture.md`
- Modify: `README.md`

- [ ] Document `GraphMemoryStore`, `memory_graph.sqlite3`, and the local-first retrieval flow.
- [ ] Run `python -m pytest -v`.
- [ ] Run `python -m compileall -q src tests`.

### Task 6: Retire Old Brief Memory

**Files:**
- Modify: `src/copy_myself/memory/persistent.py`
- Test: `tests/memory/test_persistent.py`

- [ ] Write failing tests proving the JSONL store still writes complete memory and sessions but returns no model context.
- [ ] Remove brief-memory generation, loading, model summarization, and `brief_memory.md` writes from `PersistentMemoryStore`.
- [ ] Run `python -m pytest tests/memory/test_persistent.py -v`.
