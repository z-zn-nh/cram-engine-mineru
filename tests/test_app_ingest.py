import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from app.backend.cram_app.ingest import ingest_subject_materials
from app.backend.cram_app.subjects import create_subject


class AppIngestTests(unittest.TestCase):
    def test_ingest_copies_sources_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = create_subject("通信原理", root)
            source = root / "lesson1.pdf"
            source.write_text("fake pdf", encoding="utf-8")

            with redirect_stdout(StringIO()):
                result = ingest_subject_materials(subject, [source], dry_run=True)

            copied = subject.path / "sources" / "lesson1.pdf"
            self.assertTrue(copied.exists())
            self.assertEqual(copied.read_text(encoding="utf-8"), "fake pdf")

            manifest_path = subject.path / "parsed" / "ingest-manifest.json"
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["subject"], "通信原理")
            self.assertEqual(manifest["materials"][0]["source"], str(copied))
            self.assertEqual(result.summary_path, subject.path / "parsed" / "通信原理" / "materials-summary.md")


if __name__ == "__main__":
    unittest.main()
