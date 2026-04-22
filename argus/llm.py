"""LLM client abstraction -- pluggable LLM backends.

Ships with OpenRouterClient for OpenRouter-hosted models.
Implement the LLMClient protocol to swap in any provider.
"""

from __future__ import annotations

import abc
import json
import os
from typing import Any

import httpx


class LLMClient(abc.ABC):
    """Abstract LLM backend."""

    @abc.abstractmethod
    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        """Send a chat completion request and return the assistant message text."""
        ...


class OpenRouterClient(LLMClient):
    """OpenRouter chat-completion client.

    Usage::

        client = OpenRouterClient(
            api_key="sk-or-...",
            model="nvidia/nemotron-3-super-120b-a12b:free",
        )
        reply = client.chat([{"role": "user", "content": "Hello"}])
    """

    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "nvidia/nemotron-3-super-120b-a12b:free",
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Pass api_key= or set OPENROUTER_API_KEY env var."
            )
        self.model = model
        self._client = httpx.Client(timeout=timeout)

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = self._client.post(self.ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # OpenRouter follows the OpenAI response shape
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices in LLM response: {json.dumps(data)[:500]}")
        return choices[0]["message"]["content"]
