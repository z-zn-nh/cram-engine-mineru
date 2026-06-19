from __future__ import annotations

import json
from dataclasses import asdict, dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    base_url: str
    model: str
    api_key_env: str = "CRAM_LLM_API_KEY"


@dataclass(frozen=True)
class UserLLMConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"


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


def user_llm_config_path() -> Path:
    override = os.environ.get("CRAM_LLM_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cram-engine-mineru" / "llm.json"


def save_user_llm_config(config: UserLLMConfig, path: Path | None = None) -> Path:
    target = path or user_llm_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_user_llm_config(path: Path | None = None) -> UserLLMConfig | None:
    target = path or user_llm_config_path()
    if not target.exists():
        return None
    payload = json.loads(target.read_text(encoding="utf-8"))
    api_key = str(payload.get("api_key", "")).strip()
    if not api_key:
        return None
    return UserLLMConfig(
        api_key=api_key,
        base_url=str(payload.get("base_url") or "https://api.openai.com/v1"),
        model=str(payload.get("model") or "gpt-4o-mini"),
    )

