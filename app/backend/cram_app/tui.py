from __future__ import annotations
from functools import partial
from pathlib import Path

from textual.app import App, ComposeResult
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.containers import Center, Middle, Vertical
from textual.theme import Theme
from textual.widgets import Button, Input, RichLog, Static

from .commands import CommandRouter
from .memory import MemoryStore
from .settings import UserLLMConfig, load_effective_llm_config, normalize_base_url, save_user_llm_config
from .workspace import CramWorkspace, discover_workspace_sources


# OpenCode default palette (primary/secondary/accent confirmed from OpenCode docs);
# the gray scale already matched OpenCode's dark neutral steps. Single source of
# truth for both the registered theme and the RichLog chat markup so they stay in sync.
PALETTE = {
    "base": "#0a0a0a",
    "surface": "#141414",
    "panel": "#1e1e1e",
    "text": "#eeeeee",
    "muted": "#808080",
    "primary": "#fab283",
    "primary_focus": "#ffc09f",
    "secondary": "#5c9cf5",
    "accent": "#9d7cd8",
    "success": "#7fd88f",
    "warning": "#e5c07b",
    "error": "#e06c75",
    "border": "#2a2a2a",
}

OPENCODE_THEME = Theme(
    name="opencode",
    primary=PALETTE["primary"],
    secondary=PALETTE["secondary"],
    accent=PALETTE["accent"],
    success=PALETTE["success"],
    warning=PALETTE["warning"],
    error=PALETTE["error"],
    foreground=PALETTE["text"],
    background=PALETTE["base"],
    surface=PALETTE["surface"],
    panel=PALETTE["panel"],
    dark=True,
    variables={
        "text-muted": PALETTE["muted"],
        "input-cursor-background": PALETTE["primary"],
        "border": PALETTE["border"],
    },
)

# Slash commands surfaced in the ctrl+p palette (kept aligned with commands.HELP_TEXT).
PALETTE_COMMANDS = [
    ("/ingest", "解析并索引当前文件夹资料"),
    ("/status", "查看资料、记忆和输出状态"),
    ("/plan", "生成速成计划"),
    ("/notes", "生成知识点整合"),
    ("/mindmap", "生成思维导图"),
    ("/quiz", "生成题库"),
    ("/summary", "生成考前总结"),
    ("/lint", "检查记忆、输出和引用冲突"),
    ("/config", "重新配置 LLM"),
    ("/help", "查看命令"),
]


class CramCommands(Provider):
    """Feed cram's slash commands into Textual's built-in ctrl+p palette."""

    async def discover(self) -> Hits:
        for command, description in PALETTE_COMMANDS:
            yield DiscoveryHit(
                f"{command}  {description}",
                partial(self.app._run_command, command),
                text=command,
                help=description,
            )

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for command, description in PALETTE_COMMANDS:
            candidate = f"{command}  {description}"
            score = matcher.match(candidate)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(candidate),
                    partial(self.app._run_command, command),
                    text=command,
                    help=description,
                )


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
        background: #0a0a0a;
        color: #eeeeee;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
        scrollbar-background: #0a0a0a;
        scrollbar-background-hover: #0a0a0a;
        scrollbar-background-active: #0a0a0a;
        scrollbar-color: #2a2a2a;
        scrollbar-color-hover: #3a3a3a;
        scrollbar-color-active: #fab283;
    }

    #home {
        height: 1fr;
        padding: 0 2;
        background: #0a0a0a;
        color: #eeeeee;
    }

    #llm-setup {
        height: 1fr;
        padding: 0 2;
        background: #0a0a0a;
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
        padding: 1 1 1 2;
        background: #1e1e1e;
        color: #eeeeee;
        border: none;
        border-left: thick #fab283;
    }

    .setup-input:focus {
        border: none;
        border-left: thick #9d7cd8;
    }

    #setup-save {
        width: 18;
        margin-top: 1;
        background: #1e1e1e;
        color: #fab283;
        border: none;
    }

    #setup-save:hover {
        background: #1e1e1e;
        color: #ffc09f;
    }

    #setup-message {
        width: 78;
        height: auto;
        margin-top: 1;
        color: #fab283;
    }

    #home-logo {
        width: auto;
        height: auto;
        color: #fab283;
        text-align: center;
        margin-bottom: 1;
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
        padding: 1 1 1 2;
        background: #1e1e1e;
        color: #eeeeee;
        border: none;
        border-left: thick #fab283;
    }

    #home-prompt:focus {
        border: none;
        border-left: thick #9d7cd8;
    }

    #session {
        height: 1fr;
        background: #0a0a0a;
    }

    .hidden {
        display: none;
    }

    #session-prompt {
        dock: bottom;
        height: 3;
        margin: 0 2 1 2;
        padding: 1 1 1 2;
        background: #1e1e1e;
        color: #eeeeee;
        border: none;
        border-left: thick #fab283;
    }

    #session-prompt:focus {
        border: none;
        border-left: thick #9d7cd8;
    }

    #hints {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: #0a0a0a;
        color: #808080;
    }
    """

    COMMANDS = App.COMMANDS | {CramCommands}

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
                    value=self._setup_base_url_default(),
                    placeholder="Base URL",
                    id="setup-base-url",
                    classes="setup-input",
                )
                yield Input(value=self._setup_model_default(), placeholder="Model", id="setup-model", classes="setup-input")
                yield Button("Save", id="setup-save")
                yield Static("", id="setup-message")
        with Middle(id="home", classes="hidden" if self._needs_llm_setup else None):
            with Center():
                yield Static(self._logo_text(), id="home-logo")
                yield Static(self._home_text(), id="home-card")
                yield Input(placeholder='Ask anything... "/mindmap sampling theorem"', id="home-prompt")
        with Vertical(id="session", classes="hidden"):
            yield RichLog(id="chat", wrap=True, highlight=True, markup=True)
        yield Input(placeholder='Ask anything... "/mindmap sampling theorem"', id="session-prompt", classes="hidden")
        yield Static(self._hint_text(), id="hints")

    def on_mount(self) -> None:
        self.register_theme(OPENCODE_THEME)
        self.theme = "opencode"
        chat = self.query_one("#chat", RichLog)
        boot_summary = self.memory.load_boot_summary().strip()
        if boot_summary:
            chat.write("[bold #9d7cd8]▌ memory[/bold #9d7cd8]")
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

    def _run_command(self, command: str) -> None:
        self._handle_prompt(command)

    def _handle_prompt(self, text: str) -> None:
        if not text:
            return

        result = self.router.handle(text)
        if result.kind == "config":
            self._open_llm_setup()
            return

        self._enter_session()
        self._write_user(text)
        if result.message:
            self._write_agent(result.message)
        if result.wrote:
            self._write_wrote(result.wrote)
        self.query_one("#status", Static).update(self._status_text())

    def _write_user(self, text: str) -> None:
        chat = self.query_one("#chat", RichLog)
        chat.write("")
        chat.write("[bold #5c9cf5]▌ you[/bold #5c9cf5]")
        chat.write(text)

    def _write_agent(self, text: str) -> None:
        chat = self.query_one("#chat", RichLog)
        chat.write("")
        chat.write("[bold #fab283]▌ cram[/bold #fab283]")
        chat.write(text)

    def _write_wrote(self, paths: list[Path]) -> None:
        chat = self.query_one("#chat", RichLog)
        rels = "\n".join(
            f"  {path.relative_to(self.workspace.root).as_posix()}" for path in paths
        )
        chat.write("")
        chat.write("[bold #9d7cd8]▌ wrote[/bold #9d7cd8]")
        chat.write(f"[#9d7cd8]{rels}[/#9d7cd8]")

    def _open_llm_setup(self) -> None:
        config = load_effective_llm_config()
        self.query_one("#setup-api-key", Input).value = config.api_key if config else ""
        self.query_one("#setup-base-url", Input).value = config.base_url if config else "https://api.openai.com/v1"
        self.query_one("#setup-model", Input).value = config.model if config else "gpt-4o-mini"
        self.query_one("#setup-message", Static).update("")
        self.query_one("#home").add_class("hidden")
        self.query_one("#session").add_class("hidden")
        self.query_one("#home-prompt").add_class("hidden")
        self.query_one("#session-prompt").add_class("hidden")
        self.query_one("#llm-setup").remove_class("hidden")
        self.query_one("#setup-api-key", Input).focus()

    def _save_llm_setup(self) -> None:
        api_key = self.query_one("#setup-api-key", Input).value.strip()
        raw_base_url = self.query_one("#setup-base-url", Input).value.strip() or "https://api.openai.com/v1"
        base_url = normalize_base_url(raw_base_url)
        model = self.query_one("#setup-model", Input).value.strip() or "gpt-4o-mini"
        message = self.query_one("#setup-message", Static)
        if not api_key:
            message.update("API key 不能为空")
            self.query_one("#setup-api-key", Input).focus()
            return
        if not base_url:
            message.update("Base URL 必须以 http:// 或 https:// 开头")
            self.query_one("#setup-base-url", Input).focus()
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
        chat.write("[bold #fab283]▌ cram[/bold #fab283] [#808080]session[/#808080]")
        chat.write(f"[#808080]workspace[/#808080] {self.workspace.root}")

    def _status_text(self) -> str:
        source_count = len(discover_workspace_sources(self.workspace.root))
        output_count = len([path for path in self.workspace.output_dir.rglob("*") if path.is_file()])
        return (
            f"cram · {self.workspace.course_name} · {source_count} files · "
            f"{output_count} outputs · memory on · workspace {self.workspace.root}"
        )

    def _hint_text(self) -> str:
        return "^l clear    ctrl+p commands    /help shortcuts    /status workspace"

    def _logo_text(self) -> str:
        banner = (
            " ██████╗██████╗  █████╗ ███╗   ███╗\n"
            "██╔════╝██╔══██╗██╔══██╗████╗ ████║\n"
            "██║     ██████╔╝███████║██╔████╔██║\n"
            "██║     ██╔══██╗██╔══██║██║╚██╔╝██║\n"
            "╚██████╗██║  ██║██║  ██║██║ ╚═╝ ██║\n"
            " ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝"
        )
        return f"{banner}\nCRAM · course agent"

    def _home_text(self) -> str:
        return f"[#808080]{self.workspace.root}[/#808080]"

    def _setup_text(self) -> str:
        return (
            "[bold #fab283]CRAM[/bold #fab283] [#808080]LLM setup[/#808080]\n\n"
            "输入 OpenAI-compatible 模型配置。保存后会进入复习页面。\n"
            "[#808080]配置保存在用户目录，不写入当前课程文件夹。[/#808080]"
        )

    def _setup_base_url_default(self) -> str:
        config = load_effective_llm_config()
        return config.base_url if config else "https://api.openai.com/v1"

    def _setup_model_default(self) -> str:
        config = load_effective_llm_config()
        return config.model if config else "gpt-4o-mini"


def _has_llm_config() -> bool:
    return bool(load_effective_llm_config())


def run_tui(workspace_path: Path | str = ".") -> None:
    CramTuiApp(workspace_path).run()
