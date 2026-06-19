import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.cram_app.commands import CommandRouter
from app.backend.cram_app.workspace import CramWorkspace


class FakeLLM:
    def __init__(self, answer: str = "LLM 已回答"):
        self.answer = answer
        self.messages: list[dict] = []

    def chat(self, messages: list[dict], *, stream: bool = False) -> str:
        self.messages = messages
        return self.answer


class TuiCommandTests(unittest.TestCase):
    def test_status_reports_current_folder_sources_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "通信原理")
            (workspace.root / "复习重点.pdf").write_text("pdf", encoding="utf-8")
            (workspace.output_dir / "速成计划.md").write_text("plan", encoding="utf-8")

            result = CommandRouter(workspace).handle("/status")

            self.assertEqual(result.kind, "status")
            self.assertIn("通信原理", result.message)
            self.assertIn("1 个资料文件", result.message)
            self.assertIn("1 个输出产物", result.message)

    def test_help_lists_supported_slash_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))

            result = CommandRouter(workspace).handle("/help")

            self.assertEqual(result.kind, "help")
            self.assertIn("/ingest", result.message)
            self.assertIn("/config", result.message)
            self.assertIn("/lint", result.message)

    def test_generation_command_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "数字电路")

            result = CommandRouter(workspace).handle("/plan")

            self.assertEqual(result.kind, "artifact")
            self.assertEqual(result.wrote, [workspace.output_dir / "速成计划.md"])
            self.assertTrue((workspace.output_dir / "速成计划.md").is_file())
            self.assertIn("Wrote", result.message)

    def test_lint_reports_existing_conflicts_and_reference_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "机器学习")
            router = CommandRouter(workspace)
            router.memory.record_conflict("定义冲突", left="[生成产物] A", right="[原始资料] B")

            result = router.handle("/lint")

            self.assertEqual(result.kind, "lint")
            self.assertIn("定义冲突", result.message)

    def test_free_text_is_routed_as_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            llm = FakeLLM("采样定理是把连续信号离散化的基础。")

            result = CommandRouter(workspace, llm=llm).handle("帮我讲一下采样定理")

            self.assertEqual(result.kind, "ask")
            self.assertEqual(result.message, "采样定理是把连续信号离散化的基础。")
            self.assertIn("期末速成", llm.messages[0]["content"])
            self.assertEqual(llm.messages[-1]["content"], "帮我讲一下采样定理")

    def test_free_text_reports_missing_llm_api_key_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            config_path = Path(tmp) / "missing-llm.json"

            with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                result = CommandRouter(workspace).handle("帮我讲一下采样定理")

            self.assertEqual(result.kind, "ask")
            self.assertIn("CRAM_LLM_API_KEY", result.message)
            self.assertIn("setx", result.message)


if __name__ == "__main__":
    unittest.main()
