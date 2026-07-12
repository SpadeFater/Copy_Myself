from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator, Protocol
from urllib import request

from copy_myself.config import Settings, load_settings


SYSTEM_PROMPT = "你是用户的专属个人管家，回答要自然、简洁、可执行。"


class ChatResponder(Protocol):
    def generate(self, user_input: str, memory_context: list[str]) -> str:
        """Return a chat response for one user message."""

    def stream(self, user_input: str, memory_context: list[str]) -> Iterator[str]:
        """Yield chat response chunks for one user message."""


class LocalFallbackResponder:
    def generate(self, user_input: str, memory_context: list[str]) -> str:
        memory_hint = f"我参考到这些记忆：{'; '.join(memory_context)}。" if memory_context else ""
        return (
            f"我收到你的消息了：{user_input}。"
            f"{memory_hint}你可以配置大模型 API key 后让我进行真实对话。"
        )

    def stream(self, user_input: str, memory_context: list[str]) -> Iterator[str]:
        for char in self.generate(user_input, memory_context):
            yield char


@dataclass(frozen=True)
class OpenAICompatibleResponder:
    api_key: str
    model_name: str
    base_url: str = "https://api.deepseek.com/v1"
    timeout_seconds: int = 60

    def generate(self, user_input: str, memory_context: list[str]) -> str:
        payload = {
            "model": self.model_name,
            "messages": self._build_messages(user_input, memory_context),
            "temperature": 0.7,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = self._build_request(data)

        with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        if not content:
            raise RuntimeError("Model returned an empty response.")
        return content

    def stream(self, user_input: str, memory_context: list[str]) -> Iterator[str]:
        payload = {
            "model": self.model_name,
            "messages": self._build_messages(user_input, memory_context),
            "temperature": 0.7,
            "stream": True,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = self._build_request(data)

        with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data_line = line.removeprefix("data:").strip()
                if data_line == "[DONE]":
                    break
                payload_chunk = json.loads(data_line)
                content = payload_chunk["choices"][0].get("delta", {}).get("content", "")
                if content:
                    yield content

    def _build_request(self, data: bytes) -> request.Request:
        return request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

    def _build_messages(self, user_input: str, memory_context: list[str]) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if memory_context:
            messages.append(
                {
                    "role": "system",
                    "content": "可参考的用户记忆：\n" + "\n".join(memory_context),
                }
            )
        messages.append({"role": "user", "content": user_input})
        return messages


def build_default_responder(settings: Settings | None = None) -> ChatResponder:
    loaded_settings = settings or load_settings()
    if loaded_settings.api_key:
        return OpenAICompatibleResponder(
            api_key=loaded_settings.api_key,
            model_name=loaded_settings.model_name,
            base_url=loaded_settings.base_url,
        )
    return LocalFallbackResponder()
