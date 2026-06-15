import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.subjects import create_subject, subject_slug


class SubjectStorageTests(unittest.TestCase):
    def test_subject_slug_keeps_chinese_and_removes_path_chars(self):
        self.assertEqual(subject_slug("通信原理/期末"), "通信原理-期末")

    def test_subject_slug_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            subject_slug("  ")

    def test_create_subject_creates_required_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", root=Path(tmp))

            self.assertEqual(subject.name, "通信原理")
            self.assertEqual(subject.slug, "通信原理")
            for name in ["sources", "parsed", "chunks", "index", "chats", "artifacts", "citations"]:
                self.assertTrue((subject.path / name).is_dir())
            self.assertTrue((subject.path / "subject.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
