from __future__ import annotations
from functools import partial
from pathlib import Path
import os
import sys
import time

from rich.markup import escape
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.containers import Center, Middle, Vertical, VerticalScroll
from textual.theme import Theme
from textual.widgets import Button, Input, OptionList, Static
from textual.widgets.option_list import Option

from .commands import CommandRouter
from .llm import LLMRequestError, fetch_models
from .memory import MemoryStore
from .settings import (
    UserLLMConfig,
    load_user_llm_config,
    normalize_base_url,
    save_user_llm_config,
)
from .workspace import CramWorkspace, discover_workspace_sources


# OpenCode default palette (primary/secondary/accent confirmed from OpenCode docs);
# the gray scale already matched OpenCode's dark neutral steps. Single source of
# truth for both the registered theme and the chat markup so they stay in sync.
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

class _TuiCommandError:
    kind = "error"
    wrote: list[Path] = []

    def __init__(self, message: str):
        self.message = message


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
    ("/model", "切换对话模型"),
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
        layers: base overlay;
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

    .message {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    .message-role {
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    .message-body {
        width: 100%;
        height: auto;
    }

    .message-think {
        width: 100%;
        height: auto;
        color: #808080;
    }

    .message-reason {
        width: 100%;
        height: auto;
        color: #808080;
        margin-bottom: 1;
    }

    #command-menu {
        layer: overlay;
        dock: bottom;
        height: auto;
        max-height: 11;
        margin: 0 2 4 2;
        background: #141414;
        color: #eeeeee;
        border: none;
        border-left: thick #fab283;
        scrollbar-size-vertical: 1;
        scrollbar-background: #141414;
        scrollbar-background-hover: #141414;
        scrollbar-background-active: #141414;
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

    #setup-fetch {
        width: 20;
        margin-top: 1;
        background: #1e1e1e;
        color: #5c9cf5;
        border: none;
    }

    #setup-fetch:hover {
        background: #1e1e1e;
        color: #9d7cd8;
    }

    #setup-model-list {
        width: 78;
        height: auto;
        max-height: 10;
        margin-top: 1;
        background: #1e1e1e;
        color: #eeeeee;
        border: none;
        border-left: thick #9d7cd8;
        scrollbar-size-vertical: 1;
        scrollbar-background: #1e1e1e;
        scrollbar-background-hover: #1e1e1e;
        scrollbar-background-active: #1e1e1e;
        scrollbar-color: #2a2a2a;
        scrollbar-color-hover: #3a3a3a;
        scrollbar-color-active: #fab283;
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

    # ctrl+c is intentionally NOT bound to quit. Textual uses ctrl+c to copy the
    # current selection: a focused Input copies its own selection and, when empty,
    # bubbles up (SkipAction) to screen.copy_text, which copies the chat
    # drag-selection to the clipboard via OSC 52. Quit stays on ctrl+q.
    BINDINGS = [
        ("ctrl+q", "quit", "quit"),
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
        self._fetched_models: list[str] = []
        self._message_index = 0
        self._wrote_paths: list[Path] = []
        self._thinking: dict | None = None
        self._menu_commands: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static(self._status_text(), id="status")
        with Middle(id="llm-setup", classes="hidden" if not self._needs_llm_setup else None):
            with Center():
                yield Static(self._setup_text(), id="setup-card")
                yield Input(value=self._setup_api_key_default(), placeholder="API key", password=True, id="setup-api-key", classes="setup-input")
                yield Input(
                    value=self._setup_base_url_default(),
                    placeholder="Base URL",
                    id="setup-base-url",
                    classes="setup-input",
                )
                yield Button("Fetch models", id="setup-fetch")
                yield OptionList(id="setup-model-list", classes="hidden")
                yield Input(value=self._setup_model_default(), placeholder="Model (或在上方列表选择)", id="setup-model", classes="setup-input")
                yield Button("Save", id="setup-save")
                yield Static("", id="setup-message")
        with Middle(id="home", classes="hidden" if self._needs_llm_setup else None):
            with Center():
                yield Static(self._logo_text(), id="home-logo")
                yield Static(self._home_text(), id="home-card")
                yield Input(placeholder='Ask anything... "/mindmap sampling theorem"', id="home-prompt")
        with Vertical(id="session", classes="hidden"):
            yield VerticalScroll(id="chat")
        yield OptionList(id="command-menu", classes="hidden")
        yield Input(placeholder='Ask anything... "/mindmap sampling theorem"', id="session-prompt", classes="hidden")
        yield Static(self._hint_text(), id="hints")

    def on_mount(self) -> None:
        self.register_theme(OPENCODE_THEME)
        self.theme = "opencode"
        self._think_timer = self.set_interval(0.1, self._tick_thinking, pause=True)
        boot_summary = self.memory.load_boot_summary().strip()
        if boot_summary:
            self._append_message("memory", boot_summary, color=PALETTE["accent"])
        else:
            self._append_message("cram", "first run here. use /ingest or ask a question.", color=PALETTE["muted"])
        if self._needs_llm_setup:
            self.query_one("#setup-api-key", Input).focus()
        else:
            self.query_one("#home-prompt", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "setup-api-key":
            self.query_one("#setup-base-url", Input).focus()
            return
        if event.input.id == "setup-base-url":
            self._trigger_fetch_models()
            return
        if event.input.id == "setup-model":
            self._save_llm_setup()
            return
        if event.input.id in {"home-prompt", "session-prompt"} and self._command_menu_visible():
            self._run_highlighted_command()
            return
        text = event.value.strip()
        event.input.value = ""
        self._handle_prompt(text)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id not in {"home-prompt", "session-prompt"}:
            return
        if self._session_started:
            self._scroll_chat_to_bottom()
        value = event.value
        matches = self._filtered_commands(value)
        if matches:
            self._show_command_menu(matches)
            return
        self._hide_command_menu()

    def on_key(self, event) -> None:
        if not self._command_menu_visible():
            return
        focused = self.focused
        if focused is None or getattr(focused, "id", None) not in {"home-prompt", "session-prompt"}:
            return
        menu = self.query_one("#command-menu", OptionList)
        if event.key == "down":
            menu.action_cursor_down()
            event.prevent_default()
            event.stop()
        elif event.key == "up":
            menu.action_cursor_up()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self._hide_command_menu()
            event.prevent_default()
            event.stop()

    def _command_menu_visible(self) -> bool:
        return bool(self._menu_commands) and not self.query_one("#command-menu", OptionList).has_class("hidden")

    def _hide_command_menu(self) -> None:
        self._menu_commands = []
        self.query_one("#command-menu", OptionList).add_class("hidden")

    def _filtered_commands(self, value: str) -> list[tuple[str, str]]:
        if not value.startswith("/") or " " in value:
            return []
        query = value[1:].strip().lower()
        if not query:
            return PALETTE_COMMANDS
        command_matches = [
            (command, description)
            for command, description in PALETTE_COMMANDS
            if command.lstrip("/").lower().startswith(query)
        ]
        if command_matches:
            return command_matches
        return [
            (command, description)
            for command, description in PALETTE_COMMANDS
            if query in description.lower()
        ]

    def _show_command_menu(self, matches: list[tuple[str, str]]) -> None:
        menu = self.query_one("#command-menu", OptionList)
        self._menu_commands = [command for command, _ in matches]
        menu.clear_options()
        menu.add_options([Option(f"{command:<10} {description}") for command, description in matches])
        menu.remove_class("hidden")
        menu.highlighted = 0
        menu.refresh(layout=True)

    def _run_highlighted_command(self) -> None:
        menu = self.query_one("#command-menu", OptionList)
        index = menu.highlighted or 0
        if 0 <= index < len(self._menu_commands):
            command = self._menu_commands[index]
            focused = self.focused
            if focused is not None and getattr(focused, "id", None) in {"home-prompt", "session-prompt"}:
                focused.value = ""
            self._hide_command_menu()
            self._handle_prompt(command)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "setup-fetch":
            self._trigger_fetch_models()
        elif event.button.id == "setup-save":
            self._save_llm_setup()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "command-menu":
            if 0 <= event.option_index < len(self._menu_commands):
                command = self._menu_commands[event.option_index]
                focused = self.focused
                if focused is not None and getattr(focused, "id", None) in {"home-prompt", "session-prompt"}:
                    focused.value = ""
                self._hide_command_menu()
                self._handle_prompt(command)
            return
        if event.option_list.id != "setup-model-list":
            return
        if 0 <= event.option_index < len(self._fetched_models):
            self.query_one("#setup-model", Input).value = self._fetched_models[event.option_index]
            self._save_llm_setup()

    def _run_command(self, command: str) -> None:
        self._handle_prompt(command)

    def _handle_prompt(self, text: str) -> None:
        if not text:
            return

        command = text.split(maxsplit=1)[0].lower()
        if command in {"/config", "/model", "/help", "/status", "/lint", "/ingest", "/plan", "/notes", "/mindmap", "/quiz", "/summary"}:
            if command == "/config":
                self._open_llm_setup(auto_fetch=False)
                return
            if command == "/model":
                self._open_llm_setup(auto_fetch=True)
                return

            self._enter_session()
            self._write_user(text)
            pending = self._write_agent("正在处理...")
            self._run_command_worker(text, pending.id or "")
            return

        self._enter_session()
        self._write_user(text)
        if hasattr(self.router, "run_turn"):
            ids = self._write_agent_stream()
            self._run_prompt_worker(text, ids)
        else:
            pending = self._write_agent("thinking…")
            self._run_blocking_worker(text, pending.id or "")

    @work(exclusive=False, thread=True)
    def _run_command_worker(self, text: str, message_id: str) -> None:
        try:
            result = self.router.handle(text)
        except Exception as exc:
            result = _TuiCommandError(f"命令执行失败：\n{exc}")
        self.call_from_thread(self._finish_prompt, result, message_id)

    @work(exclusive=False, thread=True)
    def _run_prompt_worker(self, text: str, ids: dict) -> None:
        start = time.monotonic()
        self.call_from_thread(self._begin_thinking, ids["think"], start)
        reasoning_parts: list[str] = ["准备上下文，等待模型返回…"]
        content_parts: list[str] = []
        wrote_paths: list[Path] = []
        first_content = False
        saw_model_reasoning = False
        try:
            self.call_from_thread(self._update_reasoning, ids["reason"], "".join(reasoning_parts))
            for event in self.router.run_turn(text):
                if event.kind == "reasoning":
                    if not saw_model_reasoning:
                        saw_model_reasoning = True
                        reasoning_parts.append("\n模型返回的思考内容：\n")
                    reasoning_parts.append(event.text)
                    self.call_from_thread(self._update_reasoning, ids["reason"], "".join(reasoning_parts))
                elif event.kind == "tool":
                    reasoning_parts.append(f"\n↪ {event.text}…\n")
                    self.call_from_thread(self._update_reasoning, ids["reason"], "".join(reasoning_parts))
                elif event.kind == "wrote":
                    wrote_paths.append(Path(event.text))
                else:
                    if not first_content:
                        first_content = True
                        self.call_from_thread(
                            self._end_thinking,
                            ids["think"],
                            time.monotonic() - start,
                            ids["reason"],
                            ids["index"],
                        )
                    content_parts.append(event.text)
                    self.call_from_thread(self._update_message, ids["answer"], "".join(content_parts))
        except Exception as exc:
            self.call_from_thread(self._end_thinking, ids["think"], time.monotonic() - start, ids["reason"], ids["index"])
            self.call_from_thread(self._update_message, ids["answer"], f"LLM 请求失败，当前会话已保留。\n{exc}")
        finally:
            self.call_from_thread(self._end_thinking, ids["think"], time.monotonic() - start, ids["reason"], ids["index"])
            if wrote_paths:
                self.call_from_thread(self._write_wrote, wrote_paths)
            self.call_from_thread(self._refresh_after_prompt)

    @work(exclusive=False, thread=True)
    def _run_blocking_worker(self, text: str, message_id: str) -> None:
        result = self.router.handle(text)
        self.call_from_thread(self._finish_prompt, result, message_id)

    def _finish_prompt(self, result, message_id: str) -> None:
        if result.kind == "config":
            self._open_llm_setup(auto_fetch=False)
            return
        if result.kind == "model":
            self._open_llm_setup(auto_fetch=True)
            return
        if result.message:
            self._update_message(message_id, result.message)
        else:
            self._update_message(message_id, "")
        if result.wrote:
            self._write_wrote(result.wrote)
        self.query_one("#status", Static).update(self._status_text())
        self._focus_session_prompt()

    def _focus_session_prompt(self) -> None:
        self.query_one("#session-prompt", Input).focus()

    def _refresh_after_prompt(self) -> None:
        self.query_one("#status", Static).update(self._status_text())
        self._focus_session_prompt()

    def _write_user(self, text: str) -> None:
        self._append_message("you", text, color=PALETTE["secondary"])

    def _write_agent(self, text: str) -> Static:
        return self._append_message("cram", text, color=PALETTE["primary"])

    def _write_agent_stream(self) -> dict:
        self._message_index += 1
        index = self._message_index
        container = Vertical(
            Static(f"[bold {PALETTE['primary']}]▌ cram[/bold {PALETTE['primary']}]", classes="message-role"),
            Static("", id=f"think-{index}", classes="message-think"),
            Static(Text(""), id=f"reason-{index}", classes="message-reason hidden"),
            Static(Text(""), id=f"message-{index}", classes="message-body"),
            classes="message",
        )
        self.query_one("#chat", VerticalScroll).mount(container)
        self._scroll_chat_to_bottom()
        return {"index": index, "think": f"think-{index}", "reason": f"reason-{index}", "answer": f"message-{index}"}

    def _begin_thinking(self, think_id: str, start: float) -> None:
        self._thinking = {"id": think_id, "start": start, "active": True}
        self.query_one(f"#{think_id}", Static).update("[#808080]● 思考中… 0s[/#808080]")
        self._think_timer.resume()

    def _tick_thinking(self) -> None:
        if not self._thinking or not self._thinking.get("active"):
            return
        elapsed = time.monotonic() - self._thinking["start"]
        try:
            self.query_one(f"#{self._thinking['id']}", Static).update(
                f"[#808080]● 思考中… {elapsed:.0f}s[/#808080]"
            )
        except Exception:
            pass

    def _end_thinking(self, think_id: str, seconds: float, reason_id: str | None = None, index: int | None = None) -> None:
        if not (self._thinking and self._thinking.get("id") == think_id and self._thinking.get("active")):
            return
        self._thinking["active"] = False
        self._think_timer.pause()
        seconds_text = f"{seconds:.0f}s"
        has_reasoning = False
        if reason_id:
            try:
                reason = self.query_one(f"#{reason_id}", Static)
                has_reasoning = bool(str(reason.content).strip())
                if has_reasoning:
                    reason.add_class("hidden")
            except Exception:
                has_reasoning = False
        try:
            self.query_one(f"#{think_id}", Static).update(f"[#7fd88f]✓ 思考 {seconds_text}[/#7fd88f]")
        except Exception:
            pass

    def _update_reasoning(self, reason_id: str, text: str) -> None:
        widget = self.query_one(f"#{reason_id}", Static)
        widget.remove_class("hidden")
        widget.update(Text(text, style="#808080"))
        self._scroll_chat_to_bottom()

    def _write_wrote(self, paths: list[Path]) -> None:
        links: list[str] = []
        for path in paths:
            index = len(self._wrote_paths)
            self._wrote_paths.append(path.resolve())
            rel = escape(path.relative_to(self.workspace.root).as_posix())
            links.append(f"  [@click=open_artifact({index})][u]{rel}[/u][/]")
        self._append_message("wrote", "\n".join(links), color=PALETTE["accent"], markup=True)

    def action_open_artifact(self, index: int) -> None:
        if 0 <= index < len(self._wrote_paths):
            path = self._wrote_paths[index]
            try:
                os.startfile(str(path))  # noqa: S606 - Windows shell open of a workspace artifact
            except Exception as exc:
                self.notify(f"无法打开 {path}: {exc}", severity="error")

    def _write_system(self, text: str) -> None:
        self._append_message("cram", text, color=PALETTE["accent"])

    def _append_message(self, role: str, text: str, *, color: str, markup: bool = False) -> Static:
        self._message_index += 1
        body = Static(
            text if markup else Text(text),
            id=f"message-{self._message_index}",
            classes="message-body",
        )
        container = Vertical(
            Static(f"[bold {color}]▌ {role}[/bold {color}]", classes="message-role"),
            body,
            classes="message",
        )
        self.query_one("#chat", VerticalScroll).mount(container)
        self._scroll_chat_to_bottom()
        return body

    def _update_message(self, message_id: str, text: str) -> None:
        if not message_id:
            return
        self.query_one(f"#{message_id}", Static).update(Text(text))
        self._scroll_chat_to_bottom()

    def _scroll_chat_to_bottom(self) -> None:
        try:
            chat = self.query_one("#chat", VerticalScroll)
        except Exception:
            return

        def scroll() -> None:
            try:
                chat.scroll_end(animate=False, immediate=True)
            except Exception:
                pass

        scroll()
        self.call_after_refresh(scroll)

    def _trigger_fetch_models(self) -> None:
        api_key = self.query_one("#setup-api-key", Input).value.strip()
        raw_base_url = self.query_one("#setup-base-url", Input).value.strip() or "https://api.openai.com/v1"
        base_url = normalize_base_url(raw_base_url)
        message = self.query_one("#setup-message", Static)
        if not api_key:
            message.update("先填 API key 再拉取模型")
            self.query_one("#setup-api-key", Input).focus()
            return
        if not base_url:
            message.update("Base URL 必须以 http:// 或 https:// 开头")
            self.query_one("#setup-base-url", Input).focus()
            return
        message.update("正在拉取模型列表…")
        self._fetch_models_worker(base_url, api_key)

    @work(exclusive=True, thread=True)
    def _fetch_models_worker(self, base_url: str, api_key: str) -> None:
        try:
            models = fetch_models(base_url, api_key)
        except LLMRequestError as exc:
            self.call_from_thread(self._on_models_error, str(exc))
            return
        self.call_from_thread(self._on_models_loaded, models)

    def _on_models_loaded(self, models: list[str]) -> None:
        self._fetched_models = models
        option_list = self.query_one("#setup-model-list", OptionList)
        option_list.clear_options()
        option_list.add_options([Option(model) for model in models])
        option_list.remove_class("hidden")
        self.query_one("#setup-message", Static).update(
            f"已拉取 {len(models)} 个模型，↑↓ 选择回车确认（也可手动输入）"
        )
        option_list.focus()

    def _on_models_error(self, error: str) -> None:
        self._fetched_models = []
        self.query_one("#setup-model-list", OptionList).add_class("hidden")
        self.query_one("#setup-message", Static).update(
            f"拉取模型失败，可手动输入模型名。{error}"
        )
        self.query_one("#setup-model", Input).focus()

    def _open_llm_setup(self, *, auto_fetch: bool = False) -> None:
        config = load_user_llm_config()
        self.query_one("#setup-api-key", Input).value = config.api_key if config else ""
        self.query_one("#setup-base-url", Input).value = config.base_url if config else "https://api.openai.com/v1"
        self.query_one("#setup-model", Input).value = config.model if config else "gpt-4o-mini"
        self.query_one("#setup-message", Static).update("")
        self.query_one("#setup-model-list", OptionList).add_class("hidden")
        self.query_one("#home").add_class("hidden")
        self.query_one("#session").add_class("hidden")
        self.query_one("#home-prompt").add_class("hidden")
        self.query_one("#session-prompt").add_class("hidden")
        self.query_one("#llm-setup").remove_class("hidden")
        if auto_fetch:
            self._trigger_fetch_models()
        else:
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
        message.update("")
        self.query_one("#setup-model-list", OptionList).add_class("hidden")
        self.query_one("#llm-setup").add_class("hidden")
        if self._session_started:
            self.query_one("#session").remove_class("hidden")
            self.query_one("#session-prompt").remove_class("hidden")
            self._write_system(f"已更新配置 · 模型 {model}")
            self.query_one("#session-prompt", Input).focus()
        else:
            self.query_one("#home").remove_class("hidden")
            self.query_one("#home-prompt", Input).focus()

    def action_clear_chat(self) -> None:
        self.query_one("#chat", VerticalScroll).remove_children(".message")

    def _enter_session(self) -> None:
        if self._session_started:
            return
        self._session_started = True
        self.query_one("#home").add_class("hidden")
        self.query_one("#session").remove_class("hidden")
        self.query_one("#home-prompt").add_class("hidden")
        self.query_one("#session-prompt").remove_class("hidden")
        self.query_one("#session-prompt", Input).focus()
        self._append_message("cram", f"session\nworkspace {self.workspace.root}", color=PALETTE["primary"])

    def _status_text(self) -> str:
        source_count = len(discover_workspace_sources(self.workspace.root))
        output_count = len([path for path in self.workspace.output_dir.rglob("*") if path.is_file()])
        return (
            f"cram · {self.workspace.course_name} · {source_count} files · "
            f"{output_count} outputs · memory on · workspace {self.workspace.root}"
        )

    def _hint_text(self) -> str:
        return "^q quit    ^l clear    drag+^c copy    ctrl+p commands    /help"

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

    def _setup_api_key_default(self) -> str:
        config = load_user_llm_config()
        return config.api_key if config else ""

    def _setup_base_url_default(self) -> str:
        config = load_user_llm_config()
        return config.base_url if config else "https://api.openai.com/v1"

    def _setup_model_default(self) -> str:
        config = load_user_llm_config()
        return config.model if config else "gpt-4o-mini"


def _has_llm_config() -> bool:
    # Only an in-app saved config (llm.json) skips the first-run setup page.
    # Env vars remain a fallback for the client and prefill the form, but never suppress setup.
    return bool(load_user_llm_config())


def terminal_title_for_workspace(workspace_path: Path | str = ".") -> str:
    workspace = CramWorkspace.open(workspace_path)
    return f"cram - {workspace.root}"


def terminal_title_escape(title: str) -> str:
    return f"\033]0;{title}\a"


def run_tui(workspace_path: Path | str = ".") -> None:
    sys.stdout.write(terminal_title_escape(terminal_title_for_workspace(workspace_path)))
    sys.stdout.flush()
    CramTuiApp(workspace_path).run()
