import json
import os
import unittest
from unittest.mock import patch

import httpx

from app.backend.cram_app.llm import (
    LLMConfigurationError,
    LLMRequestError,
    OpenAICompatibleClient,
)
from app.backend.cram_app.settings import LLMSettings


def _settings() -> LLMSettings:
    return LLMSettings(
        provider="openai-compatible",
        base_url="https://api.example.com/v1",
        model="test-model",
        api_key_env="CRAM_TEST_API_KEY",
    )


class LLMClientTests(unittest.TestCase):
    def test_chat_posts_openai_payload_and_returns_content(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": "grounded answer"}}]},
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            answer = client.chat([{"role": "system", "content": "hi"}])

        self.assertEqual(answer, "grounded answer")
        self.assertEqual(captured["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(captured["auth"], "Bearer secret")
        self.assertEqual(captured["body"]["model"], "test-model")
        self.assertEqual(captured["body"]["messages"][0]["content"], "hi")
        self.assertFalse(captured["body"]["stream"])

    def test_chat_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            client = OpenAICompatibleClient(_settings())
            with self.assertRaisesRegex(LLMConfigurationError, "CRAM_TEST_API_KEY"):
                client.chat([{"role": "user", "content": "x"}])

    def test_chat_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            with self.assertRaises(LLMRequestError):
                client.chat([{"role": "user", "content": "x"}])


if __name__ == "__main__":
    unittest.main()
