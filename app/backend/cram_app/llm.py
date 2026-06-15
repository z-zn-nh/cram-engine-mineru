from __future__ import annotations

import os
from typing import Protocol

from .settings import LLMSettings


class LLMConfigurationError(RuntimeError):
    pass


class LLMClient(Protocol):
    def chat(self, messages: list[dict], *, stream: bool = False) -> str:
        ...


class OpenAICompatibleClient:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    @property
    def api_key(self) -> str:
        value = os.environ.get(self.settings.api_key_env)
        if not value:
            raise LLMConfigurationError(
                f"Missing API key environment variable: {self.settings.api_key_env}"
            )
        return value

    def chat(self, messages: list[dict], *, stream: bool = False) -> str:
        raise NotImplementedError("OpenAI-compatible HTTP calls will be wired in the API layer.")

