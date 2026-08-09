from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import ModelProviderSettings
from llm.base import ChatMessage, ModelClient, ToolDecision


def _model_paths(base_url: str) -> tuple[str, str]:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return (f"{root}/models", f"{root[:-3]}/models")
    return (f"{root}/v1/models", f"{root}/models")


def _extract_model_names(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ()
    raw_models = payload.get("data", payload.get("models", ()))
    if not isinstance(raw_models, list):
        return ()
    models: list[str] = []
    seen: set[str] = set()
    for item in raw_models:
        if isinstance(item, str):
            candidate = item.strip()
        elif isinstance(item, dict):
            raw_name = item.get("id", item.get("name", ""))
            candidate = raw_name.strip() if isinstance(raw_name, str) else ""
        else:
            candidate = ""
        if candidate and candidate not in seen:
            models.append(candidate)
            seen.add(candidate)
    return tuple(models)


def fetch_available_models(provider: ModelProviderSettings, timeout: float = 30.0) -> tuple[str, ...]:
    last_error: Exception | None = None
    for url in _model_paths(provider.base_url):
        request = Request(url, headers=OpenAICompatibleClient(provider)._headers(), method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            models = _extract_model_names(json.loads(body))
            if not models:
                raise RuntimeError("Model list response did not contain usable model names.")
            return models
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Unable to fetch model list: {last_error}") from last_error


@dataclass
class OpenAICompatibleClient(ModelClient):
    provider: ModelProviderSettings
    timeout: float = 30.0
    extra_headers: dict[str, str] = field(default_factory=dict)

    def complete(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self.provider.model_name,
            "messages": messages,
            "temperature": 0.2,
        }
        request = Request(
            f"{self.provider.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(str(exc)) from exc

        data: Any = json.loads(body)
        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise RuntimeError("Model response missing choices.")
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Model response missing assistant content.")
        return content.strip()

    def decide(self, messages: list[ChatMessage], tools: list[dict[str, Any]]) -> ToolDecision:
        payload = {
            "model": self.provider.model_name,
            "messages": messages,
            "temperature": 0.2,
            "tools": tools,
            "tool_choice": "auto",
        }
        message = self._request_message(payload)
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
        if isinstance(tool_calls, list) and tool_calls:
            function = tool_calls[0].get("function", {}) if isinstance(tool_calls[0], dict) else {}
            name = function.get("name") if isinstance(function, dict) else None
            raw_arguments = function.get("arguments", "{}") if isinstance(function, dict) else "{}"
            if not isinstance(name, str) or not name:
                raise RuntimeError("Model tool call missing function name.")
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            except json.JSONDecodeError as exc:
                raise RuntimeError("Model tool call arguments are not valid JSON.") from exc
            if not isinstance(arguments, dict):
                raise RuntimeError("Model tool call arguments must be an object.")
            return {"tool_call": {"name": name, "arguments": arguments}, "content": None}

        content = message.get("content") if isinstance(message, dict) else None
        return {"tool_call": None, "content": content.strip() if isinstance(content, str) and content.strip() else None}

    def _request_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.provider.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(str(exc)) from exc

        data: Any = json.loads(body)
        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise RuntimeError("Model response missing choices.")
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        if not isinstance(message, dict):
            raise RuntimeError("Model response missing message.")
        return message

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.provider.api_key:
            headers["Authorization"] = f"Bearer {self.provider.api_key}"
        headers.update(self.provider.headers)
        headers.update(self.extra_headers)
        return headers
