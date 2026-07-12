# Daily Task Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first real butler workflow so Copy_Myself can turn a user's daily goals into a structured, prioritized plan.

**Architecture:** Keep planning logic behind a small deterministic tool first, then route it through the existing LangGraph boundary. Define the task and plan data models in a backend-only domain module so both the graph and GUI can reuse them without depending on PyQt or FastAPI.

**Tech Stack:** Python 3.11+, dataclasses, enum, pytest, LangGraph, PyQt6.

---

## File Structure

- `src/copy_myself/domain/tasks.py`: typed models for task priorities, task status, task items, and daily plans.
- `tests/domain/test_tasks.py`: validation and basic serialization behavior for the domain models.
- `src/copy_myself/tools/daily_plan.py`: deterministic daily planning tool that converts a request into a structured plan.
- `tests/tools/test_daily_plan.py`: tool behavior tests for normal, partial, and blank input.
- `src/copy_myself/tools/registry.py`: register the new planning tool so the graph can call it.
- `src/copy_myself/agent/nodes.py`: route planning requests to the tool and shape the graph state response.
- `src/copy_myself/agent/graph.py`: ensure the graph exposes the new intent/tool path cleanly if needed.
- `src/copy_myself/gui/view_model.py`: preserve structured tool output for the PyQt inspector.
- `README.md`: add a short daily-planning example for CLI usage.
- `docs/architecture.md`: note that the first concrete butler workflow is daily task planning.
- `docs/development-roadmap.md`: mark Phase 1 planning tasks complete after verification.
- `项目复盘与踩坑日志.md`: record implementation notes and test results.

## Tasks

### Task 1: Define The Domain Models

**Files:**
- Create: `src/copy_myself/domain/tasks.py`
- Test: `tests/domain/test_tasks.py`

- [x] **Step 1: Write the failing tests**

```python
from copy_myself.domain.tasks import DailyPlan, TaskItem, TaskPriority, TaskStatus


def test_task_item_defaults_to_todo() -> None:
    item = TaskItem(
        title="整理今天的任务",
        priority=TaskPriority.HIGH,
        rationale="先处理最重要的事情",
        next_action="列出前三件事",
    )

    assert item.status == TaskStatus.TODO


def test_daily_plan_keeps_tasks_and_questions() -> None:
    plan = DailyPlan(
        request="帮我安排今天",
        summary="先做高优先级任务",
        tasks=[
            TaskItem(
                title="写日报",
                priority=TaskPriority.HIGH,
                rationale="今天必须交付",
                next_action="先写三条要点",
            )
        ],
        follow_up_questions=["今天有固定会议吗？"],
    )

    assert plan.request == "帮我安排今天"
    assert plan.tasks[0].title == "写日报"
    assert plan.follow_up_questions == ["今天有固定会议吗？"]
```

- [x] **Step 2: Run the tests and confirm import failure**

Run: `python -m pytest tests/domain/test_tasks.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'copy_myself.domain'`.

- [x] **Step 3: Implement the domain module**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TaskPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass(frozen=True)
class TaskItem:
    title: str
    priority: TaskPriority
    rationale: str
    next_action: str
    status: TaskStatus = TaskStatus.TODO


@dataclass(frozen=True)
class DailyPlan:
    request: str
    summary: str
    tasks: list[TaskItem] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
```

- [x] **Step 4: Run the tests and confirm pass**

Run: `python -m pytest tests/domain/test_tasks.py -v`

Expected: PASS.

### Task 2: Build The Deterministic Planning Tool

**Files:**
- Create: `src/copy_myself/tools/daily_plan.py`
- Test: `tests/tools/test_daily_plan.py`

- [ ] **Step 1: Write the failing tests**

```python
from copy_myself.tools.daily_plan import DailyPlanTool


def test_daily_plan_tool_generates_three_tasks() -> None:
    tool = DailyPlanTool()

    result = tool.run(
        {
            "request": "今天我要整理简历、学习 LangGraph、去健身",
            "memory_context": ["最近在找工作"],
        }
    )

    assert result["intent"] == "daily_plan"
    assert len(result["plan"]["tasks"]) == 3
    assert result["plan"]["tasks"][0]["priority"] == "high"
    assert result["plan"]["tasks"][0]["next_action"]


def test_daily_plan_tool_rejects_blank_request() -> None:
    tool = DailyPlanTool()

    result = tool.run({"request": "   "})

    assert result["error"]["code"] == "empty_request"
```

- [ ] **Step 2: Run the tests and confirm import failure**

Run: `python -m pytest tests/tools/test_daily_plan.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'copy_myself.tools.daily_plan'`.

- [ ] **Step 3: Implement the tool**

```python
from __future__ import annotations

from copy_myself.domain.tasks import DailyPlan, TaskItem, TaskPriority


class DailyPlanTool:
    name = "daily_plan"
    description = "Create a structured daily task plan."

    def run(self, arguments: dict[str, object]) -> dict[str, object]:
        request = str(arguments.get("request", "")).strip()
        if not request:
            return {
                "intent": "daily_plan",
                "error": {
                    "code": "empty_request",
                    "message": "request must not be blank",
                },
            }

        keywords = [part.strip() for part in request.replace("、", ",").split(",") if part.strip()]
        if not keywords:
            keywords = [request]

        tasks = []
        for index, keyword in enumerate(keywords[:5]):
            priority = TaskPriority.HIGH if index == 0 else TaskPriority.MEDIUM
            tasks.append(
                TaskItem(
                    title=keyword,
                    priority=priority,
                    rationale="根据用户当天目标拆成可执行事项",
                    next_action=f"先处理：{keyword}",
                )
            )

        plan = DailyPlan(
            request=request,
            summary="先完成最重要的事项，再处理其余任务。",
            tasks=tasks,
            follow_up_questions=["今天有哪些固定会议或硬截止时间？"],
        )
        return {
            "intent": "daily_plan",
            "plan": {
                "request": plan.request,
                "summary": plan.summary,
                "tasks": [
                    {
                        "title": task.title,
                        "priority": task.priority.value,
                        "rationale": task.rationale,
                        "next_action": task.next_action,
                        "status": task.status.value,
                    }
                    for task in plan.tasks
                ],
                "follow_up_questions": plan.follow_up_questions,
            },
        }
```

- [ ] **Step 4: Run the tests and confirm pass**

Run: `python -m pytest tests/tools/test_daily_plan.py -v`

Expected: PASS.

### Task 3: Route Planning Through The Graph

**Files:**
- Modify: `src/copy_myself/tools/registry.py`
- Modify: `src/copy_myself/agent/nodes.py`
- Modify: `src/copy_myself/agent/graph.py` if the new tool needs graph wiring
- Modify: `tests/agent/test_nodes.py`
- Modify: `tests/agent/test_graph.py`

- [ ] **Step 1: Write the failing graph tests**

Add tests that assert a planning request:
- routes to the daily plan tool,
- returns `intent == "daily_plan"`,
- and includes a structured plan in `tool_result`.

- [ ] **Step 2: Run the tests and confirm failure**

Run: `python -m pytest tests/agent/test_nodes.py tests/agent/test_graph.py -v`

Expected: FAIL because the graph does not know the new workflow yet.

- [ ] **Step 3: Wire the tool into the registry and nodes**

Add `DailyPlanTool()` to the tool registry and update the intent classification / routing logic so requests containing planning language select the daily plan path.

- [ ] **Step 4: Run the tests and confirm pass**

Run: `python -m pytest tests/agent/test_nodes.py tests/agent/test_graph.py -v`

Expected: PASS.

### Task 4: Preserve Structured Output In The GUI

**Files:**
- Modify: `src/copy_myself/gui/view_model.py`
- Modify: `tests/gui/test_view_model.py` if needed

- [ ] **Step 1: Add/adjust a test for planning output**

Verify that `WorkbenchViewModel.send_message(...)` keeps the structured plan in `latest_run.tool_result`.

- [ ] **Step 2: Run the GUI view-model test**

Run: `python -m pytest tests/gui/test_view_model.py -v`

Expected: PASS.

- [ ] **Step 3: Keep the view model thin**

Do not add PyQt rendering logic here; only preserve the structured result so the window can display it later.

### Task 5: Update Documentation And Record Results

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/development-roadmap.md`
- Modify: `项目复盘与踩坑日志.md`

- [ ] **Step 1: Add one daily-planning example to the README**

Show a CLI example such as:

```powershell
copy-myself "帮我安排今天的任务"
```

- [ ] **Step 2: Mark the roadmap items complete**

Mark the Phase 1 daily-planning tasks as done after tests pass.

- [ ] **Step 3: Append the implementation note to the log**

Record:
- which files changed,
- what the tool returns,
- and the exact test commands used.

### Task 6: Final Verification

**Files:**
- All changed files

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/domain/test_tasks.py tests/tools/test_daily_plan.py tests/agent/test_nodes.py tests/agent/test_graph.py tests/gui/test_view_model.py -v
```

Expected: PASS.

- [ ] **Step 2: Run the full suite**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Run compile check**

Run: `python -m compileall -q src tests`

Expected: PASS.

- [ ] **Step 4: Commit**

Commit after the workflow is stable and documented.

## Self-Review

- Spec coverage: domain model, planning tool, graph routing, GUI preservation, and docs are all covered.
- Placeholder scan: no TBD or vague "handle edge cases" steps.
- Type consistency: `TaskPriority`, `TaskStatus`, `TaskItem`, and `DailyPlan` are used consistently across tasks.
