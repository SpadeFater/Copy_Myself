from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, TypeVar


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


VALID_MEMORY_RELATIONS = frozenset(
    {
        "semantic_similarity",
        "same_project",
        "same_task",
        "preference_relation",
        "support",
        "contradiction",
        "supersession",
    }
)


def _jsonable(value: Any, path: str = "value") -> Any:
    if is_dataclass(value):
        return {
            item.name: _jsonable(getattr(value, item.name), f"{path}.{item.name}")
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        serialized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"{path} contains a non-string key of type {type(key).__name__}"
                )
            serialized[key] = _jsonable(item, f"{path}[{key!r}]")
        return serialized
    if isinstance(value, (list, tuple)):
        return [_jsonable(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain a finite number")
        return value
    raise TypeError(
        f"{path} contains unsupported JSON type {type(value).__name__}"
    )


def _known_fields(model_type: type[Any], value: Mapping[str, Any]) -> dict[str, Any]:
    names = {item.name for item in fields(model_type)}
    return {key: item for key, item in value.items() if key in names}


def _require_nonempty(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must be non-empty")


def _require_string(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")


def _require_optional_string(value: Any, name: str) -> None:
    if value is not None:
        _require_string(value, name)


def _require_string_list(
    value: Any,
    name: str,
    *,
    non_empty_items: bool = False,
) -> None:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list of strings")
    for index, item in enumerate(value):
        _require_string(item, f"{name}[{index}]")
        if non_empty_items and not item.strip():
            raise ValueError(f"{name}[{index}] must be non-empty")


def _validate_unit_interval(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"{name} must be finite")
    if not 0.0 <= numeric_value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return numeric_value


BucketT = TypeVar("BucketT")


def _bucket_from_dict(
    value: BucketT | Mapping[str, Any] | None,
    bucket_type: type[BucketT],
) -> BucketT:
    if isinstance(value, bucket_type):
        return value
    if value is None:
        return bucket_type()  # type: ignore[call-arg]
    if not isinstance(value, Mapping):
        raise TypeError(f"{bucket_type.__name__} must be a mapping")
    return bucket_type(**_known_fields(bucket_type, value))  # type: ignore[arg-type]


@dataclass
class PreferenceMemory:
    preferences: list[str] = field(default_factory=list)
    habits: list[str] = field(default_factory=list)
    language: str | None = None
    response_style: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _require_string_list(self.preferences, "preferences")
        _require_string_list(self.habits, "habits")
        _require_optional_string(self.language, "language")
        _require_string_list(self.response_style, "response_style")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PreferenceMemory:
        if not isinstance(value, Mapping):
            raise TypeError("PreferenceMemory.from_dict expects a mapping")
        return cls(**_known_fields(cls, value))


@dataclass
class ProjectMemory:
    facts: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    direction: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _require_string_list(self.facts, "facts")
        _require_string_list(self.constraints, "constraints")
        _require_string_list(self.decisions, "decisions")
        _require_string_list(self.direction, "direction")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ProjectMemory:
        if not isinstance(value, Mapping):
            raise TypeError("ProjectMemory.from_dict expects a mapping")
        return cls(**_known_fields(cls, value))


@dataclass
class TaskMemory:
    active_tasks: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    status: str | None = None
    next_actions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _require_string_list(self.active_tasks, "active_tasks")
        _require_string_list(self.milestones, "milestones")
        _require_optional_string(self.status, "status")
        _require_string_list(self.next_actions, "next_actions")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TaskMemory:
        if not isinstance(value, Mapping):
            raise TypeError("TaskMemory.from_dict expects a mapping")
        return cls(**_known_fields(cls, value))


@dataclass
class EpisodeMemory:
    user_input: str = ""
    assistant_response: str = ""
    event: str = "user_assistant_exchange"
    actions: list[str] = field(default_factory=list)
    outcome: str | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _require_string(self.user_input, "user_input")
        _require_string(self.assistant_response, "assistant_response")
        _require_string(self.event, "event")
        _require_string_list(self.actions, "actions")
        _require_optional_string(self.outcome, "outcome")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EpisodeMemory:
        if not isinstance(value, Mapping):
            raise TypeError("EpisodeMemory.from_dict expects a mapping")
        return cls(**_known_fields(cls, value))


@dataclass
class MemoryNode:
    user_input: str
    assistant_response: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    preference_memory: PreferenceMemory = field(default_factory=PreferenceMemory)
    project_memory: ProjectMemory = field(default_factory=ProjectMemory)
    task_memory: TaskMemory = field(default_factory=TaskMemory)
    episode_memory: EpisodeMemory = field(default_factory=EpisodeMemory)
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    confidence: float = 0.5
    created_at: str = field(default_factory=_utc_now)
    session: str | None = None
    session_id: str | None = None
    source: str = "local"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.id, "id")
        _require_string(self.user_input, "user_input")
        _require_string(self.assistant_response, "assistant_response")
        _require_string(self.summary, "summary")
        _require_string(self.created_at, "created_at")
        _require_optional_string(self.session, "session")
        _require_optional_string(self.session_id, "session_id")
        _require_string(self.source, "source")
        _require_string_list(self.tags, "tags", non_empty_items=True)
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")
        for name, bucket_type in (
            ("preference_memory", PreferenceMemory),
            ("project_memory", ProjectMemory),
            ("task_memory", TaskMemory),
            ("episode_memory", EpisodeMemory),
        ):
            bucket = getattr(self, name)
            if not isinstance(bucket, bucket_type):
                raise TypeError(f"{name} must be {bucket_type.__name__}")
            bucket.validate()
        self.importance = _validate_unit_interval(self.importance, "importance")
        self.confidence = _validate_unit_interval(self.confidence, "confidence")
        if self.session is not None and self.session_id is not None:
            if self.session != self.session_id:
                raise ValueError("session and session_id must match")
        elif self.session is None:
            self.session = self.session_id
        elif self.session_id is None:
            self.session_id = self.session

    def to_dict(self) -> dict[str, Any]:
        data = _jsonable(self)
        data.pop("session_id", None)
        data["session"] = self.session
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> MemoryNode:
        data = dict(value)
        data["preference_memory"] = _bucket_from_dict(
            data.get("preference_memory"),
            PreferenceMemory,
        )
        data["project_memory"] = _bucket_from_dict(
            data.get("project_memory"),
            ProjectMemory,
        )
        data["task_memory"] = _bucket_from_dict(
            data.get("task_memory"),
            TaskMemory,
        )
        data["episode_memory"] = _bucket_from_dict(
            data.get("episode_memory"),
            EpisodeMemory,
        )
        return cls(**_known_fields(cls, data))

    @classmethod
    def from_json(cls, value: str) -> MemoryNode:
        return cls.from_dict(json.loads(value))


@dataclass
class MemoryEdge:
    from_node: str
    to_node: str
    relation: str
    weight: float = 1.0
    reason: str = ""
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.from_node, "from_node")
        _require_nonempty(self.to_node, "to_node")
        self.weight = _validate_unit_interval(self.weight, "weight")
        if not isinstance(self.relation, str):
            raise TypeError("relation must be a string")
        if self.relation not in VALID_MEMORY_RELATIONS:
            allowed = ", ".join(sorted(VALID_MEMORY_RELATIONS))
            raise ValueError(f"relation must be one of: {allowed}")

    @property
    def from_id(self) -> str:
        return self.from_node

    @property
    def to_id(self) -> str:
        return self.to_node

    @property
    def from_(self) -> str:
        return self.from_node

    @property
    def to(self) -> str:
        return self.to_node

    def to_dict(self) -> dict[str, Any]:
        data = _jsonable(self)
        data["from"] = data.pop("from_node")
        data["to"] = data.pop("to_node")
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> MemoryEdge:
        data = dict(value)
        if "from" in data:
            data["from_node"] = data.pop("from")
        elif "from_id" in data:
            data["from_node"] = data["from_id"]
        if "to" in data:
            data["to_node"] = data.pop("to")
        elif "to_id" in data:
            data["to_node"] = data["to_id"]
        data.pop("from_id", None)
        data.pop("to_id", None)
        return cls(**_known_fields(cls, data))

    @classmethod
    def from_json(cls, value: str) -> MemoryEdge:
        return cls.from_dict(json.loads(value))
