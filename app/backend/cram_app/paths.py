from __future__ import annotations

import os
from pathlib import Path


def default_app_data_root() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "cram-engine-mineru"
    return Path.home() / ".cram-engine-mineru"


def default_subjects_root() -> Path:
    return default_app_data_root() / "subjects"


def default_settings_path() -> Path:
    return default_app_data_root() / "settings.json"
