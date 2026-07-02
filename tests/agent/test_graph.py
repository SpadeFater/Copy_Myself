from copy_myself.agent.graph import build_graph, run_agent


def test_build_graph_returns_compiled_graph() -> None:
    graph = build_graph()

    assert graph is not None


def test_run_agent_returns_response_for_chat() -> None:
    state = run_agent("帮我整理任务")

    assert state["intent"] == "chat"
    assert state["response"]


def test_run_agent_routes_health_check_to_tool() -> None:
    state = run_agent("health check")

    assert state["intent"] == "health_check"
    assert state["tool_result"] == {"status": "ok", "source": "agent"}
