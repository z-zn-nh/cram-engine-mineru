from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .workspace import CramWorkspace, WorkspaceSource, discover_workspace_sources


TEXT_EXTENSIONS = {".md", ".txt"}


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_file: str
    locator: str
    text: str

    @property
    def citation_label(self) -> str:
        return f"{self.source_file}:{self.locator}"


@dataclass(frozen=True)
class WorkspaceIndexResult:
    indexed_files: int
    indexed_chunks: int
    skipped_files: int


@dataclass(frozen=True)
class ParsedTextSource:
    path: Path
    source_file: str
    locator_prefix: str = "parsed"


def workspace_chunks_path(workspace: CramWorkspace) -> Path:
    return workspace.cram_dir / "index" / "chunks.jsonl"


def index_text_sources(
    workspace: CramWorkspace,
    *,
    extra_texts: list[ParsedTextSource] | None = None,
) -> WorkspaceIndexResult:
    sources = discover_workspace_sources(workspace.root)
    text_sources = [source for source in sources if source.path.suffix.lower() in TEXT_EXTENSIONS]
    chunks: list[ChunkRecord] = []
    skipped = 0

    for source in text_sources:
        text = _read_text(source.path)
        source_chunks = _chunk_text_source(source, text)
        if not source_chunks:
            skipped += 1
            continue
        chunks.extend(source_chunks)

    parsed_texts = extra_texts or []
    for parsed in parsed_texts:
        text = _read_text(parsed.path)
        source_chunks = _chunk_parsed_text(parsed, text)
        if not source_chunks:
            skipped += 1
            continue
        chunks.extend(source_chunks)

    path = workspace_chunks_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            payload = asdict(chunk)
            payload["citation_label"] = chunk.citation_label
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return WorkspaceIndexResult(
        indexed_files=len(text_sources) + len(parsed_texts) - skipped,
        indexed_chunks=len(chunks),
        skipped_files=skipped,
    )


def load_workspace_chunks(workspace: CramWorkspace) -> list[ChunkRecord]:
    path = workspace_chunks_path(workspace)
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


def search_workspace_chunks(workspace: CramWorkspace, query: str, *, limit: int = 5) -> list[ChunkRecord]:
    terms = _query_terms(query)
    if not terms:
        return []

    scored: list[tuple[int, ChunkRecord]] = []
    for chunk in load_workspace_chunks(workspace):
        haystack = f"{chunk.source_file} {chunk.locator} {chunk.text}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
    return [chunk for _, chunk in scored[:limit]]


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _chunk_text_source(source: WorkspaceSource, text: str, *, max_chars: int = 1200) -> list[ChunkRecord]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]

    chunks: list[ChunkRecord] = []
    current: list[str] = []
    current_len = 0
    chunk_number = 1
    for paragraph in paragraphs:
        if current and current_len + len(paragraph) + 2 > max_chars:
            chunks.append(_make_chunk(source, chunk_number, "\n\n".join(current)))
            chunk_number += 1
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += len(paragraph) + 2

    if current:
        chunks.append(_make_chunk(source, chunk_number, "\n\n".join(current)))
    return chunks


def _make_chunk(source: WorkspaceSource, number: int, text: str) -> ChunkRecord:
    relative = source.relative_path.as_posix()
    return ChunkRecord(
        chunk_id=f"{relative}:text:{number}",
        source_file=relative,
        locator=f"text:{number}",
        text=text,
    )


def _chunk_parsed_text(parsed: ParsedTextSource, text: str, *, max_chars: int = 1200) -> list[ChunkRecord]:
    fake_source = WorkspaceSource(
        path=parsed.path,
        relative_path=Path(parsed.source_file),
        kind="parsed",
    )
    chunks = _chunk_text_source(fake_source, text, max_chars=max_chars)
    return [
        ChunkRecord(
            chunk_id=f"{parsed.source_file}:{parsed.locator_prefix}:{index}",
            source_file=parsed.source_file,
            locator=f"{parsed.locator_prefix}:{index}",
            text=chunk.text,
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


def _query_terms(query: str) -> list[str]:
    normalized = query.strip().lower()
    terms = [term for term in re.split(r"\s+", normalized) if term]
    compact = re.sub(r"\s+", "", normalized)
    if compact and compact == normalized and len(compact) > 2:
        terms.extend(compact[index : index + 2] for index in range(len(compact) - 1))
    return list(dict.fromkeys(terms))
