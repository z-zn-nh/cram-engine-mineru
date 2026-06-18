from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_SOURCE_EXTENSIONS = {
    ".pdf": "document",
    ".ppt": "document",
    ".pptx": "document",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".bmp": "image",
    ".gif": "image",
    ".txt": "notes",
    ".md": "notes",
}

INTERNAL_DIRS = {".cram", "cram-output", "__pycache__", ".git"}


@dataclass(frozen=True)
class WorkspaceSource:
    path: Path
    relative_path: Path
    kind: str


@dataclass(frozen=True)
class CramWorkspace:
    root: Path
    course_name: str
    cram_dir: Path
    output_dir: Path

    @classmethod
    def open(cls, path: Path | str = ".") -> "CramWorkspace":
        root = Path(path).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)

        cram_dir = root / ".cram"
        output_dir = root / "cram-output"
        for child in (
            cram_dir,
            cram_dir / "memory",
            cram_dir / "sessions",
            cram_dir / "index",
            cram_dir / "parsed",
            cram_dir / "cache",
            output_dir,
        ):
            child.mkdir(parents=True, exist_ok=True)

        return cls(
            root=root,
            course_name=root.name,
            cram_dir=cram_dir,
            output_dir=output_dir,
        )


def _is_internal(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part in INTERNAL_DIRS for part in relative.parts)


def discover_workspace_sources(root: Path | str) -> list[WorkspaceSource]:
    workspace_root = Path(root).expanduser().resolve()
    sources: list[WorkspaceSource] = []
    for path in workspace_root.rglob("*"):
        if not path.is_file() or _is_internal(path, workspace_root):
            continue
        kind = SUPPORTED_SOURCE_EXTENSIONS.get(path.suffix.lower())
        if not kind:
            continue
        sources.append(
            WorkspaceSource(
                path=path,
                relative_path=path.relative_to(workspace_root),
                kind=kind,
            )
        )

    return sorted(sources, key=lambda source: source.relative_path.as_posix().lower())
