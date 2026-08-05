from __future__ import annotations

import json
import re
from datetime import datetime

from agent.state import ButlerState
from agent.tool_execution import ToolExecutionCoordinator
from llm.base import ChatMessage, ModelClient
from memory.base import MemoryStore
from langgraph.errors import GraphInterrupt

LOCATION_TIMEZONES = {"beijing": "Asia/Shanghai", "new york": "America/New_York", "los angeles": "America/Los_Angeles", "london": "Europe/London", "tokyo": "Asia/Tokyo"}


def _extract_time_arguments(text: str) -> dict[str, str]:
    match = re.search(r"\b([A-Za-z]+(?:[_-][A-Za-z]+)?/[A-Za-z_+-]+)\b", text)
    if match:
        return {"timezone": match.group(1)}
    lowered = text.casefold()
    for location in sorted(LOCATION_TIMEZONES, key=len, reverse=True):
        if location in lowered:
            return {"location": location}
    return {}


def _extract_filesystem_arguments(text: str) -> dict[str, str] | None:
    lowered = text.casefold()
    if not any(marker in lowered for marker in ("list files", "show files", "list directory", "show directory", "project structure", "workspace structure", "列出文件", "查看目录", "项目结构")):
        return None
    match = re.search(r"\b(?:in|under|inside)\s+([^\s]+)", text, re.IGNORECASE)
    return {"action": "list", "path": match.group(1).strip("\"'`") if match else "."}


def classify_intent(state: ButlerState) -> ButlerState:
    text = state["user_input"].strip()
    lowered = text.casefold()
    if any(marker in lowered for marker in ("what time", "current time", "time now", "现在几点", "当前时间", "现在时间")):
        state["intent"] = "time_lookup"
        state["tool_name"] = "builtin__getTime"
        state["tool_arguments"] = _extract_time_arguments(text)
    elif arguments := _extract_filesystem_arguments(text):
        state["intent"] = "chat"
        state["tool_name"] = "builtin__filesystem"
        state["tool_arguments"] = arguments
    else:
        state["intent"] = "chat"
        state["tool_name"] = None
        state["tool_arguments"] = {}
    return state


def load_memory_context(state: ButlerState, memory: MemoryStore) -> ButlerState:
    if hasattr(memory, "retrieve_context"):
        context = memory.retrieve_context(state["user_input"], limit=5)
        state["memory_context"] = [context] if context else []
    else:
        state["memory_context"] = memory.search(state["user_input"], limit=5)
    return state


def save_memory_context(state: ButlerState, memory: MemoryStore) -> ButlerState:
    if state.get("response"):
        if hasattr(memory, "save_exchange"):
            memory.save_exchange(state["user_input"], state["response"] or "", source="agent")
        else:
            memory.save("user", state["user_input"])
            memory.save("assistant", state["response"] or "")
    return state


def _model_messages(state: ButlerState) -> list[ChatMessage]:
    messages: list[ChatMessage] = [{"role": "system", "content": "You are Copy_Myself, a concise local-first personal assistant. Answer in the user's language."}]
    if state["memory_context"]:
        messages.append({"role": "system", "content": "Relevant memory:\n" + "\n".join(state["memory_context"])})
    messages.append({"role": "user", "content": state["user_input"]})
    return messages


async def select_model_tool(state: ButlerState, model_client: ModelClient | None, coordinator: ToolExecutionCoordinator) -> ButlerState:
    if state.get("tool_name") is not None or model_client is None or not hasattr(model_client, "decide"):
        return state
    definitions = await coordinator.definitions()
    state["tool_definitions"] = definitions
    try:
        decision = model_client.decide(_model_messages(state), definitions)
    except Exception:
        return state
    call = decision.get("tool_call")
    if call:
        name = call["name"]
        if "__" not in name and any(item["function"]["name"] == f"builtin__{name}" for item in definitions):
            name = f"builtin__{name}"
        state["tool_name"] = name
        state["tool_arguments"] = call.get("arguments", {})
    elif decision.get("content"):
        state["response"] = decision["content"]
    return state


async def run_selected_tool(state: ButlerState, coordinator: ToolExecutionCoordinator) -> ButlerState:
    if state.get("tool_name") is None:
        return state
    try:
        payload = await coordinator.execute(state["tool_name"], state.get("tool_arguments", {}), state["session_id"])
        if payload.get("code") == "ok":
            state["tool_result"] = payload.get("result")
            state["error"] = None
        else:
            state["error"] = payload.get("code", "tool_call_failed")
    except GraphInterrupt:
        raise
    except Exception as exc:
        state["error"] = str(exc)
    return state


def create_response(state: ButlerState, model_client: ModelClient | None = None) -> ButlerState:
    if state.get("response"):
        return state
    if state.get("error"):
        state["response"] = f"Unable to complete the request: {state['error']}"
    elif state.get("tool_result"):
        if model_client is not None:
            messages = _model_messages(state)
            messages.append({"role": "system", "content": f"Tool result from {state.get('tool_name')}:\n{json.dumps(state['tool_result'], ensure_ascii=False, default=str)}"})
            try:
                state["response"] = model_client.complete(messages)
                return state
            except Exception as exc:
                state["error"] = None
        if state.get("tool_name") == "builtin__getTime":
            raw = str(state["tool_result"].get("time", ""))
            try:
                raw = datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
            state["response"] = f"Current time: {raw}\nTimezone: {state['tool_result'].get('timezone', 'local')}"
        else:
            state["response"] = str(state["tool_result"])
    elif model_client is not None:
        try:
            state["response"] = model_client.complete(_model_messages(state))
        except Exception as exc:
            state["error"] = str(exc)
            state["response"] = "The model is unavailable; local chat remains available."
    else:
        state["response"] = "I received your request."
    return state
