from __future__ import annotations

import os
from typing import Protocol

import httpx

from .settings import LLMSettings


class LLMConfigurationError(RuntimeError):
    pass


class LLMRequestError(RuntimeError):
    pass


class LLMClient(Protocol):
    def chat(self, messages: list[dict], *, stream: bool = False) -> str:
        ...


class OpenAICompatibleClient:
    def __init__(
        self,
        settings: LLMSettings,
        *,
        http_client: httpx.Client | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
    ):
        self.settings = settings
        self._http_client = http_client
        self._api_key = api_key
        self.timeout = timeout

    @property
    def api_key(self) -> str:
        if self._api_key:
            return self._api_key
        value = os.environ.get(self.settings.api_key_env)
        if not value:
            raise LLMConfigurationError(
                f"Missing API key environment variable: {self.settings.api_key_env}"
            )
        return value

    def chat(self, messages: list[dict], *, stream: bool = False) -> str:
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        payload = {"model": self.settings.model, "messages": messages, "stream": False}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self._http_client is not None:
                response = self._http_client.post(url, json=payload, headers=headers)
            else:
                response = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMRequestError(f"LLM request failed: {exc}") from exc

        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMRequestError(f"Unexpected LLM response shape: {exc}") from exc
