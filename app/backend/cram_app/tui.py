from __future__ import annotations

import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.widgets import Button, Input, RichLog, Static

from .commands import CommandRouter
from .memory import MemoryStore
from .settings import UserLLMConfig, load_user_llm_config, save_user_llm_config
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

    #llm-setup {
        height: 1fr;
        padding: 0 2;
        background: #141414;
        color: #eeeeee;
    }

    #setup-card {
        width: 78;
        height: auto;
        padding: 1 2;
    }

    .setup-input {
        width: 78;
        height: 3;
        margin-top: 1;
        padding: 0 1 0 2;
        background: #1e1e1e;
        color: #eeeeee;
        border: none;
        border-left: thick #fab283;
    }

    .setup-input:focus {
        border: none;
        border-left: thick #ffc09f;
    }

    #setup-save {
        width: 18;
        margin-top: 1;
    }

    #setup-message {
        width: 78;
        height: auto;
        margin-top: 1;
        color: #fab283;
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
        self._needs_llm_setup = not _has_llm_config()

    def compose(self) -> ComposeResult:
        yield Static(self._status_text(), id="status")
        with Middle(id="llm-setup", classes="hidden" if not self._needs_llm_setup else None):
            with Center():
                yield Static(self._setup_text(), id="setup-card")
                yield Input(placeholder="API key", password=True, id="setup-api-key", classes="setup-input")
                yield Input(
                    value="https://api.openai.com/v1",
                    placeholder="Base URL",
                    id="setup-base-url",
                    classes="setup-input",
                )
                yield Input(value="gpt-4o-mini", placeholder="Model", id="setup-model", classes="setup-input")
                yield Button("Save", id="setup-save")
                yield Static("", id="setup-message")
        with Middle(id="home", classes="hidden" if self._needs_llm_setup else None):
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
        if self._needs_llm_setup:
            self.query_one("#setup-api-key", Input).focus()
        else:
            self.query_one("#home-prompt", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"setup-api-key", "setup-base-url", "setup-model"}:
            self._save_llm_setup()
            return
        text = event.value.strip()
        event.input.value = ""
        self._handle_prompt(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "setup-save":
            self._save_llm_setup()

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

    def _save_llm_setup(self) -> None:
        api_key = self.query_one("#setup-api-key", Input).value.strip()
        base_url = self.query_one("#setup-base-url", Input).value.strip() or "https://api.openai.com/v1"
        model = self.query_one("#setup-model", Input).value.strip() or "gpt-4o-mini"
        message = self.query_one("#setup-message", Static)
        if not api_key:
            message.update("API key 不能为空")
            self.query_one("#setup-api-key", Input).focus()
            return

        save_user_llm_config(UserLLMConfig(api_key=api_key, base_url=base_url, model=model))
        self.router = CommandRouter(self.workspace)
        self._needs_llm_setup = False
        self.query_one("#llm-setup").add_class("hidden")
        self.query_one("#home").remove_class("hidden")
        message.update("")
        self.query_one("#home-prompt", Input).focus()

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

    def _setup_text(self) -> str:
        return (
            "[bold #fab283]CRAM[/bold #fab283] [#808080]LLM setup[/#808080]\n\n"
            "输入 OpenAI-compatible 模型配置。保存后会进入复习页面。\n"
            "[#808080]配置保存在用户目录，不写入当前课程文件夹。[/#808080]"
        )


def _has_llm_config() -> bool:
    return bool(os.environ.get("CRAM_LLM_API_KEY") or load_user_llm_config())


def run_tui(workspace_path: Path | str = ".") -> None:
    CramTuiApp(workspace_path).run()
