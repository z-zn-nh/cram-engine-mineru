from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    base_url: str
    model: str
    api_key_env: str = "CRAM_LLM_API_KEY"


def save_llm_settings(path: Path, settings: LLMSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    payload.pop("api_key", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_llm_settings(path: Path) -> LLMSettings:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return LLMSettings(
        provider=payload["provider"],
        base_url=payload["base_url"],
        model=payload["model"],
        api_key_env=payload.get("api_key_env", "CRAM_LLM_API_KEY"),
    )

