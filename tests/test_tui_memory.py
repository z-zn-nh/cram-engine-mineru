import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.memory import MemoryStore
from app.backend.cram_app.workspace import CramWorkspace


class TuiMemoryTests(unittest.TestCase):
    def test_append_memory_note_dedups_and_categorizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "通信原理")
            store = MemoryStore.open(workspace)

            self.assertTrue(store.append_memory_note("第3章必考", category="考点"))
            self.assertTrue(store.append_memory_note("用户常混淆采样与量化", category="易错"))
            self.assertFalse(store.append_memory_note("第3章必考", category="考点"))  # dedup

            memory = MemoryStore.open(workspace).load_boot_summary()
            self.assertIn("- [考点] 第3章必考", memory)
            self.assertIn("- [易错] 用户常混淆采样与量化", memory)
            self.assertEqual(memory.count("第3章必考"), 1)

    def test_memory_store_persists_boot_summary_and_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "数字电路")
            store = MemoryStore.open(workspace)

            store.save_boot_summary("上次复习到触发器。")
            store.append_session_event("user", "继续讲时序逻辑")

            reopened = MemoryStore.open(workspace)

            self.assertIn("触发器", reopened.load_boot_summary())
            self.assertEqual(reopened.load_recent_session_events(limit=1)[0]["content"], "继续讲时序逻辑")

    def test_outputs_are_indexed_as_lower_priority_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "机器学习")
            (workspace.root / "老师重点.pdf").write_text("支持向量机", encoding="utf-8")
            output = workspace.output_dir / "知识点整合.md"
            output.write_text("SVM 是支持向量机。", encoding="utf-8")

            references = MemoryStore.open(workspace).build_reference_catalog()

            labels = [reference.label for reference in references]
            priorities = {reference.label: reference.priority for reference in references}
            self.assertIn("[原始资料] 老师重点.pdf", labels)
            self.assertIn("[生成产物] cram-output/知识点整合.md", labels)
            self.assertLess(
                priorities["[原始资料] 老师重点.pdf"],
                priorities["[生成产物] cram-output/知识点整合.md"],
            )

    def test_conflict_records_are_saved_for_lint_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "通信原理")
            store = MemoryStore.open(workspace)

            store.record_conflict(
                "抽样频率条件不一致",
                left="[生成产物] cram-output/速成计划.md",
                right="[原始资料] 复习重点.pdf p.8",
            )

            conflicts = store.load_conflicts()
            self.assertEqual(conflicts[0]["title"], "抽样频率条件不一致")
            self.assertIn("原始资料", conflicts[0]["right"])


if __name__ == "__main__":
    unittest.main()
