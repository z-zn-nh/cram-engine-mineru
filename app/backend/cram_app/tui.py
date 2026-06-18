from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog, Static

from .commands import CommandRouter
from .memory import MemoryStore
from .workspace import CramWorkspace, discover_workspace_sources


class CramTuiApp(App):
    CSS = """
    Screen {
        background: #0a0a0a;
        color: #eeeeee;
    }

    #status {
        dock: top;
        height: 1;
        padding: 0 1;
        background: #0a0a0a;
        color: #808080;
    }

    #chat {
        height: 1fr;
        padding: 1 3 0 3;
        background: #141414;
        color: #eeeeee;
    }

    #prompt {
        dock: bottom;
        height: 3;
        margin: 0 2;
        padding: 0 1 0 2;
        background: #1e1e1e;
        color: #eeeeee;
        border-left: thick #fab283;
        border-top: tall #323232;
    }

    #prompt:focus {
        border-left: thick #ffc09f;
        border-top: tall #606060;
    }

    #hints {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: #0a0a0a;
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
        yield Input(placeholder='Ask anything... "/mindmap sampling theorem"', id="prompt")
        yield Static(self._hint_text(), id="hints")

    def on_mount(self) -> None:
        chat = self.query_one("#chat", RichLog)
        chat.write("[bold #fab283]cram[/bold #fab283] [#808080]course agent[/#808080]")
        chat.write(f"[#808080]workspace[/#808080] {self.workspace.root}")
        boot_summary = self.memory.load_boot_summary().strip()
        if boot_summary:
            chat.write("[bold #5c9cf5]memory[/bold #5c9cf5]")
            chat.write(boot_summary)
        else:
            chat.write("[#808080]first run here. use[/#808080] [bold #fab283]/ingest[/bold #fab283] [#808080]or ask a question.[/#808080]")
        self.query_one("#prompt", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return

        chat = self.query_one("#chat", RichLog)
        chat.write(f"\n[bold #7fd88f]you[/bold #7fd88f]\n{text}")
        result = self.router.handle(text)
        if result.message:
            chat.write(f"\n[bold #5c9cf5]agent[/bold #5c9cf5]\n{result.message}")
        if result.wrote:
            wrote = "\n".join(path.relative_to(self.workspace.root).as_posix() for path in result.wrote)
            chat.write(f"\n[bold #f5a742]wrote[/bold #f5a742]\n{wrote}")
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

    def _hint_text(self) -> str:
        return "^l clear    ctrl+p commands    /help shortcuts    /status workspace"


def run_tui(workspace_path: Path | str = ".") -> None:
    CramTuiApp(workspace_path).run()
