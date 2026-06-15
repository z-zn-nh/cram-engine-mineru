import json
import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.artifacts import save_artifact
from app.backend.cram_app.subjects import create_subject


class ArtifactTests(unittest.TestCase):
    def test_save_mindmap_artifact_under_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))

            artifact = save_artifact(
                subject,
                artifact_type="mindmap",
                title="通信原理总图",
                content='{"root":"通信原理"}',
                citations=["教材.pdf:p45"],
                fmt="json",
            )

            self.assertTrue(artifact.path.exists())
            self.assertEqual(artifact.relative_path.as_posix(), "artifacts/思维导图/通信原理总图.json")
            self.assertEqual(artifact.path.read_text(encoding="utf-8"), '{"root":"通信原理"}')

            citation_payload = json.loads(artifact.citations_path.read_text(encoding="utf-8"))
            self.assertEqual(citation_payload["citations"], ["教材.pdf:p45"])

    def test_save_artifact_sanitizes_title_path_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))

            artifact = save_artifact(
                subject,
                artifact_type="notes",
                title="../第一章/信号",
                content="笔记",
                citations=[],
                fmt="md",
            )

            self.assertEqual(artifact.relative_path.as_posix(), "artifacts/笔记/第一章-信号.md")

    def test_save_artifact_rejects_unknown_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))

            with self.assertRaises(ValueError):
                save_artifact(subject, artifact_type="random", title="x", content="x", citations=[], fmt="md")


if __name__ == "__main__":
    unittest.main()
