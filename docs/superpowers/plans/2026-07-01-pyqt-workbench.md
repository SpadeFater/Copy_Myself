# PyQt Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a PyQt desktop GUI while preserving the existing agent, CLI, and API foundations.

**Architecture:** Add a small GUI package that calls `run_agent` directly through a testable view model. Keep PyQt widgets in `main_window.py` and keep state transitions in `view_model.py` so tests do not need to open a real window.

**Tech Stack:** Python 3.11+, PyQt6, LangGraph, pytest.

---

## File Structure

- `pyproject.toml`: add PyQt6 dependency and `copy-myself-gui` script.
- `README.md`: document the PyQt GUI run command and keep API/CLI commands.
- `src/copy_myself/gui/__init__.py`: GUI package marker.
- `src/copy_myself/gui/view_model.py`: chat messages, run summaries, and agent invocation wrapper.
- `src/copy_myself/gui/main_window.py`: PyQt main window with sidebar, chat, overview, and inspector.
- `src/copy_myself/gui/app.py`: QApplication entry point.
- `tests/gui/test_view_model.py`: view model tests without Qt window startup.

## Tasks

### Task 1: GUI View Model

**Files:**
- Create: `tests/gui/test_view_model.py`
- Create: `src/copy_myself/gui/__init__.py`
- Create: `src/copy_myself/gui/view_model.py`

- [ ] **Step 1: Write failing tests**

```python
from copy_myself.gui.view_model import WorkbenchViewModel


def test_view_model_starts_with_welcome_message() -> None:
    view_model = WorkbenchViewModel()

    assert view_model.messages[0].role == "assistant"
    assert "Copy_Myself" in view_model.messages[0].content
    assert view_model.latest_run is None


def test_send_message_updates_messages_and_run_summary() -> None:
    view_model = WorkbenchViewModel()

    run = view_model.send_message("health check")

    assert view_model.messages[-2].role == "user"
    assert view_model.messages[-2].content == "health check"
    assert view_model.messages[-1].role == "assistant"
    assert run.intent == "health_check"
    assert run.tool_result == {"status": "ok", "source": "agent"}
    assert view_model.latest_run == run


def test_send_message_ignores_blank_input() -> None:
    view_model = WorkbenchViewModel()
    before = list(view_model.messages)

    result = view_model.send_message("   ")

    assert result is None
    assert view_model.messages == before
```

- [ ] **Step 2: Run tests and confirm import failure**

Run: `python -m pytest tests/gui/test_view_model.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'copy_myself.gui'`.

- [ ] **Step 3: Implement view model**

- [ ] **Step 4: Run view model tests**

Run: `python -m pytest tests/gui/test_view_model.py -v`

Expected: PASS.

### Task 2: PyQt Application Shell

**Files:**
- Create: `src/copy_myself/gui/app.py`
- Create: `src/copy_myself/gui/main_window.py`
- Modify: `pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Add PyQt dependency and script**

Add `PyQt6>=6.7.0` and `copy-myself-gui = "copy_myself.gui.app:main"`.

- [ ] **Step 2: Implement main window**

Create a three-panel desktop shell:
- left sidebar with workbench navigation
- center overview, conversation list, and composer
- right inspector for graph steps, tool result, and memory context

- [ ] **Step 3: Implement app entry point**

Create a `QApplication`, instantiate `MainWindow`, show it, and return `app.exec()`.

- [ ] **Step 4: Update docs**

Add `copy-myself-gui` usage to README.

### Task 3: Verification

**Files:**
- All files above.

- [ ] **Step 1: Run focused GUI tests**

Run: `python -m pytest tests/gui/test_view_model.py -v`

Expected: PASS.

- [ ] **Step 2: Run full backend test suite**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Verify package metadata**

Run: `python -m pip install -e .[dev]`

Expected: package installs with `copy-myself-gui` entry point available. If network or dependency installation is unavailable, report that clearly.
