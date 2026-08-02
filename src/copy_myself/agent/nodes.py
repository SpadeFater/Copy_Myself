from __future__ import annotations

import json
import re
from datetime import datetime

from copy_myself.agent.state import ButlerState
from copy_myself.llm.base import ChatMessage, ModelClient
from copy_myself.memory.base import MemoryStore
from copy_myself.tools.timetool import LOCATION_TIMEZONES
from copy_myself.tools.registry import ToolRegistry


def _extract_time_arguments(text: str) -> dict[str, str]:
    timezone_match = re.search(
        r"\b([A-Za-z]+(?:[_-][A-Za-z]+)?/[A-Za-z_+-]+)\b",
        text,
    )
    if timezone_match:
        return {"timezone": timezone_match.group(1)}

    lowered = text.casefold()
    for location in sorted(LOCATION_TIMEZONES, key=len, reverse=True):
        if location.casefold() in lowered:
            return {"location": location}
    return {}


def _extract_filesystem_arguments(text: str) -> dict[str, str] | None:
    lowered = text.casefold()
    list_markers = (
        "list files",
        "show files",
        "list directory",
        "show directory",
        "directory listing",
        "project structure",
        "workspace structure",
        "列出文件",
        "查看文件",
        "查看目录",
        "项目结构",
        "工作区结构",
        "有哪些文件",
    )
    if not any(marker in lowered for marker in list_markers):
        return None

    path = "."
    path_match = re.search(r"\b(?:in|under|inside)\s+([^\s]+)", text, re.IGNORECASE)
    if path_match:
        path = path_match.group(1).strip("\"'`")
    return {"action": "list", "path": path or "."}


def classify_intent(state: ButlerState) -> ButlerState:
    text = state["user_input"].strip()
    lowered = text.casefold()
    is_time_request = any(
        marker in lowered
        for marker in (
            "what time",
            "current time",
            "time now",
            "现在几点",
            "几点了",
            "当前时间",
            "现在时间",
        )
    )
    if is_time_request:
        state["intent"] = "time_lookup"
        state["tool_name"] = "getTime"
        state["tool_arguments"] = _extract_time_arguments(text)
    elif filesystem_arguments := _extract_filesystem_arguments(text):
        state["intent"] = "chat"
        state["tool_name"] = "filesystem"
        state["tool_arguments"] = filesystem_arguments
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
            memory.save_exchange(
                state["user_input"],
                state["response"] or "",
                source="agent",
            )
        else:
            memory.save("user", state["user_input"])
            memory.save("assistant", state["response"])
    return state


def run_selected_tool(state: ButlerState, registry: ToolRegistry) -> ButlerState:
    tool_name = state.get("tool_name")
    if tool_name is None:
        return state

    arguments = {"source": "agent", **state.get("tool_arguments", {})}
    result = registry.run(tool_name, arguments)
    if result.ok:
        state["tool_result"] = result.data
        state["error"] = None
    else:
        state["tool_result"] = None
        state["error"] = result.error
    return state


def _build_model_messages(state: ButlerState) -> list[ChatMessage]:
    messages: list[ChatMessage] = [
        {
            "role": "system",
            "content": (
                "You are Copy_Myself, a local-first personal butler agent. "
                "Answer in the user's language, stay concise, and use memory when relevant."
            ),
        }
    ]
    if state["memory_context"]:
        messages.append(
            {
                "role": "system",
                "content": "Relevant memory:\n" + "\n".join(state["memory_context"]),
            }
        )
    messages.append({"role": "user", "content": state["user_input"]})
    return messages


def _build_tool_result_messages(state: ButlerState) -> list[ChatMessage]:
    messages = _build_model_messages(state)
    tool_payload = json.dumps(state.get("tool_result") or {}, ensure_ascii=False, default=str)
    messages.append(
        {
            "role": "system",
            "content": (
                f"Tool result from {state.get('tool_name')}:\n{tool_payload}\n\n"
                "Use this tool result to answer the user's original request. "
                "Do not expose raw tool JSON unless the user asks for raw data."
            ),
        }
    )
    return messages


def _format_tool_response(state: ButlerState) -> str:
    tool_result = state["tool_result"] or {}
    if state.get("tool_name") == "getTime":
        raw_time = str(tool_result.get("time", ""))
        try:
            formatted_time = datetime.fromisoformat(raw_time).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted_time = raw_time
        return (
            "好的，我已经帮你查好了。\n\n"
            f"当前时间：{formatted_time}\n"
            f"时区：{tool_result.get('timezone', 'local')}"
        )
    return f"好的，工具调用已经完成。\n\n{tool_result}"


def create_response(
    state: ButlerState,
    model_client: ModelClient | None = None,
    registry: ToolRegistry | None = None,
) -> ButlerState:
    if state.get("error"):
        state["response"] = f"暂时无法完成这个请求：{state['error']}"
    elif state.get("tool_result"):
        state["response"] = _format_tool_response(state)
    elif state.get("intent") == "chat" and model_client is not None:
        try:
            messages = _build_model_messages(state)
            if registry is not None and hasattr(model_client, "decide"):
                decision = model_client.decide(messages, registry.definitions())
                tool_call = decision.get("tool_call")
                if tool_call is not None:
                    state["tool_name"] = tool_call["name"]
                    state["tool_arguments"] = tool_call.get("arguments", {})
                    result = registry.run(
                        state["tool_name"],
                        {"source": "agent", **state["tool_arguments"]},
                    )
                    if result.ok:
                        state["tool_result"] = result.data
                        state["error"] = None
                        state["response"] = model_client.complete(_build_tool_result_messages(state))
                    else:
                        state["tool_result"] = None
                        state["error"] = result.error
                        state["response"] = f"暂时无法完成这个请求：{result.error}"
                    return state
                if decision.get("content"):
                    state["response"] = decision["content"]
                    return state
            state["response"] = model_client.complete(messages)
        except Exception as exc:
            state["error"] = str(exc)
            state["response"] = "模型连接失败，已回退到本地响应。"
    else:
        state["response"] = (
            "我已收到你的请求。当前项目框架已预留意图识别、工具调用和记忆接口，"
            "后续可以在这些接口上继续扩展具体个人管家能力。"
        )
    return state
