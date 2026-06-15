from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .subjects import Subject


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_file: str
    locator: str
    text: str

    @property
    def citation_label(self) -> str:
        return f"{self.source_file}:{self.locator}"


def chunks_path(subject: Subject) -> Path:
    return subject.path / "chunks" / "chunks.jsonl"


def append_chunks(subject: Subject, chunks: list[ChunkRecord]) -> Path:
    path = chunks_path(subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for chunk in chunks:
            payload = asdict(chunk)
            payload["citation_label"] = chunk.citation_label
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def load_chunks(subject: Subject) -> list[ChunkRecord]:
    path = chunks_path(subject)
    if not path.exists():
        return []
    records: list[ChunkRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        records.append(
            ChunkRecord(
                chunk_id=payload["chunk_id"],
                source_file=payload["source_file"],
                locator=payload["locator"],
                text=payload["text"],
            )
        )
    return records


def _query_terms(query: str) -> list[str]:
    return [term for term in re.split(r"\s+", query.strip().lower()) if term]


def search_chunks(subject: Subject, query: str, *, limit: int = 5) -> list[ChunkRecord]:
    terms = _query_terms(query)
    if not terms:
        return []

    scored: list[tuple[int, ChunkRecord]] = []
    for chunk in load_chunks(subject):
        haystack = f"{chunk.source_file} {chunk.locator} {chunk.text}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
    return [chunk for _, chunk in scored[:limit]]

