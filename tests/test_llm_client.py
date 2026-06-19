import json
import os
import unittest
from unittest.mock import patch

import httpx

from app.backend.cram_app.llm import (
    LLMConfigurationError,
    LLMRequestError,
    OpenAICompatibleClient,
    fetch_models,
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

    def test_chat_surfaces_provider_error_when_no_choices(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"error": {"message": "model not found"}})

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            with self.assertRaisesRegex(LLMRequestError, "model not found"):
                client.chat([{"role": "user", "content": "x"}])

    def test_chat_surfaces_gateway_msg_field(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"code": 0, "msg": "网关已关闭", "data": None})

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            with self.assertRaisesRegex(LLMRequestError, "网关已关闭"):
                client.chat([{"role": "user", "content": "x"}])


    def test_chat_sends_non_default_user_agent(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["ua"] = request.headers.get("user-agent")
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            client.chat([{"role": "user", "content": "x"}])

        self.assertTrue(captured["ua"])
        self.assertNotIn("python-httpx", captured["ua"])

    def test_user_agent_can_be_overridden_via_env(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["ua"] = request.headers.get("user-agent")
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(
            os.environ,
            {"CRAM_TEST_API_KEY": "secret", "CRAM_LLM_USER_AGENT": "CherryStudio/1.0"},
            clear=True,
        ):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            client.chat([{"role": "user", "content": "x"}])

        self.assertEqual(captured["ua"], "CherryStudio/1.0")

    def test_stream_chat_posts_stream_payload_and_yields_deltas(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                text=(
                    'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
                    'data: {"choices":[{"delta":{"content":"好"}}]}\n\n'
                    "data: [DONE]\n\n"
                ),
                headers={"content-type": "text/event-stream"},
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            chunks = list(client.stream_chat([{"role": "user", "content": "x"}]))

        self.assertTrue(captured["body"]["stream"])
        self.assertEqual(chunks, ["你", "好"])

    def test_stream_chat_surfaces_error_event(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text='data: {"error":{"message":"bad stream"}}\n\n',
                headers={"content-type": "text/event-stream"},
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            client = OpenAICompatibleClient(_settings(), http_client=http_client)
            with self.assertRaisesRegex(LLMRequestError, "bad stream"):
                list(client.stream_chat([{"role": "user", "content": "x"}]))


class FetchModelsTests(unittest.TestCase):
    def test_fetch_models_returns_unique_ids_in_order(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization")
            return httpx.Response(
                200,
                json={"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]},
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        models = fetch_models("https://api.example.com/v1", "secret", http_client=http_client)

        self.assertEqual(models, ["gpt-4o", "gpt-4o-mini"])
        self.assertEqual(captured["url"], "https://api.example.com/v1/models")
        self.assertEqual(captured["auth"], "Bearer secret")

    def test_fetch_models_raises_with_provider_detail(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": {"message": "bad key"}})

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        with self.assertRaisesRegex(LLMRequestError, "bad key"):
            fetch_models("https://api.example.com/v1", "secret", http_client=http_client)

    def test_fetch_models_sends_non_default_user_agent(self):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["ua"] = request.headers.get("user-agent")
            return httpx.Response(200, json={"data": [{"id": "m"}]})

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        fetch_models("https://api.example.com/v1", "secret", http_client=http_client)

        self.assertTrue(captured["ua"])
        self.assertNotIn("python-httpx", captured["ua"])


if __name__ == "__main__":
    unittest.main()
