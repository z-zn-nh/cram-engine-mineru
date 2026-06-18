import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CramCommandInstallTests(unittest.TestCase):
    def test_install_script_exists_and_writes_cram_cmd(self):
        script = ROOT / "scripts" / "install-cram-command.ps1"

        self.assertTrue(script.is_file())
        content = script.read_text(encoding="utf-8")
        self.assertIn("cram.cmd", content)
        self.assertIn("app\\backend\\cram.py", content)
        self.assertIn("PATH", content)

    def test_command_shim_template_points_to_backend_entrypoint(self):
        template = ROOT / "scripts" / "cram.cmd.template"

        self.assertTrue(template.is_file())
        content = template.read_text(encoding="utf-8")
        self.assertIn("@PYTHON@", content)
        self.assertIn("@CRAM_PY@", content)
        self.assertIn('"%CRAM_PY%"', content)
        self.assertNotIn('"@PYTHON@"', content)

    def test_entrypoint_supports_non_interactive_status_smoke(self):
        entrypoint = (ROOT / "app" / "backend" / "cram.py").read_text(encoding="utf-8")

        self.assertIn("--status", entrypoint)
        self.assertIn('handle("/status")', entrypoint)

    def test_readme_documents_cram_command_install(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("install-cram-command.ps1", readme)
        self.assertIn("重开终端", readme)
        self.assertIn("cd D:\\期末资料\\通信原理", readme)
        self.assertIn("\ncram\n", readme)
        self.assertIn("cram --status", readme)


if __name__ == "__main__":
    unittest.main()
