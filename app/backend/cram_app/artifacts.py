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


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"mindmap {field_name} must be a non-empty string")
    return value


def _validate_mindmap_node(node: object, path: str) -> None:
    if not isinstance(node, dict):
        raise ValueError(f"mindmap node at {path} must be an object")
    _require_text(node.get("label"), f"{path}.label")

    children = node.get("children", [])
    if children is None:
        return
    if not isinstance(children, list):
        raise ValueError(f"mindmap {path}.children must be a list")
    for index, child in enumerate(children):
        _validate_mindmap_node(child, f"{path}.children[{index}]")


def validate_mindmap_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise ValueError("mindmap payload must be an object")
    _require_text(payload.get("title"), "title")

    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("mindmap nodes must be a non-empty list")
    for index, node in enumerate(nodes):
        _validate_mindmap_node(node, f"nodes[{index}]")


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
    if artifact_type == "mindmap" and extension.lower() == "json":
        try:
            validate_mindmap_payload(json.loads(content))
        except json.JSONDecodeError as exc:
            raise ValueError("mindmap content must be valid JSON") from exc

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
