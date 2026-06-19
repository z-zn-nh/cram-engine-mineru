import importlib
import asyncio
import tempfile
import unittest
from pathlib import Path


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
                app = module.CramTuiApp(tmp)
                async with app.run_test(size=size) as pilot:
                    await pilot.press("h", "i", "enter")
                    await pilot.pause()
                    prompt = app.query_one("#session-prompt")
                    hints = app.query_one("#hints")
                    return prompt.region, hints.region

        for size in [(80, 24), (100, 30), (120, 40)]:
            with self.subTest(size=size):
                prompt_region, hints_region = asyncio.run(inspect_layout(size))

                self.assertLessEqual(prompt_region.y + prompt_region.height, hints_region.y)


if __name__ == "__main__":
    unittest.main()
