# Standard Agent Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable, testable LangGraph foundation for the Copy_Myself personal butler agent.

**Architecture:** The project uses a small Python package with a LangGraph state machine as the orchestration boundary. Tools and memory are defined behind protocols so future calendar, reminder, note, and long-term memory features can be added without rewriting the graph.

**Tech Stack:** Python 3.11+, LangGraph, pytest, standard library configuration and logging.

---

## File Structure

- `pyproject.toml`: package metadata, dependencies, pytest configuration, CLI script.
- `.env.example`: documented environment variables.
- `README.md`: project overview and local commands.
- `docs/architecture.md`: architecture and extension guide.
- `src/copy_myself/__init__.py`: package export.
- `src/copy_myself/config.py`: settings loaded from environment variables.
- `src/copy_myself/logging.py`: logging setup helper.
- `src/copy_myself/cli.py`: command-line entry point.
- `src/copy_myself/agent/state.py`: shared graph state type and factory.
- `src/copy_myself/agent/nodes.py`: graph node functions.
- `src/copy_myself/agent/graph.py`: LangGraph construction and invocation.
- `src/copy_myself/tools/base.py`: tool protocol and result type.
- `src/copy_myself/tools/registry.py`: tool registry.
- `src/copy_myself/tools/health.py`: sample health tool.
- `src/copy_myself/memory/base.py`: memory protocol.
- `src/copy_myself/memory/in_memory.py`: in-memory store.
- `tests/`: pytest coverage for the foundation.

## Tasks

### Task 1: Project Metadata and State

**Files:**
- Create: `pyproject.toml`
- Create: `src/copy_myself/__init__.py`
- Create: `src/copy_myself/agent/__init__.py`
- Create: `src/copy_myself/agent/state.py`
- Test: `tests/agent/test_state.py`

- [ ] Write failing tests for default state creation.
- [ ] Run `pytest tests/agent/test_state.py -v` and confirm import failure.
- [ ] Add package metadata and state implementation.
- [ ] Run `pytest tests/agent/test_state.py -v` and confirm pass.

### Task 2: Memory Foundation

**Files:**
- Create: `src/copy_myself/memory/__init__.py`
- Create: `src/copy_myself/memory/base.py`
- Create: `src/copy_myself/memory/in_memory.py`
- Test: `tests/memory/test_in_memory.py`

- [ ] Write failing tests for saving and searching memory records.
- [ ] Run `pytest tests/memory/test_in_memory.py -v` and confirm import failure.
- [ ] Implement memory protocol and in-memory store.
- [ ] Run `pytest tests/memory/test_in_memory.py -v` and confirm pass.

### Task 3: Tool Foundation

**Files:**
- Create: `src/copy_myself/tools/__init__.py`
- Create: `src/copy_myself/tools/base.py`
- Create: `src/copy_myself/tools/registry.py`
- Create: `src/copy_myself/tools/health.py`
- Test: `tests/tools/test_registry.py`

- [ ] Write failing tests for registering and running tools.
- [ ] Run `pytest tests/tools/test_registry.py -v` and confirm import failure.
- [ ] Implement tool protocol, registry, and health tool.
- [ ] Run `pytest tests/tools/test_registry.py -v` and confirm pass.

### Task 4: Graph Nodes and Routing

**Files:**
- Create: `src/copy_myself/agent/nodes.py`
- Test: `tests/agent/test_nodes.py`

- [ ] Write failing tests for intent detection, health routing, response creation, and error response.
- [ ] Run `pytest tests/agent/test_nodes.py -v` and confirm import failure.
- [ ] Implement focused node functions.
- [ ] Run `pytest tests/agent/test_nodes.py -v` and confirm pass.

### Task 5: LangGraph Assembly

**Files:**
- Create: `src/copy_myself/agent/graph.py`
- Test: `tests/agent/test_graph.py`

- [ ] Write failing tests for normal graph invocation and health tool invocation.
- [ ] Run `pytest tests/agent/test_graph.py -v` and confirm import failure.
- [ ] Implement LangGraph construction and `run_agent`.
- [ ] Run `pytest tests/agent/test_graph.py -v` and confirm pass.

### Task 6: CLI, Config, Logging, and Docs

**Files:**
- Create: `src/copy_myself/config.py`
- Create: `src/copy_myself/logging.py`
- Create: `src/copy_myself/cli.py`
- Create: `.env.example`
- Create: `README.md`
- Create: `docs/architecture.md`
- Test: `tests/test_cli.py`

- [ ] Write failing tests for CLI single-message output.
- [ ] Run `pytest tests/test_cli.py -v` and confirm import failure.
- [ ] Implement config, logging, CLI, and documentation.
- [ ] Run `pytest tests/test_cli.py -v` and confirm pass.
- [ ] Run `pytest -v` and confirm the foundation passes as a whole.
