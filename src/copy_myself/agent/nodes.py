from __future__ import annotations

import json
from typing import Any

from copy_myself.agent.state import ButlerState
from copy_myself.memory.base import MemoryStore
from copy_myself.model_adapter import ChatResponder, LocalFallbackResponder
from copy_myself.tools.registry import ToolRegistry


def classify_intent(
    state: ButlerState,
    registry: ToolRegistry | None = None,
    responder: ChatResponder | None = None,
) -> ButlerState:
    text = state["user_input"].strip().lower()
    if text in {"health", "health check", "健康检查"} or "健康检查" in text:
        state["intent"] = "health_check"
        state["tool_name"] = "health"
        state["tool_arguments"] = {}
        return state

    if registry is not None and responder is not None:
        selected = _select_tool_with_model(state["user_input"], registry, responder)
        if selected is not None:
            state["intent"] = "tool"
            state["tool_name"] = selected["tool_name"]
            state["tool_arguments"] = selected["arguments"]
            return state

    state["intent"] = "chat"
    state["tool_name"] = None
    state["tool_arguments"] = {}
    return state


def _select_tool_with_model(
    user_input: str,
    registry: ToolRegistry,
    responder: ChatResponder,
) -> dict[str, Any] | None:
    catalog = registry.catalog()
    if not catalog:
        return None

    tool_lines = "\n".join(f"- {item.name}: {item.description}" for item in catalog)
    prompt = (
        "Choose the best tool for the user request from this tool catalog.\n"
        "Return only JSON with this shape: "
        '{"tool_name": "name-or-null", "arguments": {}}.\n'
        'If no tool fits, return {"tool_name": null, "arguments": {}}.\n\n'
        f"Tool catalog:\n{tool_lines}\n\n"
        f"User request:\n{user_input}"
    )
    try:
        payload = json.loads(responder.generate(prompt, []))
    except Exception:
        return None

    tool_name = payload.get("tool_name")
    arguments = payload.get("arguments", {})
    if not isinstance(tool_name, str) or tool_name not in registry.names():
        return None
    if not isinstance(arguments, dict):
        arguments = {}
    return {"tool_name": tool_name, "arguments": arguments}


def load_memory_context(state: ButlerState, memory: MemoryStore) -> ButlerState:
    brief_context_getter = getattr(memory, "get_brief_context", None)
    if callable(brief_context_getter):
        try:
            brief_context = brief_context_getter(state["user_input"])
        except TypeError:
            brief_context = brief_context_getter()
        if brief_context:
            state["memory_context"] = brief_context
            return state

    state["memory_context"] = memory.search(state["user_input"], limit=5)
    return state


def run_selected_tool(state: ButlerState, registry: ToolRegistry) -> ButlerState:
    tool_name = state.get("tool_name")
    if tool_name is None:
        return state

    arguments = {"source": "agent"}
    arguments.update(state.get("tool_arguments", {}))
    result = registry.run(tool_name, arguments)
    if result.ok:
        state["tool_result"] = result.data
        state["error"] = None
    else:
        state["tool_result"] = None
        state["error"] = result.error
    return state


def create_response(
    state: ButlerState,
    responder: ChatResponder | None = None,
) -> ButlerState:
    if state.get("error"):
        state["response"] = f"暂时无法完成这个请求：{state['error']}"
    elif state.get("tool_result"):
        state["response"] = f"工具调用完成：{state['tool_result']}"
    else:
        chat_responder = responder or LocalFallbackResponder()
        try:
            state["response"] = chat_responder.generate(
                state["user_input"],
                state.get("memory_context", []),
            )
        except Exception as exc:
            state["error"] = str(exc)
            state["response"] = f"模型调用失败：{exc}"
    return state
