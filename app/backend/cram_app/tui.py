from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Input, RichLog, Static

from .commands import CommandRouter
from .memory import MemoryStore
from .workspace import CramWorkspace, discover_workspace_sources


class CramTuiApp(App):
    CSS = """
    Screen {
        background: #0b0f14;
        color: #d6deeb;
    }

    #status {
        dock: top;
        height: 1;
        padding: 0 1;
        background: #0b0f14;
        color: #9aa4b2;
        border-bottom: tall #1c2533;
    }

    #chat {
        height: 1fr;
        padding: 1 2 0 2;
        background: #0d1117;
        color: #d6deeb;
    }

    #prompt {
        dock: bottom;
        height: 3;
        margin: 0 1;
        padding: 0 1;
        background: #0b0f14;
        color: #d6deeb;
        border-top: tall #1c2533;
        border-bottom: tall #1c2533;
    }

    #prompt:focus {
        border-top: tall #607b96;
        border-bottom: tall #607b96;
    }

    Footer {
        background: #0b0f14;
        color: #8b949e;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "quit"),
        ("ctrl+l", "clear_chat", "clear"),
    ]

    def __init__(self, workspace_path: Path | str = "."):
        super().__init__()
        self.workspace = CramWorkspace.open(workspace_path)
        self.router = CommandRouter(self.workspace)
        self.memory = MemoryStore.open(self.workspace)
        self.title = f"cram - {self.workspace.root}"
        self.sub_title = self.workspace.course_name

    def compose(self) -> ComposeResult:
        yield Static(self._status_text(), id="status")
        with Vertical():
            yield RichLog(id="chat", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="ask or run /help /status /ingest /plan /notes /mindmap /quiz /summary", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        chat = self.query_one("#chat", RichLog)
        chat.write("[bold #79c0ff]cram[/bold #79c0ff] [#6e7681]course agent[/#6e7681]")
        chat.write(f"[#6e7681]workspace[/#6e7681] {self.workspace.root}")
        boot_summary = self.memory.load_boot_summary().strip()
        if boot_summary:
            chat.write("[bold #a5d6ff]memory[/bold #a5d6ff]")
            chat.write(boot_summary)
        else:
            chat.write("[#8b949e]first run here. use[/#8b949e] [bold]/ingest[/bold] [#8b949e]or ask a question.[/#8b949e]")
        self.query_one("#prompt", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return

        chat = self.query_one("#chat", RichLog)
        chat.write(f"\n[bold #7ee787]you[/bold #7ee787]\n{text}")
        result = self.router.handle(text)
        if result.message:
            chat.write(f"\n[bold #79c0ff]agent[/bold #79c0ff]\n{result.message}")
        if result.wrote:
            wrote = "\n".join(path.relative_to(self.workspace.root).as_posix() for path in result.wrote)
            chat.write(f"\n[bold #ffa657]wrote[/bold #ffa657]\n{wrote}")
        self.query_one("#status", Static).update(self._status_text())

    def action_clear_chat(self) -> None:
        self.query_one("#chat", RichLog).clear()

    def _status_text(self) -> str:
        source_count = len(discover_workspace_sources(self.workspace.root))
        output_count = len([path for path in self.workspace.output_dir.rglob("*") if path.is_file()])
        return (
            f"cram | {self.workspace.course_name} | {source_count} files | "
            f"{output_count} outputs | memory on | workspace {self.workspace.root}"
        )


def run_tui(workspace_path: Path | str = ".") -> None:
    CramTuiApp(workspace_path).run()
