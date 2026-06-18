import importlib
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


if __name__ == "__main__":
    unittest.main()
