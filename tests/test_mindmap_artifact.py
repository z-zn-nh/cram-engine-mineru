import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.artifacts import save_artifact, validate_mindmap_payload
from app.backend.cram_app.subjects import create_subject


class MindMapArtifactTests(unittest.TestCase):
    def test_valid_mindmap_schema_can_be_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("signals", Path(tmp))

            artifact = save_artifact(
                subject,
                artifact_type="mindmap",
                title="signals-map",
                content='{"title":"Signals","nodes":[{"id":"sampling","label":"Sampling","children":[]}]}',
                citations=["slides:p8"],
                fmt="json",
            )

            self.assertTrue(artifact.path.exists())

    def test_mindmap_requires_title(self):
        with self.assertRaises(ValueError):
            validate_mindmap_payload({"nodes": [{"label": "Sampling"}]})

    def test_mindmap_requires_node_labels(self):
        with self.assertRaises(ValueError):
            validate_mindmap_payload({"title": "Signals", "nodes": [{"id": "sampling"}]})


if __name__ == "__main__":
    unittest.main()
