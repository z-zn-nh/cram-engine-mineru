from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .subjects import Subject


ARTIFACT_DIRS = {
    "cram_plan": "速成计划",
    "notes": "笔记",
    "mindmap": "思维导图",
    "qbank": "题库",
    "mistakes": "错题本",
    "summary": "考前总结",
}


@dataclass(frozen=True)
class Artifact:
    artifact_type: str
    title: str
    path: Path
    relative_path: Path
    citations_path: Path


def artifact_filename(title: str) -> str:
    name = title.strip().replace("\\", "-").replace("/", "-")
    name = re.sub(r"[.]+", "", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    if not name:
        raise ValueError("artifact title cannot be empty")
    return name


def save_artifact(
    subject: Subject,
    *,
    artifact_type: str,
    title: str,
    content: str,
    citations: list[str],
    fmt: str,
) -> Artifact:
    if artifact_type not in ARTIFACT_DIRS:
        raise ValueError(f"unknown artifact type: {artifact_type}")

    extension = fmt.strip().lstrip(".")
    if not extension:
        raise ValueError("artifact format cannot be empty")

    folder = subject.path / "artifacts" / ARTIFACT_DIRS[artifact_type]
    folder.mkdir(parents=True, exist_ok=True)

    stem = artifact_filename(title)
    path = folder / f"{stem}.{extension}"
    path.write_text(content, encoding="utf-8")

    citations_path = folder / f"{stem}.citations.json"
    citations_path.write_text(
        json.dumps({"artifact": path.name, "citations": citations}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return Artifact(
        artifact_type=artifact_type,
        title=title,
        path=path,
        relative_path=path.relative_to(subject.path),
        citations_path=citations_path,
    )

