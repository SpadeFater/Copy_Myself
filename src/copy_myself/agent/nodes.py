from __future__ import annotations

from copy_myself.agent.state import ButlerState
from copy_myself.llm.base import ChatMessage, ModelClient
from copy_myself.memory.base import MemoryStore
from copy_myself.tools.registry import ToolRegistry


def classify_intent(state: ButlerState) -> ButlerState:
    text = state["user_input"].strip().lower()
    if text in {"health", "health check", "健康检查"} or "健康检查" in text:
        state["intent"] = "health_check"
        state["tool_name"] = "health"
    else:
        state["intent"] = "chat"
        state["tool_name"] = None
    return state


def load_memory_context(state: ButlerState, memory: MemoryStore) -> ButlerState:
    state["memory_context"] = memory.search(state["user_input"], limit=5)
    return state


def run_selected_tool(state: ButlerState, registry: ToolRegistry) -> ButlerState:
    tool_name = state.get("tool_name")
    if tool_name is None:
        return state

    result = registry.run(tool_name, {"source": "agent"})
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


def create_response(state: ButlerState, model_client: ModelClient | None = None) -> ButlerState:
    if state.get("error"):
        state["response"] = f"暂时无法完成这个请求：{state['error']}"
    elif state.get("tool_result"):
        state["response"] = f"工具调用完成：{state['tool_result']}"
    elif state.get("intent") == "chat" and model_client is not None:
        try:
            state["response"] = model_client.complete(_build_model_messages(state))
        except Exception as exc:
            state["error"] = str(exc)
            state["response"] = "模型连接失败，已回退到本地响应。"
    else:
        state["response"] = (
            "我已收到你的请求。当前项目框架已预留意图识别、工具调用和记忆接口，"
            "后续可以在这些接口上继续扩展具体个人管家能力。"
        )
    return state
