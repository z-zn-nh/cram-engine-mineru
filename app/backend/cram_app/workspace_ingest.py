from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .workspace import CramWorkspace, WorkspaceSource
from .workspace_index import ParsedTextSource


PPT_EXTENSIONS = {".ppt", ".pptx"}
MINERU_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"} | PPT_EXTENSIONS
PENDING_EXTENSIONS = {".webp", ".bmp", ".gif"}


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
    libreoffice_bin: str | None = None,
    timeout: int = 600,
) -> MaterialIngestResult:
    mineru = mineru_bin or os.environ.get("CRAM_MINERU_BIN", "mineru")
    libreoffice = libreoffice_bin or os.environ.get("CRAM_LIBREOFFICE_BIN", "soffice")
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

        markdown_files = _run_mineru(mineru, source.path, output_dir, timeout=timeout)
        if not markdown_files and suffix in PPT_EXTENSIONS:
            if shutil.which(libreoffice) is None:
                pending.append(relative)
                continue
            markdown_files = _run_ppt_pdf_fallback(
                source.path,
                output_dir,
                workspace.cram_dir / "converted" / _parsed_dir_name(source.relative_path),
                mineru_bin=mineru,
                libreoffice_bin=libreoffice,
                timeout=timeout,
            )
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


def _run_mineru(mineru: str, source: Path, output_dir: Path, *, timeout: int) -> list[Path]:
    command = [mineru, "-p", str(source), "-o", str(output_dir)]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    if completed.returncode != 0:
        return []
    return sorted(output_dir.rglob("*.md"), key=lambda path: path.as_posix().lower())


def _run_ppt_pdf_fallback(
    source: Path,
    output_dir: Path,
    fallback_dir: Path,
    *,
    mineru_bin: str,
    libreoffice_bin: str,
    timeout: int,
) -> list[Path]:
    fallback_dir.mkdir(parents=True, exist_ok=True)
    command = [
        libreoffice_bin,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(fallback_dir),
        str(source),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    if completed.returncode != 0:
        return []
    pdf_path = fallback_dir / f"{source.stem}.pdf"
    if not pdf_path.exists():
        converted = sorted(fallback_dir.glob("*.pdf"), key=lambda path: path.as_posix().lower())
        if not converted:
            return []
        pdf_path = converted[0]
    return _run_mineru(mineru_bin, pdf_path, output_dir, timeout=timeout)
