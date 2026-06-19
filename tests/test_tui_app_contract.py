import importlib
import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Input

from app.backend.cram_app.commands import CommandResult


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
                        app.query_one("#session-prompt", Input).focus()
                        app.screen.selections = {body: SELECT_ALL}
                        await pilot.pause()
                        await pilot.press("ctrl+c")
                        await pilot.pause()
                        return app.is_running, app._clipboard

        is_running, clipboard = asyncio.run(copy_selection())

        self.assertTrue(is_running)  # ctrl+c copied, it did not quit
        self.assertIn("采样定理答案要点", clipboard)


if __name__ == "__main__":
    unittest.main()
