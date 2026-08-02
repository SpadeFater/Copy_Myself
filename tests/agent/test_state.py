from copy_myself.agent.state import create_initial_state


def test_create_initial_state_sets_predictable_defaults() -> None:
    state = create_initial_state("帮我看一下今天要做什么")

    assert state["user_input"] == "帮我看一下今天要做什么"
    assert state["messages"] == []
    assert state["intent"] == "unknown"
    assert state["tool_name"] is None
    assert state["tool_arguments"] == {}
    assert state["tool_result"] is None
    assert state["memory_context"] == []
    assert state["response"] is None
    assert state["error"] is None
