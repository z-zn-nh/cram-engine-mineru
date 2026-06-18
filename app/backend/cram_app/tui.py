from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from .commands import CommandRouter
from .memory import MemoryStore
from .workspace import CramWorkspace, discover_workspace_sources


class CramTuiApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #e5e7eb;
    }

    #status {
        dock: top;
        height: 3;
        padding: 0 1;
        background: #111827;
        color: #d1d5db;
        border-bottom: solid #334155;
    }

    #chat {
        height: 1fr;
        padding: 1 2;
        background: #0f172a;
        color: #e5e7eb;
    }

    #prompt {
        dock: bottom;
        margin: 0 1 1 1;
        border: round #475569;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "退出"),
        ("ctrl+l", "clear_chat", "清屏"),
    ]

    def __init__(self, workspace_path: Path | str = "."):
        super().__init__()
        self.workspace = CramWorkspace.open(workspace_path)
        self.router = CommandRouter(self.workspace)
        self.memory = MemoryStore.open(self.workspace)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._status_text(), id="status")
        with Vertical():
            yield RichLog(id="chat", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="输入问题，或 /help /status /ingest /plan /notes /mindmap /quiz /summary /lint", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        chat = self.query_one("#chat", RichLog)
        chat.write("[bold cyan]cram-engine-mineru[/bold cyan]")
        chat.write(f"当前课程文件夹：[bold]{self.workspace.course_name}[/bold]")
        boot_summary = self.memory.load_boot_summary().strip()
        if boot_summary:
            chat.write("[bold]Memory[/bold]")
            chat.write(boot_summary)
        else:
            chat.write("首次打开此课程文件夹。输入 /ingest 扫描资料，或直接开始提问。")
        self.query_one("#prompt", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return

        chat = self.query_one("#chat", RichLog)
        chat.write(f"\n[bold green]You[/bold green]\n{text}")
        result = self.router.handle(text)
        if result.message:
            chat.write(f"\n[bold cyan]Agent[/bold cyan]\n{result.message}")
        if result.wrote:
            wrote = "\n".join(path.relative_to(self.workspace.root).as_posix() for path in result.wrote)
            chat.write(f"\n[bold yellow]Wrote[/bold yellow]\n{wrote}")
        self.query_one("#status", Static).update(self._status_text())

    def action_clear_chat(self) -> None:
        self.query_one("#chat", RichLog).clear()

    def _status_text(self) -> str:
        source_count = len(discover_workspace_sources(self.workspace.root))
        output_count = len([path for path in self.workspace.output_dir.rglob("*") if path.is_file()])
        return (
            f"cram · {self.workspace.course_name} · {source_count} files · "
            f"{output_count} outputs · memory on · cwd workspace"
        )


def run_tui(workspace_path: Path | str = ".") -> None:
    CramTuiApp(workspace_path).run()
