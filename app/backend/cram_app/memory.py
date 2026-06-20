from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .workspace import CramWorkspace, discover_workspace_sources


@dataclass(frozen=True)
class ReferenceRecord:
    label: str
    path: Path
    priority: int
    source_type: str


class MemoryStore:
    def __init__(self, workspace: CramWorkspace):
        self.workspace = workspace
        self.memory_dir = workspace.cram_dir / "memory"
        self.sessions_dir = workspace.cram_dir / "sessions"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def open(cls, workspace: CramWorkspace) -> "MemoryStore":
        return cls(workspace)

    @property
    def boot_summary_path(self) -> Path:
        return self.memory_dir / "memory.md"

    @property
    def session_path(self) -> Path:
        return self.sessions_dir / "current.jsonl"

    @property
    def conflicts_path(self) -> Path:
        return self.memory_dir / "conflicts.jsonl"

    def save_boot_summary(self, content: str) -> Path:
        self.boot_summary_path.write_text(content, encoding="utf-8")
        return self.boot_summary_path

    def append_memory_note(self, note: str, *, category: str | None = None) -> bool:
        """Append a durable note to the long-term memory file. Returns False if it already exists."""
        note = note.strip()
        if not note:
            return False
        line = f"- [{category}] {note}" if category else f"- {note}"
        existing = self.load_boot_summary()
        lines = [item for item in existing.splitlines() if item.strip()]
        if line in lines:
            return False
        lines.append(line)
        self.save_boot_summary("\n".join(lines) + "\n")
        return True

    def load_boot_summary(self) -> str:
        if not self.boot_summary_path.exists():
            return ""
        return self.boot_summary_path.read_text(encoding="utf-8")

    def append_session_event(self, role: str, content: str) -> Path:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        with self.session_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return self.session_path

    def load_recent_session_events(self, *, limit: int = 20) -> list[dict]:
        events = self.load_all_session_events()
        return events[-limit:]

    def load_all_session_events(self) -> list[dict]:
        if not self.session_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.session_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @property
    def rolling_summary_path(self) -> Path:
        return self.memory_dir / "rolling_summary.md"

    @property
    def summary_state_path(self) -> Path:
        return self.memory_dir / "summary_state.json"

    def load_rolling_summary(self) -> str:
        if not self.rolling_summary_path.exists():
            return ""
        return self.rolling_summary_path.read_text(encoding="utf-8")

    def save_rolling_summary(self, text: str) -> Path:
        self.rolling_summary_path.write_text(text, encoding="utf-8")
        return self.rolling_summary_path

    def load_summarized_through(self) -> int:
        if not self.summary_state_path.exists():
            return 0
        try:
            return int(json.loads(self.summary_state_path.read_text(encoding="utf-8")).get("summarized_through", 0))
        except (ValueError, OSError):
            return 0

    def save_summarized_through(self, count: int) -> None:
        self.summary_state_path.write_text(json.dumps({"summarized_through": count}), encoding="utf-8")

    def build_reference_catalog(self) -> list[ReferenceRecord]:
        references: list[ReferenceRecord] = []
        for source in discover_workspace_sources(self.workspace.root):
            references.append(
                ReferenceRecord(
                    label=f"[原始资料] {source.relative_path.as_posix()}",
                    path=source.path,
                    priority=10,
                    source_type="source",
                )
            )

        for path in sorted(self.workspace.output_dir.rglob("*"), key=lambda item: item.as_posix().lower()):
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".html", ".json"}:
                continue
            relative = path.relative_to(self.workspace.root).as_posix()
            references.append(
                ReferenceRecord(
                    label=f"[生成产物] {relative}",
                    path=path,
                    priority=30,
                    source_type="artifact",
                )
            )

        return sorted(references, key=lambda reference: (reference.priority, reference.label))

    def record_conflict(self, title: str, *, left: str, right: str) -> Path:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "left": left,
            "right": right,
        }
        with self.conflicts_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return self.conflicts_path

    def load_conflicts(self) -> list[dict]:
        if not self.conflicts_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.conflicts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
