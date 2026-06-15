import json
import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.artifacts import save_artifact
from app.backend.cram_app.subjects import create_subject


class ArtifactTests(unittest.TestCase):
    def test_save_mindmap_artifact_under_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("signals", Path(tmp))
            content = '{"title":"signals","nodes":[{"label":"modulation","children":[]}]}'

            artifact = save_artifact(
                subject,
                artifact_type="mindmap",
                title="signals-map",
                content=content,
                citations=["slides:p8"],
                fmt="json",
            )

            self.assertTrue(artifact.path.exists())
            self.assertIn("artifacts", artifact.relative_path.parts)
            self.assertEqual(artifact.path.read_text(encoding="utf-8"), content)

            citation_payload = json.loads(artifact.citations_path.read_text(encoding="utf-8"))
            self.assertEqual(citation_payload["citations"], ["slides:p8"])

    def test_save_artifact_sanitizes_title_path_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("signals", Path(tmp))

            artifact = save_artifact(
                subject,
                artifact_type="notes",
                title="../chapter one",
                content="notes",
                citations=[],
                fmt="md",
            )

            self.assertEqual(artifact.path.name, "chapter-one.md")
            self.assertIn("artifacts", artifact.relative_path.parts)

    def test_save_artifact_rejects_unknown_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("signals", Path(tmp))

            with self.assertRaises(ValueError):
                save_artifact(subject, artifact_type="random", title="x", content="x", citations=[], fmt="md")


if __name__ == "__main__":
    unittest.main()
