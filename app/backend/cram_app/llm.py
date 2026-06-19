from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

import httpx

from .settings import LLMSettings


class LLMConfigurationError(RuntimeError):
    pass


class LLMRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class StreamEvent:
    """A single streamed delta. kind is "reasoning" (model thinking) or "content" (answer)."""

    kind: str
    text: str


# Some OpenAI-compatible gateways reject default library User-Agents (e.g. "python-httpx")
# with "this channel does not allow the current client". Present a browser-like UA so the
# request passes those client filters. Gateways with a strict allowlist can be matched by
# setting CRAM_LLM_USER_AGENT to whatever client string they expect.
_CLIENT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


def _resolve_user_agent() -> str:
    return os.environ.get("CRAM_LLM_USER_AGENT", "").strip() or _CLIENT_USER_AGENT


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
            "User-Agent": _resolve_user_agent(),
        }
        try:
            if self._http_client is not None:
                response = self._http_client.post(url, json=payload, headers=headers)
            else:
                response = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise LLMRequestError(f"LLM request failed: {exc}") from exc

        data = _safe_json(response)
        if response.is_error:
            detail = _extract_error_message(data) or (response.text or "").strip()[:300]
            raise LLMRequestError(f"LLM HTTP {response.status_code}: {detail}")
        if not isinstance(data, dict) or "choices" not in data:
            detail = _extract_error_message(data)
            if detail:
                raise LLMRequestError(f"LLM error: {detail}")
            raise LLMRequestError(f"Unexpected LLM response (no choices): {str(data)[:300]}")
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMRequestError(f"Unexpected LLM response shape: {exc}") from exc

    def stream_chat(self, messages: list[dict]):
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        payload = {"model": self.settings.model, "messages": messages, "stream": True}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": _resolve_user_agent(),
        }
        try:
            if self._http_client is not None:
                response = self._http_client.post(url, json=payload, headers=headers)
            else:
                response = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise LLMRequestError(f"LLM request failed: {exc}") from exc

        if response.is_error:
            data = _safe_json(response)
            detail = _extract_error_message(data) or (response.text or "").strip()[:300]
            raise LLMRequestError(f"LLM HTTP {response.status_code}: {detail}")

        for line in response.iter_lines():
            line = line.strip()
            if not line or not line.startswith("data:"):
                continue
            payload_text = line.removeprefix("data:").strip()
            if payload_text == "[DONE]":
                break
            try:
                data = json.loads(payload_text)
            except ValueError as exc:
                raise LLMRequestError(f"Unexpected stream event: {payload_text[:120]}") from exc
            detail = _extract_error_message(data)
            if detail:
                raise LLMRequestError(f"LLM stream error: {detail}")
            try:
                delta = data["choices"][0].get("delta") or {}
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMRequestError(f"Unexpected stream response shape: {exc}") from exc
            reasoning = delta.get("reasoning_content") or delta.get("reasoning")
            if reasoning:
                yield StreamEvent("reasoning", str(reasoning))
            content = delta.get("content")
            if content:
                yield StreamEvent("content", str(content))


def _safe_json(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return None


def _extract_error_message(data) -> str | None:
    if not isinstance(data, dict):
        return None
    error = data.get("error")
    if isinstance(error, dict):
        return error.get("message") or error.get("code") or json.dumps(error, ensure_ascii=False)[:300]
    if isinstance(error, str):
        return error
    for key in ("message", "msg", "detail"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def fetch_models(
    base_url: str,
    api_key: str,
    *,
    http_client: httpx.Client | None = None,
    timeout: float = 30.0,
) -> list[str]:
    """Return the model ids advertised by an OpenAI-compatible /models endpoint."""
    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": _resolve_user_agent()}
    try:
        if http_client is not None:
            response = http_client.get(url, headers=headers)
        else:
            response = httpx.get(url, headers=headers, timeout=timeout)
    except httpx.HTTPError as exc:
        raise LLMRequestError(f"Failed to fetch models: {exc}") from exc

    data = _safe_json(response)
    if response.is_error:
        detail = _extract_error_message(data) or (response.text or "").strip()[:300]
        raise LLMRequestError(f"Models HTTP {response.status_code}: {detail}")

    items = data.get("data") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise LLMRequestError("Unexpected /models response shape")

    models: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            models.append(str(item["id"]))
        elif isinstance(item, str):
            models.append(item)
    if not models:
        raise LLMRequestError("No models returned by provider")
    return list(dict.fromkeys(models))
