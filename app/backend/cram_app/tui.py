from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Center, Middle, Vertical
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

    #home {
        height: 1fr;
        padding: 0 2;
        background: #141414;
        color: #eeeeee;
    }

    #home-card {
        width: 78;
        height: auto;
        padding: 1 2;
    }

    #home-prompt {
        width: 78;
        height: 3;
        margin-top: 1;
        padding: 0 1 0 2;
        background: #1e1e1e;
        color: #eeeeee;
        border: none;
        border-left: thick #fab283;
    }

    #home-prompt:focus {
        border: none;
        border-left: thick #ffc09f;
    }

    #session {
        height: 1fr;
        background: #141414;
    }

    .hidden {
        display: none;
    }

    #session-prompt {
        dock: bottom;
        height: 3;
        margin: 0 2 1 2;
        padding: 0 1 0 2;
        background: #1e1e1e;
        color: #eeeeee;
        border: none;
        border-left: thick #fab283;
    }

    #session-prompt:focus {
        border: none;
        border-left: thick #ffc09f;
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
        self._session_started = False

    def compose(self) -> ComposeResult:
        yield Static(self._status_text(), id="status")
        with Middle(id="home"):
            with Center():
                yield Static(self._home_text(), id="home-card")
                yield Input(placeholder='Ask anything... "/mindmap sampling theorem"', id="home-prompt")
        with Vertical(id="session", classes="hidden"):
            yield RichLog(id="chat", wrap=True, highlight=True, markup=True)
        yield Input(placeholder='Ask anything... "/mindmap sampling theorem"', id="session-prompt", classes="hidden")
        yield Static(self._hint_text(), id="hints")

    def on_mount(self) -> None:
        chat = self.query_one("#chat", RichLog)
        boot_summary = self.memory.load_boot_summary().strip()
        if boot_summary:
            chat.write("[bold #5c9cf5]memory[/bold #5c9cf5]")
            chat.write(boot_summary)
        else:
            chat.write("[#808080]first run here. use[/#808080] [bold #fab283]/ingest[/bold #fab283] [#808080]or ask a question.[/#808080]")
        self.query_one("#home-prompt", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        self._handle_prompt(text)

    def _handle_prompt(self, text: str) -> None:
        if not text:
            return

        self._enter_session()
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

    def _enter_session(self) -> None:
        if self._session_started:
            return
        self._session_started = True
        self.query_one("#home").add_class("hidden")
        self.query_one("#session").remove_class("hidden")
        self.query_one("#home-prompt").add_class("hidden")
        self.query_one("#session-prompt").remove_class("hidden")
        self.query_one("#session-prompt", Input).focus()
        chat = self.query_one("#chat", RichLog)
        chat.write("[bold #fab283]cram[/bold #fab283] [#808080]session[/#808080]")
        chat.write(f"[#808080]workspace[/#808080] {self.workspace.root}")

    def _status_text(self) -> str:
        source_count = len(discover_workspace_sources(self.workspace.root))
        output_count = len([path for path in self.workspace.output_dir.rglob("*") if path.is_file()])
        return (
            f"cram | {self.workspace.course_name} | {source_count} files | "
            f"{output_count} outputs | memory on | workspace {self.workspace.root}"
        )

    def _hint_text(self) -> str:
        return "^l clear    ctrl+p commands    /help shortcuts    /status workspace"

    def _logo_text(self) -> str:
        return "CRAM"

    def _home_text(self) -> str:
        return (
            "[bold #fab283]CRAM[/bold #fab283] [#808080]course agent[/#808080]\n\n"
            f"[#808080]workspace[/#808080] {self.workspace.root}\n"
            f"[#808080]course[/#808080] {self.workspace.course_name}\n\n"
            "[#eeeeee]Drop PDFs, PPTX, notes, and images into this folder.[/#eeeeee]\n"
            "[#808080]Then ask a question, or start with[/#808080] [bold #fab283]/ingest[/bold #fab283]"
        )


def run_tui(workspace_path: Path | str = ".") -> None:
    CramTuiApp(workspace_path).run()
