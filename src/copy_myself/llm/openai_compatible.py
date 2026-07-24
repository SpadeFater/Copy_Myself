from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from copy_myself.config import ModelProviderSettings
from copy_myself.llm.base import ChatMessage, ModelClient


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
