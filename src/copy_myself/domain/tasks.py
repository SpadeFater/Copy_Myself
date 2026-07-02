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
