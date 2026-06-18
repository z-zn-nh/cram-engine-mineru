import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.workspace import CramWorkspace, discover_workspace_sources


class TuiWorkspaceTests(unittest.TestCase):
    def test_open_uses_current_folder_as_course_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "通信原理"
            root.mkdir()

            workspace = CramWorkspace.open(root)

            self.assertEqual(workspace.root, root)
            self.assertEqual(workspace.course_name, "通信原理")
            self.assertEqual(workspace.cram_dir, root / ".cram")
            self.assertEqual(workspace.output_dir, root / "cram-output")
            self.assertTrue((root / ".cram" / "memory").is_dir())
            self.assertTrue((root / ".cram" / "sessions").is_dir())
            self.assertTrue((root / ".cram" / "index").is_dir())
            self.assertTrue((root / "cram-output").is_dir())

    def test_discover_sources_ignores_internal_and_output_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "第1章.pptx").write_text("ppt", encoding="utf-8")
            (root / "复习重点.pdf").write_text("pdf", encoding="utf-8")
            (root / "公式截图.png").write_text("png", encoding="utf-8")
            (root / "notes.md").write_text("notes", encoding="utf-8")
            (root / "cram-output").mkdir()
            (root / "cram-output" / "知识点整合.md").write_text("generated", encoding="utf-8")
            (root / ".cram").mkdir()
            (root / ".cram" / "memory.md").write_text("memory", encoding="utf-8")

            sources = discover_workspace_sources(root)
            names = [source.relative_path.as_posix() for source in sources]

            self.assertEqual(
                names,
                ["notes.md", "公式截图.png", "复习重点.pdf", "第1章.pptx"],
            )
            self.assertTrue(all(source.kind in {"document", "image", "notes"} for source in sources))


if __name__ == "__main__":
    unittest.main()
