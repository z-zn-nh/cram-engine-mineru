from __future__ import annotations

import json
from pathlib import Path

from .chunks import ChunkRecord
from .subjects import Subject


def citations_path(subject: Subject) -> Path:
    return subject.path / "citations" / "citations.json"


def write_citations(subject: Subject, chunks: list[ChunkRecord]) -> Path:
    path = citations_path(subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "source_file": chunk.source_file,
            "locator": chunk.locator,
            "citation_label": chunk.citation_label,
            "excerpt": chunk.text,
        }
        for chunk in chunks
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

