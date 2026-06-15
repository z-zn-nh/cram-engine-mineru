import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.chunks import ChunkRecord, append_chunks, load_chunks, search_chunks
from app.backend.cram_app.citations import write_citations
from app.backend.cram_app.subjects import create_subject


class ChunkIndexTests(unittest.TestCase):
    def test_append_and_load_chunks_with_citation_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))
            chunk = ChunkRecord(
                chunk_id="教材-p45-001",
                source_file="教材.pdf",
                locator="p45",
                text="调制是把基带信号搬移到载波上的过程。",
            )

            append_chunks(subject, [chunk])
            loaded = load_chunks(subject)

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].citation_label, "教材.pdf:p45")

    def test_search_chunks_scores_keyword_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))
            append_chunks(
                subject,
                [
                    ChunkRecord("a", "教材.pdf", "p1", "调制 解调 载波"),
                    ChunkRecord("b", "教材.pdf", "p2", "随机过程 噪声"),
                ],
            )

            results = search_chunks(subject, "调制 解调")

            self.assertEqual(results[0].chunk_id, "a")
            self.assertEqual(len(results), 1)

    def test_write_citations_records_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))
            path = write_citations(
                subject,
                [
                    ChunkRecord("a", "教材.pdf", "p45", "调制定义"),
                    ChunkRecord("b", "第3讲.pptx", "s8", "调制分类"),
                ],
            )

            content = path.read_text(encoding="utf-8")
            self.assertIn("教材.pdf:p45", content)
            self.assertIn("第3讲.pptx:s8", content)


if __name__ == "__main__":
    unittest.main()
