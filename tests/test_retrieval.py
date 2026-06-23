import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.retrieval import retrieve
from app.backend.cram_app.workspace import CramWorkspace
from app.backend.cram_app.workspace_index import index_text_sources, load_workspace_chunks


class FakeEmbedder:
    """Stand-in for fastembed: maps exact text -> vector, so tests need no model download."""

    def __init__(self, table: dict[str, list[float]]):
        self.table = table
        self.embed_calls = 0

    def embed(self, texts):
        self.embed_calls += 1
        return [self.table[text] for text in texts]

    def query_embed(self, texts):
        return [self.table[text] for text in texts]


def _two_doc_workspace(tmp: str):
    workspace = CramWorkspace.open(Path(tmp) / "通信原理")
    (workspace.root / "a.md").write_text("甲文档讲的是奈奎斯特采样定理与混叠。", encoding="utf-8")
    (workspace.root / "b.md").write_text("乙文档讲的是傅里叶变换与卷积。", encoding="utf-8")
    index_text_sources(workspace)
    chunks = load_workspace_chunks(workspace)
    a = next(c for c in chunks if c.source_file == "a.md")
    b = next(c for c in chunks if c.source_file == "b.md")
    return workspace, a, b


class HybridRetrievalTests(unittest.TestCase):
    def test_embeddings_surface_a_chunk_bm25_alone_would_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, a, b = _two_doc_workspace(tmp)
            # "QUERY" shares no tokens with either doc, so BM25 returns nothing; only the
            # embedding tier (which scores "QUERY" close to doc A) can surface it.
            embedder = FakeEmbedder({a.text: [1.0, 0.0], b.text: [0.0, 1.0], "QUERY": [1.0, 0.0]})

            results = retrieve(workspace, "QUERY", limit=1, embedder=embedder)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].source_file, "a.md")

    def test_falls_back_to_bm25_when_no_embedder(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, _a, _b = _two_doc_workspace(tmp)

            results = retrieve(workspace, "采样定理", limit=1, embedder=None)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].source_file, "a.md")
            self.assertFalse((workspace.cram_dir / "index" / "embeddings.npy").exists())

    def test_embeddings_are_cached_between_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, a, b = _two_doc_workspace(tmp)
            embedder = FakeEmbedder({a.text: [1.0, 0.0], b.text: [0.0, 1.0], "QUERY": [1.0, 0.0]})

            retrieve(workspace, "QUERY", limit=1, embedder=embedder)
            retrieve(workspace, "QUERY", limit=1, embedder=embedder)

            self.assertEqual(embedder.embed_calls, 1)  # corpus embedded once, then cached
            self.assertTrue((workspace.cram_dir / "index" / "embeddings.npy").is_file())

    def test_reranker_reorders_candidates_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace, a, b = _two_doc_workspace(tmp)
            # both docs are retrieved (similar embeddings); fusion would order a before b,
            # but the cross-encoder scores b higher and must flip them.
            embedder = FakeEmbedder({a.text: [1.0, 0.0], b.text: [0.9, 0.1], "QUERY": [1.0, 0.0]})
            reranker = FakeReranker({a.text: 0.1, b.text: 0.9})

            results = retrieve(workspace, "QUERY", limit=2, embedder=embedder, reranker=reranker)

            self.assertEqual([r.source_file for r in results], ["b.md", "a.md"])


class FakeReranker:
    def __init__(self, scores: dict[str, float]):
        self.scores = scores

    def rerank(self, query, documents):
        return [self.scores.get(document, 0.0) for document in documents]


if __name__ == "__main__":
    unittest.main()
