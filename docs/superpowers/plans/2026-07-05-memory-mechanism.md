# Memory Mechanism Implementation Plan

> Retired on 2026-07-10: this plan describes the older JSONL plus brief-summary mechanism. Current development should use the memory graph plan, and the old JSONL store should remain display-only.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build durable complete memory, generated brief model memory, and PyQt new-session/close persistence.

**Architecture:** Add a persistent memory store under `src/copy_myself/memory/` while keeping `MemoryStore` as the graph boundary. The GUI view model owns session rotation and exposes complete memory for display. The graph loads brief memory when the store supports it.

**Tech Stack:** Python dataclasses, JSONL, pathlib, LangGraph graph nodes, PyQt6 widgets, pytest.

---

### Task 1: Persistent Memory Core

**Files:**
- Modify: `src/copy_myself/memory/base.py`
- Modify: `src/copy_myself/memory/in_memory.py`
- Create: `src/copy_myself/memory/persistent.py`
- Modify: `src/copy_myself/memory/__init__.py`
- Test: `tests/memory/test_persistent.py`

- [ ] Write failing tests for saving complete records, flushing JSONL files, loading existing memory, producing brief memory, and rotating sessions.
- [ ] Implement `MemoryRecord`, optional brief-context protocol behavior, deterministic summarization, model-backed summarization, and `PersistentMemoryStore`.
- [ ] Run `python -m pytest tests/memory/test_persistent.py -v`.

### Task 2: Graph Brief Memory Usage

**Files:**
- Modify: `src/copy_myself/agent/nodes.py`
- Test: `tests/agent/test_nodes.py`

- [ ] Write a failing test showing `load_memory_context` prefers `get_brief_context()`.
- [ ] Implement the preference while preserving `search()` fallback.
- [ ] Run `python -m pytest tests/agent/test_nodes.py -v`.

### Task 3: View Model Session Lifecycle

**Files:**
- Modify: `src/copy_myself/gui/view_model.py`
- Test: `tests/gui/test_view_model.py`

- [ ] Write failing tests for default persistent memory, complete memory listing, new conversation flushing, and chat reset.
- [ ] Implement view-model methods `complete_memory_items()`, `flush_memory()`, and `start_new_conversation()`.
- [ ] Run `python -m pytest tests/gui/test_view_model.py -v`.

### Task 4: PyQt Controls And Close Save

**Files:**
- Modify: `src/copy_myself/gui/main_window.py`
- Test: `tests/gui/test_main_window.py`

- [ ] Write failing tests for clicking new conversation and `closeEvent()` flushing memory.
- [ ] Add the new conversation button, complete-memory list, refresh behavior, and close hook.
- [ ] Run `python -m pytest tests/gui/test_main_window.py -v`.

### Task 5: Documentation And Verification

**Files:**
- Modify: `docs/architecture.md`
- Modify: `README.md`
- Modify: `项目复盘与踩坑日志.md`

- [ ] Document the `memory/` folder shape and PyQt persistence behavior.
- [ ] Run `python -m pytest -v`.
- [ ] Run `python -m compileall -q src tests`.
