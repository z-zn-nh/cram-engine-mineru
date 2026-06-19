from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .workspace import CramWorkspace, WorkspaceSource
from .workspace_index import ParsedTextSource


MINERU_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
PENDING_EXTENSIONS = {".ppt", ".pptx", ".webp", ".bmp", ".gif"}


@dataclass(frozen=True)
class MaterialIngestResult:
    parsed_texts: list[ParsedTextSource]
    processed_files: int
    failed_files: list[str]
    pending_files: list[str]


def ingest_material_sources(
    workspace: CramWorkspace,
    sources: list[WorkspaceSource],
    *,
    mineru_bin: str | None = None,
    timeout: int = 600,
) -> MaterialIngestResult:
    mineru = mineru_bin or os.environ.get("CRAM_MINERU_BIN", "mineru")
    parsed_texts: list[ParsedTextSource] = []
    failed: list[str] = []
    pending: list[str] = []
    processed = 0

    for source in sources:
        suffix = source.path.suffix.lower()
        relative = source.relative_path.as_posix()
        if suffix in {".md", ".txt"}:
            continue
        if suffix in PENDING_EXTENSIONS:
            pending.append(relative)
            continue
        if suffix not in MINERU_EXTENSIONS:
            pending.append(relative)
            continue
        if shutil.which(mineru) is None:
            pending.append(relative)
            continue

        output_dir = workspace.cram_dir / "parsed" / _parsed_dir_name(source.relative_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        cached_markdown = _fresh_markdown_files(output_dir, source.path)
        if cached_markdown:
            processed += 1
            parsed_texts.extend(
                ParsedTextSource(path=path, source_file=relative, locator_prefix="mineru")
                for path in cached_markdown
            )
            continue

        command = [mineru, "-p", str(source.path), "-o", str(output_dir)]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
        if completed.returncode != 0:
            failed.append(relative)
            continue
        markdown_files = sorted(output_dir.rglob("*.md"), key=lambda path: path.as_posix().lower())
        if not markdown_files:
            failed.append(relative)
            continue
        processed += 1
        parsed_texts.extend(
            ParsedTextSource(path=path, source_file=relative, locator_prefix="mineru")
            for path in markdown_files
        )

    return MaterialIngestResult(
        parsed_texts=parsed_texts,
        processed_files=processed,
        failed_files=failed,
        pending_files=pending,
    )


def _parsed_dir_name(relative_path: Path) -> str:
    return "__".join(relative_path.with_suffix("").parts)


def _fresh_markdown_files(output_dir: Path, source: Path) -> list[Path]:
    markdown_files = sorted(output_dir.rglob("*.md"), key=lambda path: path.as_posix().lower())
    if not markdown_files:
        return []
    source_mtime = source.stat().st_mtime
    if all(path.stat().st_mtime >= source_mtime for path in markdown_files):
        return markdown_files
    return []
