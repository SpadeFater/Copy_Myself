from memory import (
    EpisodeMemory,
    PreferenceMemory,
    ProjectMemory,
    TaskMemory,
    extract_memory,
    extract_memory_node,
)


def test_extract_memory_identifies_preference_project_and_task_buckets() -> None:
    user_input = (
        "Please answer in concise Chinese. The Copy_Myself project uses LangGraph "
        "and must keep the agent boundary. The task is in progress; next step is "
        "to add SQLite persistence."
    )
    assistant_response = "Understood. I will keep replies concise and add the persistence step."

    extracted = extract_memory(user_input, assistant_response)

    assert isinstance(extracted.preference_memory, PreferenceMemory)
    assert extracted.preference_memory.language == "Chinese"
    assert "concise" in extracted.preference_memory.response_style
    assert isinstance(extracted.project_memory, ProjectMemory)
    assert "Copy_Myself project uses LangGraph" in extracted.project_memory.facts
    assert "must keep the agent boundary" in extracted.project_memory.constraints
    assert isinstance(extracted.task_memory, TaskMemory)
    assert extracted.task_memory.status == "in_progress"
    assert "add SQLite persistence" in extracted.task_memory.next_actions
    assert isinstance(extracted.episode_memory, EpisodeMemory)
    assert extracted.episode_memory.user_input == user_input
    assert extracted.episode_memory.assistant_response == assistant_response


def test_extract_memory_is_deterministic_without_external_configuration() -> None:
    user_input = "I prefer short answers. Next step: review the task."
    assistant_response = "Done. The task is now in progress."

    first = extract_memory(user_input, assistant_response)
    second = extract_memory(user_input, assistant_response)

    assert first == second
    assert first.tags == ["episode", "preference", "task", "review"]
    assert 0.0 <= first.importance <= 1.0
    assert 0.0 <= first.confidence <= 1.0


def test_extract_memory_node_preserves_raw_exchange_and_metadata() -> None:
    node = extract_memory_node(
        "请用中文回答，并记住这个项目必须本地优先。",
        "好的，我会遵循这个约束。",
        session_id="session-3",
        source="test",
    )

    assert node.user_input == "请用中文回答，并记住这个项目必须本地优先。"
    assert node.assistant_response == "好的，我会遵循这个约束。"
    assert node.session_id == "session-3"
    assert node.source == "test"
    assert node.episode_memory.user_input == node.user_input
    assert node.episode_memory.assistant_response == node.assistant_response


def test_extract_memory_node_uses_assistant_response_for_all_structured_buckets() -> None:
    node = extract_memory_node(
        "Please record this exchange.",
        (
            "I prefer detailed responses. The Copy_Myself project uses SQLite and "
            "must remain local-first. The task is completed; next step is archive notes."
        ),
        session="session-assistant",
        source="assistant-test",
    )

    assert node.preference_memory.response_style == ["detailed"]
    assert "Copy_Myself project uses SQLite" in node.project_memory.facts
    assert "must remain local-first" in node.project_memory.constraints
    assert node.task_memory.status == "completed"
    assert node.task_memory.next_actions == ["archive notes"]


def test_extract_memory_node_includes_summary_scores_tags_and_source() -> None:
    node = extract_memory_node(
        "Please answer in concise Chinese.",
        "The project uses LangGraph. The task is in progress.",
        session="session-metadata",
        source="unit-test",
    )

    assert node.summary
    assert 0.0 <= node.importance <= 1.0
    assert 0.0 <= node.confidence <= 1.0
    assert {"episode", "preference", "project", "task", "chinese", "langgraph"} <= set(node.tags)
    assert node.source == "unit-test"


def test_extract_memory_keeps_all_components_of_project_fact() -> None:
    extracted = extract_memory(
        "The Copy_Myself project uses SQLite and LangGraph.",
        "Recorded.",
    )

    assert extracted.project_memory.facts == [
        "Copy_Myself project uses SQLite and LangGraph"
    ]
