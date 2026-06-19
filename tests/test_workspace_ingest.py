import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.cram_app.workspace import CramWorkspace, discover_workspace_sources
from app.backend.cram_app.workspace_ingest import ingest_material_sources


class WorkspaceIngestTests(unittest.TestCase):
    def test_runs_mineru_for_pdf_and_collects_markdown_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "signals")
            pdf = workspace.root / "slides.pdf"
            pdf.write_text("pdf placeholder", encoding="utf-8")
            sources = discover_workspace_sources(workspace.root)
            commands: list[list[str]] = []

            def fake_run(command, **kwargs):
                commands.append(command)
                output_dir = Path(command[command.index("-o") + 1])
                output_dir.mkdir(parents=True, exist_ok=True)
                (output_dir / "slides.md").write_text("Parsed by MinerU.", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0)

            with patch("app.backend.cram_app.workspace_ingest.shutil.which", return_value="mineru"):
                with patch("app.backend.cram_app.workspace_ingest.subprocess.run", side_effect=fake_run):
                    result = ingest_material_sources(workspace, sources, mineru_bin="mineru")

            self.assertEqual(result.processed_files, 1)
            self.assertEqual(result.pending_files, [])
            self.assertEqual(result.failed_files, [])
            self.assertEqual(result.parsed_texts[0].source_file, "slides.pdf")
            self.assertEqual(result.parsed_texts[0].locator_prefix, "mineru")
            self.assertEqual(commands[0][0], "mineru")
            self.assertIn(str(pdf), commands[0])

    def test_marks_ppt_as_pending_for_conversion_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "signals")
            (workspace.root / "deck.pptx").write_text("ppt placeholder", encoding="utf-8")

            result = ingest_material_sources(workspace, discover_workspace_sources(workspace.root))

            self.assertEqual(result.processed_files, 0)
            self.assertEqual(result.pending_files, ["deck.pptx"])

    def test_reuses_cached_mineru_markdown_when_source_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "signals")
            pdf = workspace.root / "slides.pdf"
            pdf.write_text("pdf placeholder", encoding="utf-8")
            cached = workspace.cram_dir / "parsed" / "slides" / "slides.md"
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text("Cached MinerU markdown.", encoding="utf-8")

            with patch("app.backend.cram_app.workspace_ingest.shutil.which", return_value="mineru"):
                with patch("app.backend.cram_app.workspace_ingest.subprocess.run") as run:
                    result = ingest_material_sources(workspace, discover_workspace_sources(workspace.root))

            run.assert_not_called()
            self.assertEqual(result.processed_files, 1)
            self.assertEqual(result.parsed_texts[0].path, cached)


if __name__ == "__main__":
    unittest.main()
