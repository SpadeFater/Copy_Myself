# GUI Workbench Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved compact sci-fi three-column PyQt workbench with hidden-by-default memory and visible execution/tool/plan panels.

**Architecture:** Keep `MainWindow` as the widget assembly boundary and `WorkbenchViewModel` as testable GUI state. Use `ToolRegistry.catalog()` for available tool display and keep external MCP visibility as a non-invoking status row. The left rail exposes only `工作台`, `记忆`, and `设置`; the right inspector omits tool-result rendering.

**Tech Stack:** Python, PyQt6, LangGraph-backed `WorkbenchViewModel`, pytest.

---

### Task 1: Add GUI Behavior Tests

**Files:**
- Modify: `tests/gui/test_main_window.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert:

```python
def test_main_window_shows_tool_stage_plan_and_memory_button(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication, QLabel
    from copy_myself.gui import main_window

    app = QApplication.instance() or QApplication([])
    window = main_window.MainWindow()
    app.processEvents()

    labels = [label.text() for label in window.findChildren(QLabel)]
    assert "执行阶段" in labels
    assert "计划列表" in labels
    assert "可调用工具" in labels
    assert window.complete_memory_button.text() == "完整记忆"
    assert window.complete_memory.parent() is None
    assert window.tools_list.count() >= 2
```

```python
def test_main_window_memory_button_opens_complete_memory_dialog(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    from copy_myself.gui import main_window
    from copy_myself.gui.view_model import WorkbenchViewModel
    from copy_myself.memory import PersistentMemoryStore

    app = QApplication.instance() or QApplication([])
    memory = PersistentMemoryStore(root=tmp_path, session_id="session-a")
    memory.save("user", "只在点击按钮后查看")
    window = main_window.MainWindow(view_model=WorkbenchViewModel(memory=memory))

    dialog = window._build_complete_memory_dialog()

    assert dialog.windowTitle() == "完整记忆"
    assert dialog.memory_list.count() == 1
    assert "只在点击按钮后查看" in dialog.memory_list.item(0).text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\gui\test_main_window.py::test_main_window_shows_tool_stage_plan_and_memory_button tests\gui\test_main_window.py::test_main_window_memory_button_opens_complete_memory_dialog -v`

Expected: fail because `complete_memory_button`, `tools_list`, `plan_list`, or `_build_complete_memory_dialog()` do not exist yet.

### Task 2: Implement Workbench Panels

**Files:**
- Modify: `src/copy_myself/gui/main_window.py`
- Modify: `src/copy_myself/gui/view_model.py`

- [ ] **Step 1: Add GUI state helpers**

Add a `plan_items()` helper to `WorkbenchViewModel` that returns default plan items before a run and run-aware items after completion.

- [ ] **Step 2: Add widgets**

In `MainWindow.__init__`, add:

```python
self.plan_list = QListWidget()
self.tools_list = QListWidget()
self.complete_memory_button = QPushButton("完整记忆")
```

- [ ] **Step 3: Replace inspector memory list with a button**

In `_build_inspector()`, show execution stages, plan list, available tools, current intent, tool result, and the memory button. Do not add `self.complete_memory` to the visible layout.

- [ ] **Step 4: Add memory dialog builder**

Add `_build_complete_memory_dialog()` returning a `QDialog` with a `memory_list` attribute and items from `complete_memory_items()`.

- [ ] **Step 5: Refresh tools and plan panels**

Add `_refresh_tools()` and update `_refresh_inspector()` to populate `steps_list`, `plan_list`, `tools_list`, `intent_value`, and `tool_result`.

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests\gui\test_main_window.py tests\gui\test_view_model.py -v`

Expected: pass.

### Task 3: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/project-review-log.md`

- [ ] **Step 1: Update README**

Document the new GUI organization and hidden-by-default complete memory viewer.

- [ ] **Step 2: Update review log**

Append a 2026-07-12 entry summarizing the redesign and verification.

- [ ] **Step 3: Full verification**

Run:

```powershell
python -m pytest -v
python -m compileall -q src tests
```

Expected: both commands exit 0.
