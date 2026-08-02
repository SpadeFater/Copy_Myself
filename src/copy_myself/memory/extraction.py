from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from copy_myself.memory.models import (
    EpisodeMemory,
    MemoryNode,
    PreferenceMemory,
    ProjectMemory,
    TaskMemory,
)


_CLAUSE_SPLIT = re.compile(r"[\r\n.!?。！？；;]+")
_STATUS_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("completed", ("completed", "done", "finished", "已完成", "完成")),
    ("blocked", ("blocked", "阻塞", "卡住")),
    ("in_progress", ("in progress", "ongoing", "进行中", "处理中")),
    ("pending", ("pending", "待办", "未开始", "计划")),
)
_TAG_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("chinese", ("chinese", "中文")),
    ("concise", ("concise", "简洁", "简短")),
    ("langgraph", ("langgraph",)),
    ("sqlite", ("sqlite",)),
    ("local-first", ("local-first", "local first", "本地优先")),
    ("review", ("review", "审查", "复核")),
)


@dataclass
class MemoryExtraction:
    preference_memory: PreferenceMemory = field(default_factory=PreferenceMemory)
    project_memory: ProjectMemory = field(default_factory=ProjectMemory)
    task_memory: TaskMemory = field(default_factory=TaskMemory)
    episode_memory: EpisodeMemory = field(default_factory=EpisodeMemory)
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    confidence: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "preference_memory": self.preference_memory.to_dict(),
            "project_memory": self.project_memory.to_dict(),
            "task_memory": self.task_memory.to_dict(),
            "episode_memory": self.episode_memory.to_dict(),
            "summary": self.summary,
            "tags": list(self.tags),
            "importance": self.importance,
            "confidence": self.confidence,
        }


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" \t,，:：")).strip()


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean_value = _clean(value)
        if clean_value and clean_value not in seen:
            result.append(clean_value)
            seen.add(clean_value)
    return result


def _clauses(user_input: str, assistant_response: str) -> list[str]:
    return [
        clause
        for clause in (_clean(item) for item in _CLAUSE_SPLIT.split(
            f"{user_input}\n{assistant_response}"
        ))
        if clause
    ]


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(phrase.lower() in lowered for phrase in phrases)


def _extract_language(text: str) -> str | None:
    lowered = text.lower()
    if "中文" in text or "chinese" in lowered:
        return "Chinese"
    if "英文" in text or "english" in lowered:
        return "English"
    return None


def _extract_preferences(clauses: list[str]) -> PreferenceMemory:
    preference_clauses = [
        clause
        for clause in clauses
        if _contains_any(
            clause,
            (
                "prefer",
                "preference",
                "like",
                "want",
                "please",
                "我喜欢",
                "我偏好",
                "请",
                "不要",
                "习惯",
            ),
        )
    ]
    style: list[str] = []
    for label, phrases in (
        ("concise", ("concise", "short", "brief", "简洁", "简短")),
        ("detailed", ("detailed", "详细", "展开")),
        ("formal", ("formal", "正式")),
    ):
        if any(_contains_any(clause, phrases) for clause in clauses):
            style.append(label)
    habits = [
        clause
        for clause in preference_clauses
        if _contains_any(clause, ("habit", "习惯", "always", "总是"))
    ]
    return PreferenceMemory(
        preferences=_unique(preference_clauses),
        habits=_unique(habits),
        language=next(
            (language for language in (_extract_language(item) for item in clauses) if language),
            None,
        ),
        response_style=style,
    )


def _extract_project(clauses: list[str]) -> ProjectMemory:
    facts: list[str] = []
    constraints: list[str] = []
    decisions: list[str] = []
    direction: list[str] = []

    for clause in clauses:
        lowered = clause.lower()
        if re.search(
            r"(?:project|项目).*(?:uses|use|built|based|采用|使用|基于|是|包含)",
            lowered,
        ):
            fact_match = re.search(
                r"((?:the )?(?:[\w-]+\s+)?project\s+uses\s+.+?)(?=\s+(?:and\s+)?(?:must|should|do not|don't|avoid)\b|$)",
                clause,
                re.IGNORECASE,
            )
            fact = fact_match.group(1) if fact_match else clause
            facts.append(_clean(re.sub(r"^the\s+", "", fact, flags=re.IGNORECASE)))
        if _contains_any(
            clause,
            ("must", "should", "do not", "don't", "avoid", "必须", "不要", "不能", "约束", "本地优先"),
        ):
            constraint_match = re.search(
                r"((?:must|should|do not|don't|keep|avoid)\b.+)",
                clause,
                re.IGNORECASE,
            )
            constraints.append(_clean(constraint_match.group(1) if constraint_match else clause))
        if _contains_any(clause, ("decided", "decision", "决定", "采用", "选用")):
            decisions.append(clause)
        if _contains_any(clause, ("direction", "roadmap", "方向", "路线", "目标")):
            direction.append(clause)

    return ProjectMemory(
        facts=_unique(facts),
        constraints=_unique(constraints),
        decisions=_unique(decisions),
        direction=_unique(direction),
    )


def _extract_task(clauses: list[str]) -> TaskMemory:
    active_tasks = [
        clause
        for clause in clauses
        if _contains_any(clause, ("task", "todo", "任务", "待办", "milestone", "里程碑"))
    ]
    status: str | None = None
    for candidate, phrases in _STATUS_PATTERNS:
        if any(_contains_any(clause, phrases) for clause in clauses):
            status = candidate
            break

    next_actions: list[str] = []
    for clause in clauses:
        match = re.search(r"next step is to (.+)", clause, re.IGNORECASE)
        if match is None:
            match = re.search(r"next step is (.+)", clause, re.IGNORECASE)
        if match is None:
            match = re.search(r"next step:\s*(.+)", clause, re.IGNORECASE)
        if match is None:
            match = re.search(r"(?:下一步|接下来)(?:是|要|：|:)?\s*(.+)", clause)
        if match:
            next_actions.append(_clean(match.group(1)))
        elif _contains_any(clause, ("next action", "下一步")):
            next_actions.append(clause)

    milestones = [
        clause
        for clause in clauses
        if _contains_any(clause, ("milestone", "里程碑", "deadline", "截止日期"))
    ]
    return TaskMemory(
        active_tasks=_unique(active_tasks),
        milestones=_unique(milestones),
        status=status,
        next_actions=_unique(next_actions),
    )


def _make_tags(
    user_input: str,
    assistant_response: str,
    preference: PreferenceMemory,
    project: ProjectMemory,
    task: TaskMemory,
) -> list[str]:
    text = f"{user_input} {assistant_response}"
    tags = ["episode"]
    if preference.language or preference.preferences or preference.response_style:
        tags.append("preference")
    if project.facts or project.constraints or project.decisions or project.direction:
        tags.append("project")
    if task.active_tasks or task.status or task.next_actions or task.milestones:
        tags.append("task")
    for tag, phrases in _TAG_KEYWORDS:
        if _contains_any(text, phrases):
            tags.append(tag)
    return tags


def extract_memory(user_input: str, assistant_response: str) -> MemoryExtraction:
    clean_user_input = user_input.strip()
    clean_assistant_response = assistant_response.strip()
    clauses = _clauses(clean_user_input, clean_assistant_response)
    preference = _extract_preferences(clauses)
    project = _extract_project(clauses)
    task = _extract_task(clauses)
    episode = EpisodeMemory(
        user_input=clean_user_input,
        assistant_response=clean_assistant_response,
        actions=list(task.next_actions),
        outcome=clean_assistant_response or None,
    )
    category_count = sum(
        (
            bool(preference.language or preference.preferences or preference.response_style),
            bool(project.facts or project.constraints or project.decisions or project.direction),
            bool(task.active_tasks or task.status or task.next_actions or task.milestones),
        )
    )
    importance = min(
        1.0,
        0.45 + category_count * 0.1 + (0.1 if project.constraints else 0.0) + (0.1 if task.next_actions else 0.0),
    )
    confidence = 0.9 if clean_user_input and clean_assistant_response else 0.75
    return MemoryExtraction(
        preference_memory=preference,
        project_memory=project,
        task_memory=task,
        episode_memory=episode,
        summary=_clean(clean_user_input or clean_assistant_response)[:240],
        tags=_make_tags(clean_user_input, clean_assistant_response, preference, project, task),
        importance=importance,
        confidence=confidence,
    )


def extract_memory_node(
    user_input: str,
    assistant_response: str,
    *,
    node_id: str | None = None,
    session: str | None = None,
    session_id: str | None = None,
    source: str = "local",
) -> MemoryNode:
    extracted = extract_memory(user_input, assistant_response)
    return MemoryNode(
        user_input=user_input,
        assistant_response=assistant_response,
        id=node_id or MemoryNode(user_input="", assistant_response="").id,
        preference_memory=extracted.preference_memory,
        project_memory=extracted.project_memory,
        task_memory=extracted.task_memory,
        episode_memory=extracted.episode_memory,
        summary=extracted.summary,
        tags=extracted.tags,
        importance=extracted.importance,
        confidence=extracted.confidence,
        session=session,
        session_id=session_id,
        source=source,
    )


extract_structured_memory = extract_memory
extract_memory_buckets = extract_memory


__all__ = [
    "MemoryExtraction",
    "extract_memory",
    "extract_memory_buckets",
    "extract_memory_node",
    "extract_structured_memory",
]
