from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


REQUIRED_DIRS = ("sources", "parsed", "chunks", "index", "chats", "artifacts", "citations")


@dataclass(frozen=True)
class Subject:
    name: str
    slug: str
    path: Path


def subject_slug(name: str) -> str:
    slug = name.strip().replace("\\", "-").replace("/", "-")
    slug = re.sub(r"[.]+", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ValueError("subject name cannot be empty")
    return slug


def create_subject(name: str, root: Path) -> Subject:
    slug = subject_slug(name)
    subject_path = root.expanduser() / slug
    subject_path.mkdir(parents=True, exist_ok=True)
    for child in REQUIRED_DIRS:
        (subject_path / child).mkdir(exist_ok=True)

    db_path = subject_path / "subject.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("create table if not exists metadata (key text primary key, value text not null)")
        conn.execute("insert or replace into metadata(key, value) values ('subject_name', ?)", (name,))
        conn.commit()
    finally:
        conn.close()

    return Subject(name=name, slug=slug, path=subject_path)
