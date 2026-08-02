import json
import math

import pytest
from copy_myself.memory import (
    EpisodeMemory,
    MemoryEdge,
    MemoryNode,
    PreferenceMemory,
    ProjectMemory,
    TaskMemory,
)


def test_memory_node_preserves_exchange_and_serializes_buckets() -> None:
    node = MemoryNode(
        user_input="Use concise Chinese replies.",
        assistant_response="Understood.",
        preference_memory=PreferenceMemory(
            language="Chinese",
            response_style=["concise"],
        ),
        project_memory=ProjectMemory(
            facts=["Copy_Myself uses LangGraph"],
            constraints=["Keep the graph boundary"],
        ),
        task_memory=TaskMemory(
            status="in_progress",
            next_actions=["Add SQLite persistence"],
        ),
        episode_memory=EpisodeMemory(
            event="Preference captured",
            outcome="Assistant acknowledged it",
        ),
        summary="User requested concise Chinese replies.",
        tags=["preference", "project", "task"],
        importance=0.8,
        confidence=0.95,
        session_id="session-1",
        source="cli",
    )

    serialized = node.to_dict()

    assert serialized["user_input"] == "Use concise Chinese replies."
    assert serialized["assistant_response"] == "Understood."
    assert serialized["preference_memory"]["language"] == "Chinese"
    assert serialized["project_memory"]["constraints"] == ["Keep the graph boundary"]
    assert serialized["task_memory"]["next_actions"] == ["Add SQLite persistence"]
    assert serialized["episode_memory"]["event"] == "Preference captured"
    assert json.loads(json.dumps(serialized)) == serialized


def test_memory_node_round_trips_from_serialized_data() -> None:
    original = MemoryNode(
        user_input="Remember the deadline.",
        assistant_response="I will track it.",
        tags=["task"],
        session="session-2",
        source="test",
    )

    serialized = json.loads(original.to_json())
    restored = MemoryNode.from_json(original.to_json())

    assert serialized["session"] == "session-2"
    assert serialized["source"] == "test"
    assert "session_id" not in serialized
    assert restored == original


def test_memory_edge_json_uses_from_and_to_and_round_trips() -> None:
    edge = MemoryEdge(
        from_node="node-a",
        to_node="node-b",
        relation="same_task",
        weight=0.75,
        reason="Both exchanges discuss the release task.",
        created_at="2026-07-25T12:00:00+08:00",
    )

    serialized = json.loads(edge.to_json())

    assert serialized == {
        "from": "node-a",
        "to": "node-b",
        "relation": "same_task",
        "weight": 0.75,
        "reason": "Both exchanges discuss the release task.",
        "created_at": "2026-07-25T12:00:00+08:00",
    }
    assert edge.from_ == "node-a"
    assert edge.to == "node-b"
    assert MemoryEdge.from_json(edge.to_json()) == edge


@pytest.mark.parametrize(
    ("metadata", "error_type", "message"),
    [
        ({"unsupported": {1, 2}}, TypeError, "metadata"),
        ({"nan": math.nan}, ValueError, "finite"),
        ({"positive_infinity": math.inf}, ValueError, "finite"),
        ({"negative_infinity": -math.inf}, ValueError, "finite"),
    ],
)
def test_memory_node_rejects_non_standard_metadata_json(
    metadata: dict[str, object],
    error_type: type[Exception],
    message: str,
) -> None:
    node = MemoryNode(
        user_input="input",
        assistant_response="response",
        metadata=metadata,
    )

    with pytest.raises(error_type, match=message):
        node.to_json()


def test_from_dict_ignores_unknown_fields_and_supports_legacy_edge_keys() -> None:
    node = MemoryNode.from_dict(
        {
            "id": "node-1",
            "user_input": "input",
            "assistant_response": "response",
            "session": "session-1",
            "source": "test",
            "future_field": "ignore me",
        }
    )
    edge_from_ids = MemoryEdge.from_dict(
        {
            "from_id": "node-a",
            "to_id": "node-b",
            "relation": "support",
            "unknown": "ignore me",
        }
    )
    edge_from_nodes = MemoryEdge.from_dict(
        {
            "from_node": "node-c",
            "to_node": "node-d",
            "relation": "same_task",
            "unknown": "ignore me",
        }
    )

    assert node.session == "session-1"
    assert edge_from_ids.from_ == "node-a"
    assert edge_from_ids.to == "node-b"
    assert edge_from_nodes.from_ == "node-c"
    assert edge_from_nodes.to == "node-d"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": ""},
        {"id": "   "},
        {"importance": -0.01},
        {"importance": 1.01},
        {"importance": math.nan},
        {"confidence": -0.01},
        {"confidence": 1.01},
        {"confidence": math.inf},
    ],
)
def test_memory_node_validates_identity_and_scores(kwargs: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError)):
        MemoryNode(
            user_input="input",
            assistant_response="response",
            **kwargs,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"from_node": "", "to_node": "node-b"},
        {"from_node": "node-a", "to_node": " "},
        {"weight": -0.01},
        {"weight": 1.01},
        {"weight": math.nan},
        {"relation": "unknown_relation"},
    ],
)
def test_memory_edge_validates_endpoints_weight_and_relation(
    kwargs: dict[str, object],
) -> None:
    params: dict[str, object] = {
        "from_node": "node-a",
        "to_node": "node-b",
        "relation": "support",
    }
    params.update(kwargs)

    with pytest.raises((TypeError, ValueError)):
        MemoryEdge(**params)


@pytest.mark.parametrize(
    ("bucket_type", "payload", "expected_field", "expected_value", "default_field"),
    [
        (
            PreferenceMemory,
            {"language": "Chinese", "unknown": "ignore"},
            "language",
            "Chinese",
            "preferences",
        ),
        (
            ProjectMemory,
            {"facts": ["uses SQLite"], "unknown": "ignore"},
            "facts",
            ["uses SQLite"],
            "constraints",
        ),
        (
            TaskMemory,
            {"status": "pending", "unknown": "ignore"},
            "status",
            "pending",
            "next_actions",
        ),
        (
            EpisodeMemory,
            {"event": "exchange", "unknown": "ignore"},
            "event",
            "exchange",
            "actions",
        ),
    ],
)
def test_memory_buckets_from_dict_ignore_unknown_fields_and_keep_defaults(
    bucket_type: type[object],
    payload: dict[str, object],
    expected_field: str,
    expected_value: object,
    default_field: str,
) -> None:
    bucket = bucket_type.from_dict(payload)  # type: ignore[attr-defined]

    assert getattr(bucket, expected_field) == expected_value
    assert getattr(bucket, default_field) == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user_input": None},
        {"assistant_response": 123},
        {"summary": []},
        {"tags": "task"},
        {"tags": ["task", 1]},
        {"preference_memory": {}},
        {"project_memory": []},
        {"task_memory": {"status": "pending"}},
        {"episode_memory": None},
    ],
)
def test_memory_node_rejects_invalid_field_and_bucket_shapes(
    kwargs: dict[str, object],
) -> None:
    params: dict[str, object] = {
        "user_input": "input",
        "assistant_response": "response",
    }
    params.update(kwargs)

    with pytest.raises((TypeError, ValueError)):
        MemoryNode(**params)


def test_memory_node_rejects_malformed_nested_bucket_fields() -> None:
    with pytest.raises((TypeError, ValueError)):
        MemoryNode(
            user_input="input",
            assistant_response="response",
            preference_memory=PreferenceMemory(preferences="not-a-list"),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"created_at": 123},
        {"session": 123},
        {"session_id": object()},
        {"source": None},
    ],
)
def test_memory_node_rejects_invalid_metadata_field_types(
    kwargs: dict[str, object],
) -> None:
    params: dict[str, object] = {
        "user_input": "input",
        "assistant_response": "response",
    }
    params.update(kwargs)

    with pytest.raises(TypeError):
        MemoryNode(**params)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"created_at": 123},
        {"session": 123},
        {"session_id": object()},
        {"source": None},
    ],
)
def test_memory_node_from_dict_rejects_invalid_metadata_field_types(
    kwargs: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "id": "node-1",
        "user_input": "input",
        "assistant_response": "response",
    }
    payload.update(kwargs)

    with pytest.raises(TypeError):
        MemoryNode.from_dict(payload)


def test_memory_node_normalizes_equal_session_aliases() -> None:
    node = MemoryNode(
        user_input="input",
        assistant_response="response",
        session="session-1",
        session_id="session-1",
    )

    assert node.session == "session-1"
    assert node.session_id == "session-1"
    assert node.to_dict()["session"] == "session-1"


def test_memory_node_rejects_conflicting_session_aliases() -> None:
    with pytest.raises(ValueError, match="session"):
        MemoryNode(
            user_input="input",
            assistant_response="response",
            session="session-a",
            session_id="session-b",
        )


def test_memory_node_from_dict_rejects_conflicting_session_aliases() -> None:
    with pytest.raises(ValueError, match="session"):
        MemoryNode.from_dict(
            {
                "id": "node-1",
                "user_input": "input",
                "assistant_response": "response",
                "session": "session-a",
                "session_id": "session-b",
            }
        )
