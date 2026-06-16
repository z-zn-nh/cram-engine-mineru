from __future__ import annotations

import os

from cram_app.api import create_app
from cram_app.llm import OpenAICompatibleClient
from cram_app.paths import default_settings_path
from cram_app.settings import LLMSettings, load_llm_settings


def _load_llm() -> OpenAICompatibleClient:
    path = default_settings_path()
    if path.exists():
        settings = load_llm_settings(path)
    else:
        settings = LLMSettings(
            provider="openai-compatible",
            base_url=os.environ.get("CRAM_LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("CRAM_LLM_MODEL", "gpt-4o-mini"),
        )
    return OpenAICompatibleClient(settings)


app = create_app(llm=_load_llm())
