import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.cram_app.llm import LLMConfigurationError, OpenAICompatibleClient
from app.backend.cram_app.settings import LLMSettings, load_llm_settings, save_llm_settings


class LLMSettingsTests(unittest.TestCase):
    def test_save_and_load_openai_compatible_settings_without_api_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            settings = LLMSettings(
                provider="openai-compatible",
                base_url="https://api.example.com/v1",
                model="test-model",
                api_key_env="CRAM_TEST_API_KEY",
            )

            save_llm_settings(path, settings)
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertNotIn("api_key", payload)
            self.assertEqual(load_llm_settings(path), settings)

    def test_client_requires_api_key_environment_variable(self):
        settings = LLMSettings(
            provider="openai-compatible",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key_env="CRAM_MISSING_API_KEY",
        )

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(LLMConfigurationError, "CRAM_MISSING_API_KEY"):
                OpenAICompatibleClient(settings).api_key

    def test_client_reads_api_key_from_environment(self):
        settings = LLMSettings(
            provider="openai-compatible",
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key_env="CRAM_TEST_API_KEY",
        )

        with patch.dict(os.environ, {"CRAM_TEST_API_KEY": "secret"}, clear=True):
            self.assertEqual(OpenAICompatibleClient(settings).api_key, "secret")


if __name__ == "__main__":
    unittest.main()
