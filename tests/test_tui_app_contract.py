import importlib
import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.containers import VerticalScroll
from textual.widgets import Input

from app.backend.cram_app.commands import CommandResult
from app.backend.cram_app.llm import StreamEvent


ROOT = Path(__file__).resolve().parents[1]


class TuiAppContractTests(unittest.TestCase):
    def test_textual_dependency_is_declared(self):
        requirements = (ROOT / "app" / "backend" / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("textual", requirements)

    def test_tui_app_exports_opencode_style_app(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        self.assertTrue(hasattr(module, "CramTuiApp"))
        self.assertTrue(hasattr(module, "run_tui"))

    def test_cram_entrypoint_exists(self):
        entrypoint = ROOT / "app" / "backend" / "cram.py"

        self.assertTrue(entrypoint.is_file())
        self.assertIn("run_tui", entrypoint.read_text(encoding="utf-8"))

    def test_status_bar_shows_absolute_workspace_path(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "signals"
            app = module.CramTuiApp(workspace_root)
            status = app._status_text()

            self.assertIn(str(workspace_root.resolve()), status)
            self.assertNotIn("cwd workspace", status)

    def test_run_tui_sets_terminal_title_to_workspace_path(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "course"
            title = module.terminal_title_for_workspace(workspace_root)

            self.assertIn(str(workspace_root.resolve()), title)
            self.assertNotIn("System32", title)
            self.assertEqual(module.terminal_title_escape(title), f"\x1b]0;{title}\x07")

    def test_tui_css_uses_compact_opencode_style_surface(self):
        module = importlib.import_module("app.backend.cram_app.tui")
        css = module.CramTuiApp.CSS

        self.assertIn("#0a0a0a", css)
        self.assertIn("#1e1e1e", css)
        self.assertIn("border-left", css)
        self.assertIn("#hints", css)
        self.assertNotIn("background: #0f172a", css)

    def test_tui_uses_custom_prompt_chrome_instead_of_textual_footer(self):
        module = importlib.import_module("app.backend.cram_app.tui")
        source = (ROOT / "app" / "backend" / "cram_app" / "tui.py").read_text(encoding="utf-8")

        self.assertNotIn("Footer", source)
        self.assertIn('id="hints"', source)
        self.assertIn("ctrl+p commands", module.CramTuiApp()._hint_text())

    def test_tui_uses_opencode_home_then_session_mode(self):
        module = importlib.import_module("app.backend.cram_app.tui")
        source = (ROOT / "app" / "backend" / "cram_app" / "tui.py").read_text(encoding="utf-8")
        app = module.CramTuiApp()

        self.assertIn('id="home"', source)
        self.assertIn('id="session"', source)
        self.assertIn("_enter_session", source)
        self.assertIn("CRAM", app._logo_text())
        self.assertIn(str(app.workspace.root), app._home_text())

    def test_tui_chat_uses_selectable_updatable_message_widgets(self):
        source = (ROOT / "app" / "backend" / "cram_app" / "tui.py").read_text(encoding="utf-8")

        self.assertIn("VerticalScroll", source)
        self.assertNotIn("RichLog", source)
        self.assertIn("_run_prompt_worker", source)

    def test_tui_shows_user_message_before_slow_agent_finishes(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        class SlowRouter:
            def handle(self, text):
                time.sleep(0.5)
                return CommandResult(kind="ask", message="slow answer")

        async def submit_prompt():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps(
                        {
                            "api_key": "secret",
                            "base_url": "https://api.example.com/v1",
                            "model": "test-model",
                        }
                    ),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    app.router = SlowRouter()
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.press("h", "i", "enter")
                        await pilot.pause(0.1)
                        return [node.content for node in app.query("#chat .message-body")]

        renderables = asyncio.run(submit_prompt())
        joined = "\n".join(str(item) for item in renderables)

        self.assertIn("hi", joined)
        self.assertIn("thinking", joined)

    def test_tui_shows_feedback_before_slow_slash_command_finishes(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        class SlowRouter:
            def handle(self, text):
                time.sleep(0.5)
                return CommandResult(kind="ingest", message="done")

        async def submit_command():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps(
                        {
                            "api_key": "secret",
                            "base_url": "https://api.example.com/v1",
                            "model": "test-model",
                        }
                    ),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    app.router = SlowRouter()
                    async with app.run_test(size=(100, 30)) as pilot:
                        started = time.perf_counter()
                        app._handle_prompt("/ingest")
                        await pilot.pause(0.1)
                        elapsed = time.perf_counter() - started
                        renderables = [node.content for node in app.query("#chat .message-body")]
                        return elapsed, renderables

        elapsed, renderables = asyncio.run(submit_command())
        joined = "\n".join(str(item) for item in renderables)

        self.assertLess(elapsed, 0.3)
        self.assertIn("/ingest", joined)
        self.assertIn("正在处理", joined)

    def test_tui_starts_on_centered_llm_setup_when_config_is_missing(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def inspect_setup():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        return (
                            app.query_one("#llm-setup").display,
                            app.query_one("#home").display,
                            app.query_one("#setup-api-key").has_focus,
                        )

        setup_display, home_display, api_key_focus = asyncio.run(inspect_setup())

        self.assertTrue(setup_display)
        self.assertFalse(home_display)
        self.assertTrue(api_key_focus)

    def test_tui_starts_on_llm_setup_when_env_base_url_is_invalid(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def inspect_setup():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "missing.json"
                with patch.dict(
                    "os.environ",
                    {
                        "CRAM_LLM_CONFIG_PATH": str(config_path),
                        "CRAM_LLM_API_KEY": "secret",
                        "CRAM_LLM_BASE_URL": "api.example.com/v1",
                        "CRAM_LLM_MODEL": "test-model",
                    },
                    clear=True,
                ):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        return app.query_one("#llm-setup").display, app.query_one("#home").display

        setup_display, home_display = asyncio.run(inspect_setup())

        self.assertTrue(setup_display)
        self.assertFalse(home_display)

    def test_tui_shows_setup_when_only_env_config_is_present(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def inspect_setup():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "missing.json"
                with patch.dict(
                    "os.environ",
                    {
                        "CRAM_LLM_CONFIG_PATH": str(config_path),
                        "CRAM_LLM_API_KEY": "secret",
                        "CRAM_LLM_BASE_URL": "https://api.example.com/v1",
                        "CRAM_LLM_MODEL": "gpt-4o-mini",
                    },
                    clear=True,
                ):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        return (
                            app.query_one("#llm-setup").display,
                            app.query_one("#home").display,
                            app.query_one("#setup-base-url", Input).value,
                        )

        setup_display, home_display, base_url = asyncio.run(inspect_setup())

        self.assertTrue(setup_display)
        self.assertFalse(home_display)
        # env vars must not leak into the form: cram's setup reads only its own llm.json
        self.assertEqual(base_url, "https://api.openai.com/v1")

    def test_tui_saves_llm_setup_and_enters_home(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def save_setup():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        app.query_one("#setup-api-key", Input).value = "secret"
                        app.query_one("#setup-base-url", Input).value = "https://api.example.com/v1"
                        app.query_one("#setup-model", Input).value = "test-model"
                        app._save_llm_setup()
                        await pilot.pause()
                        payload = json.loads(config_path.read_text(encoding="utf-8"))
                        return (
                            app.query_one("#llm-setup").display,
                            app.query_one("#home").display,
                            app.query_one("#home-prompt").has_focus,
                            payload,
                        )

        setup_display, home_display, home_focus, payload = asyncio.run(save_setup())

        self.assertFalse(setup_display)
        self.assertTrue(home_display)
        self.assertTrue(home_focus)
        self.assertEqual(payload["api_key"], "secret")
        self.assertEqual(payload["model"], "test-model")

    def test_config_command_reopens_llm_setup(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def open_config():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps(
                        {
                            "api_key": "secret",
                            "base_url": "https://api.example.com/v1",
                            "model": "test-model",
                        }
                    ),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.press("/", "c", "o", "n", "f", "i", "g", "enter")
                        await pilot.pause()
                        return (
                            app.query_one("#llm-setup").display,
                            app.query_one("#session").display,
                            app.query_one("#setup-base-url", Input).value,
                        )

        setup_display, session_display, base_url = asyncio.run(open_config())

        self.assertTrue(setup_display)
        self.assertFalse(session_display)
        self.assertEqual(base_url, "https://api.example.com/v1")

    def test_home_prompt_is_centered_not_docked_to_terminal_bottom(self):
        module = importlib.import_module("app.backend.cram_app.tui")
        source = (ROOT / "app" / "backend" / "cram_app" / "tui.py").read_text(encoding="utf-8")
        css = module.CramTuiApp.CSS

        self.assertIn('id="home-prompt"', source)
        self.assertIn('id="session-prompt"', source)
        self.assertIn("#home-prompt", css)
        self.assertIn("#session-prompt", css)
        self.assertNotIn("dock: bottom", css.split("#home-prompt", 1)[1].split("#session-prompt", 1)[0])

    def test_prompt_chrome_uses_left_accent_without_rectangular_frame(self):
        module = importlib.import_module("app.backend.cram_app.tui")
        css = module.CramTuiApp.CSS

        home_prompt_css = css.split("#home-prompt", 1)[1].split("#home-prompt:focus", 1)[0]
        home_focus_css = css.split("#home-prompt:focus", 1)[1].split("#session", 1)[0]
        session_prompt_css = css.split("#session-prompt", 1)[1].split("#session-prompt:focus", 1)[0]
        session_focus_css = css.split("#session-prompt:focus", 1)[1].split("#hints", 1)[0]

        for block in [home_prompt_css, home_focus_css, session_prompt_css, session_focus_css]:
            with self.subTest(block=block):
                self.assertIn("border-left", block)
                self.assertNotIn("border-top", block)

    def test_session_prompt_and_hints_do_not_overlap(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def inspect_layout(size):
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps(
                        {
                            "api_key": "secret",
                            "base_url": "https://api.example.com/v1",
                            "model": "test-model",
                        }
                    ),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(tmp)
                    async with app.run_test(size=size) as pilot:
                        await pilot.press("/", "s", "t", "a", "t", "u", "s", "enter")
                        await pilot.pause()
                        prompt = app.query_one("#session-prompt")
                        hints = app.query_one("#hints")
                        return prompt.region, hints.region

        for size in [(80, 24), (100, 30), (120, 40)]:
            with self.subTest(size=size):
                prompt_region, hints_region = asyncio.run(inspect_layout(size))

                self.assertLessEqual(prompt_region.y + prompt_region.height, hints_region.y)

    def test_ctrl_c_copies_chat_selection_instead_of_quitting(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        # ctrl+c must not be bound to quit (that would shadow the copy chain).
        self.assertNotIn(("ctrl+c", "quit", "quit"), module.CramTuiApp.BINDINGS)

        from textual.selection import SELECT_ALL

        async def copy_selection():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps(
                        {
                            "api_key": "secret",
                            "base_url": "https://api.example.com/v1",
                            "model": "test-model",
                        }
                    ),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        app._enter_session()
                        body = app._append_message("cram", "采样定理答案要点", color="#fab283")
                        await pilot.pause()
                        # prompt input keeps focus after a turn; selection lives on the screen
                        app.query_one("#session-prompt").focus()
                        app.screen.selections = {body: SELECT_ALL}
                        await pilot.pause()
                        await pilot.press("ctrl+c")
                        await pilot.pause()
                        return app.is_running, app._clipboard

        is_running, clipboard = asyncio.run(copy_selection())

        self.assertTrue(is_running)  # ctrl+c copied, it did not quit
        self.assertIn("采样定理答案要点", clipboard)

    def test_typing_slash_shows_filtered_command_menu(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        app._enter_session()
                        await pilot.pause()
                        app.query_one("#session-prompt").focus()
                        await pilot.press("/", "p")
                        await pilot.pause()
                        menu = app.query_one("#command-menu")
                        return (not menu.has_class("hidden"), list(app._menu_commands))

        visible, commands = asyncio.run(run())
        self.assertTrue(visible)
        self.assertEqual(commands, ["/plan"])

    def test_typing_slash_filters_commands_by_description_and_works_on_home_prompt(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        await pilot.press("/", "生", "成")
                        await pilot.pause()
                        menu = app.query_one("#command-menu")
                        return (not menu.has_class("hidden"), list(app._menu_commands))

        visible, commands = asyncio.run(run())
        self.assertTrue(visible)
        self.assertIn("/plan", commands)
        self.assertIn("/summary", commands)
        self.assertNotIn("/status", commands)

    def test_command_menu_shows_more_than_six_rows(self):
        module = importlib.import_module("app.backend.cram_app.tui")
        css = module.CramTuiApp.CSS

        command_menu_css = css.split("#command-menu", 1)[1].split("#home", 1)[0]

        self.assertIn("max-height: 11", command_menu_css)

    def test_enter_on_home_command_menu_runs_highlighted_command(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        class RecordingRouter:
            def __init__(self):
                self.seen = []

            def handle(self, text):
                self.seen.append(text)
                return CommandResult(kind="status", message="status ok")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    router = RecordingRouter()
                    app.router = router
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.press("/", "s", "t", "a", "enter")
                        await pilot.pause(0.1)
                        return router.seen

        seen = asyncio.run(run())

        self.assertEqual(seen, ["/status"])

    def test_home_prompt_does_not_shift_when_command_menu_opens(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        before = app.query_one("#home-prompt").region
                        await pilot.press("/")
                        await pilot.pause()
                        after = app.query_one("#home-prompt").region
                        return before, after

        before, after = asyncio.run(run())

        self.assertEqual(before.y, after.y)
        self.assertEqual(before.height, after.height)

    def test_chat_scrolls_to_bottom_after_long_message_update(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(80, 12)) as pilot:
                        await pilot.pause()
                        app._enter_session()
                        body = app._append_message("cram", "short", color="#fab283")
                        await pilot.pause()
                        chat = app.query_one("#chat", VerticalScroll)
                        chat.scroll_home(animate=False, immediate=True)
                        await pilot.pause()
                        app._update_message(body.id or "", "\n".join(f"line {index}" for index in range(80)))
                        await pilot.pause()
                        return chat.scroll_y, chat.max_scroll_y

        scroll_y, max_scroll_y = asyncio.run(run())

        self.assertEqual(scroll_y, max_scroll_y)

    def test_streamed_reasoning_collapses_after_answer_and_uses_whole_seconds(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        class StreamingRouter:
            def run_turn(self, text):
                yield StreamEvent("reasoning", "先定位教材定义")
                yield StreamEvent("reasoning", "，再合并公式")
                yield StreamEvent("content", "这是答案")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    app.router = StreamingRouter()
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.press("h", "i", "enter")
                        await pilot.pause(0.2)
                        reason = app.query_one(".message-reason")
                        think = app.query_one(".message-think")
                        answer = app.query_one("#chat .message:last-child .message-body")
                        reason_hidden = reason.has_class("hidden")
                        think_text = str(think.content)
                        return (
                            reason_hidden,
                            str(reason.content),
                            think_text,
                            str(answer.content),
                        )

        reason_hidden, reason_text, think_text, answer_text = asyncio.run(run())

        self.assertTrue(reason_hidden)
        self.assertIn("先定位教材定义，再合并公式", reason_text)
        self.assertIn("思考", think_text)
        self.assertIn("s", think_text)
        self.assertNotIn(".0s", think_text)
        self.assertIn("这是答案", answer_text)

    def test_written_paths_are_tracked_and_openable(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "course")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        app._enter_session()
                        app._write_wrote([app.workspace.output_dir / "速成计划.md"])
                        await pilot.pause()
                        return [p.name for p in app._wrote_paths], hasattr(app, "action_open_artifact")

        names, has_action = asyncio.run(run())
        self.assertEqual(names, ["速成计划.md"])
        self.assertTrue(has_action)

    def test_switch_workspace_repoints_app(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                other = Path(tmp) / "数字电路"
                other.mkdir()
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "通信原理")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        app._switch_workspace(str(other))
                        await pilot.pause()
                        return app.workspace.root.name, str(app.query_one("#status").content)

        name, status = asyncio.run(run())
        self.assertEqual(name, "数字电路")
        self.assertIn("数字电路", status)

    def test_send_button_toggles_between_send_and_stop(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "通信原理")
                    async with app.run_test(size=(100, 30)) as pilot:
                        await pilot.pause()
                        from textual.widgets import Button

                        button = app.query_one("#send-btn", Button)
                        idle = str(button.label)
                        app._set_send_button(busy=True)
                        await pilot.pause()
                        busy = str(button.label)
                        return idle, busy, app._generating

        idle, busy, generating = asyncio.run(run())
        self.assertIn("↑", idle)
        self.assertIn("●", busy)
        self.assertTrue(generating)

    def test_prompt_is_softwrap_textarea_that_grows(self):
        module = importlib.import_module("app.backend.cram_app.tui")

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "llm.json"
                config_path.write_text(
                    json.dumps({"api_key": "k", "base_url": "https://api.example.com/v1", "model": "m"}),
                    encoding="utf-8",
                )
                with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                    app = module.CramTuiApp(Path(tmp) / "通信原理")
                    async with app.run_test(size=(60, 30)) as pilot:
                        await pilot.pause()
                        app._enter_session()
                        await pilot.pause()
                        area = app.query_one("#session-prompt", module.PromptArea)
                        soft = area.soft_wrap
                        area.text = "第一行\n第二行\n第三行\n第四行"
                        app._autosize_prompt(area)
                        await pilot.pause()
                        return soft, float(area.styles.height.value)

        soft, height = asyncio.run(run())
        self.assertTrue(soft)  # multi-line, wrapping input
        self.assertGreater(height, 3)  # grew past the single-line minimum


if __name__ == "__main__":
    unittest.main()
