from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .artifacts import ARTIFACT_DIRS
from .chat import CramChatService
from .llm import LLMClient, LLMConfigurationError, LLMRequestError
from .paths import default_subjects_root
from .subjects import Subject, create_subject, subject_slug


class SubjectCreateRequest(BaseModel):
    name: str


class ChatRequest(BaseModel):
    message: str


class UploadSourceRequest(BaseModel):
    paths: list[str]


def _read_subject_name(path: Path) -> str:
    db_path = path / "subject.sqlite"
    if not db_path.exists():
        return path.name
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("select value from metadata where key = 'subject_name'").fetchone()
        return row[0] if row else path.name
    finally:
        conn.close()


def _list_subjects(root: Path) -> list[dict[str, str]]:
    if not root.exists():
        return []
    subjects = []
    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if child.is_dir():
            subjects.append({"name": _read_subject_name(child), "slug": child.name})
    return subjects


def _get_subject(root: Path, slug_or_name: str) -> Subject:
    slug = subject_slug(slug_or_name)
    path = root / slug
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"subject not found: {slug_or_name}")
    return Subject(name=_read_subject_name(path), slug=slug, path=path)


def _list_artifacts(subject: Subject) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    root = subject.path / "artifacts"
    for artifact_type, folder_name in ARTIFACT_DIRS.items():
        folder = root / folder_name
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if path.is_file() and not path.name.endswith(".citations.json"):
                artifacts.append(
                    {
                        "artifact_type": artifact_type,
                        "title": path.stem,
                        "path": str(path),
                        "relative_path": path.relative_to(subject.path).as_posix(),
                    }
                )
    return artifacts


def _read_citations(subject: Subject) -> list[dict[str, Any]]:
    path = subject.path / "citations" / "citations.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _read_artifact_content(subject: Subject, relative_path: str) -> dict[str, Any]:
    artifacts_root = (subject.path / "artifacts").resolve()
    selected = (subject.path / relative_path).resolve()
    try:
        selected.relative_to(artifacts_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="artifact path must stay inside subject artifacts") from exc
    if not selected.exists() or not selected.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    if selected.name.endswith(".citations.json"):
        raise HTTPException(status_code=400, detail="citation sidecars are not preview artifacts")
    return {
        "title": selected.stem,
        "relative_path": selected.relative_to(subject.path).as_posix(),
        "content": selected.read_text(encoding="utf-8"),
    }


def create_app(*, subjects_root: Path | None = None, llm: LLMClient | None = None) -> FastAPI:
    root = subjects_root or default_subjects_root()
    root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="cram-engine-mineru")

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/subjects")
    def list_subjects() -> list[dict[str, str]]:
        return _list_subjects(root)

    @app.post("/subjects")
    def post_subject(request: SubjectCreateRequest) -> dict[str, str]:
        subject = create_subject(request.name, root)
        return {"name": subject.name, "slug": subject.slug}

    @app.post("/subjects/{subject}/sources")
    def post_sources(subject: str, request: UploadSourceRequest) -> dict[str, Any]:
        selected = _get_subject(root, subject)
        return {"subject": selected.name, "paths": request.paths}

    @app.post("/subjects/{subject}/chat")
    def post_chat(subject: str, request: ChatRequest) -> dict[str, Any]:
        if llm is None:
            raise HTTPException(status_code=503, detail="LLM client is not configured")
        selected = _get_subject(root, subject)
        try:
            response = CramChatService(llm).review(selected, request.message)
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LLMRequestError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "message": response.message,
            "citations": response.citations,
            "artifacts": response.artifacts,
        }

    @app.get("/subjects/{subject}/artifacts")
    def get_artifacts(subject: str) -> list[dict[str, Any]]:
        return _list_artifacts(_get_subject(root, subject))

    @app.get("/subjects/{subject}/artifacts/content")
    def get_artifact_content(subject: str, relative_path: str) -> dict[str, Any]:
        return _read_artifact_content(_get_subject(root, subject), relative_path)

    @app.get("/subjects/{subject}/citations")
    def get_citations(subject: str) -> list[dict[str, Any]]:
        return _read_citations(_get_subject(root, subject))

    return app
