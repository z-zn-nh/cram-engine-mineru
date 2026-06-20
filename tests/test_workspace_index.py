import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.workspace import CramWorkspace
from app.backend.cram_app.workspace_index import (
    ParsedTextSource,
    index_text_sources,
    load_workspace_chunks,
    search_workspace_chunks,
)


class WorkspaceIndexTests(unittest.TestCase):
    def test_indexes_markdown_and_text_sources_into_workspace_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "signals")
            (workspace.root / "chapter1.md").write_text(
                "# Sampling\nNyquist theorem prevents aliasing.",
                encoding="utf-8",
            )
            (workspace.root / "formula.txt").write_text(
                "Fourier transform turns convolution into multiplication.",
                encoding="utf-8",
            )

            result = index_text_sources(workspace)
            chunks = load_workspace_chunks(workspace)

            self.assertEqual(result.indexed_files, 2)
            self.assertEqual(result.indexed_chunks, 2)
            self.assertEqual(result.skipped_files, 0)
            self.assertTrue((workspace.cram_dir / "index" / "chunks.jsonl").is_file())
            self.assertEqual([chunk.source_file for chunk in chunks], ["chapter1.md", "formula.txt"])
            self.assertEqual(chunks[0].citation_label, "chapter1.md:text:1")

    def test_search_workspace_chunks_returns_relevant_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "signals")
            (workspace.root / "notes.md").write_text(
                "Sampling theorem says the sampling rate must exceed twice the highest frequency.",
                encoding="utf-8",
            )
            index_text_sources(workspace)

            matches = search_workspace_chunks(workspace, "sampling rate", limit=1)

            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].source_file, "notes.md")
            self.assertIn("twice", matches[0].text)

    def test_indexes_mineru_markdown_as_original_pdf_citation(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "signals")
            parsed = workspace.cram_dir / "parsed" / "slides" / "auto.md"
            parsed.parent.mkdir(parents=True, exist_ok=True)
            parsed.write_text("Formula OCR captured E = mc^2.", encoding="utf-8")

            result = index_text_sources(
                workspace,
                extra_texts=[
                    ParsedTextSource(
                        path=parsed,
                        source_file="slides.pdf",
                        locator_prefix="mineru",
                    )
                ],
            )
            chunks = load_workspace_chunks(workspace)

            self.assertEqual(result.indexed_chunks, 1)
            self.assertEqual(chunks[0].citation_label, "slides.pdf:mineru:1")
            self.assertIn("Formula OCR", chunks[0].text)


    def test_bm25_prefers_focused_chunk_over_long_tangential_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "通信原理")
            (workspace.root / "a.md").write_text(
                "采样定理：采样率必须大于信号最高频率的两倍。", encoding="utf-8"
            )
            (workspace.root / "b.md").write_text(
                "本章导论介绍了很多主题，包括傅里叶变换、卷积、滤波器、调制解调，内容很长很长很长很长。",
                encoding="utf-8",
            )
            index_text_sources(workspace)

            matches = search_workspace_chunks(workspace, "采样率", limit=2)

            self.assertTrue(matches)
            self.assertEqual(matches[0].source_file, "a.md")  # IDF + length-norm favors the focused chunk


if __name__ == "__main__":
    unittest.main()
