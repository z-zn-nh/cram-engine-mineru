import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConvertPptToPdfScriptTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / "scripts" / "convert-ppt-to-pdf.ps1"
        self.content = self.script.read_text(encoding="utf-8")

    def test_script_exists(self):
        self.assertTrue(self.script.is_file())

    def test_honors_libreoffice_env_override_with_soffice_default(self):
        # Must match the ingest fallback contract in workspace_ingest.py.
        self.assertIn("CRAM_LIBREOFFICE_BIN", self.content)
        self.assertIn("soffice", self.content)

    def test_runs_headless_pdf_conversion(self):
        for token in ("--headless", "--convert-to", "pdf", "--outdir"):
            self.assertIn(token, self.content)

    def test_validates_ppt_extension(self):
        self.assertIn(".pptx", self.content)
        self.assertIn(".ppt", self.content)

    def test_verifies_and_reports_output_pdf(self):
        self.assertIn("Test-Path", self.content)
        self.assertIn("Write-Output", self.content)


if __name__ == "__main__":
    unittest.main()
