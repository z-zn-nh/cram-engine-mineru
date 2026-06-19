import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.cram_app.commands import CommandRouter
from app.backend.cram_app.workspace import CramWorkspace
from app.backend.cram_app.workspace_ingest import MaterialIngestResult
from app.backend.cram_app.workspace_index import ParsedTextSource


class FakeLLM:
    def __init__(self, answer: str = "LLM 已回答"):
        self.answer = answer
        self.messages: list[dict] = []

    def chat(self, messages: list[dict], *, stream: bool = False) -> str:
        self.messages = messages
        return self.answer


class FakeStreamingLLM(FakeLLM):
    def stream_chat(self, messages: list[dict]):
        self.messages = messages
        yield "采样"
        yield "定理"


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
            self.assertIn("/model", result.message)
            self.assertIn("/lint", result.message)

    def test_model_command_routes_to_model_picker(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))

            result = CommandRouter(workspace).handle("/model")

            self.assertEqual(result.kind, "model")

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

    def test_ingest_indexes_text_sources_and_reports_pdf_as_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            (workspace.root / "notes.md").write_text("Nyquist sampling theorem.", encoding="utf-8")
            (workspace.root / "slides.pdf").write_text("pdf placeholder", encoding="utf-8")

            def fake_ingest(workspace, sources):
                return MaterialIngestResult(parsed_texts=[], processed_files=0, failed_files=[], pending_files=["slides.pdf"])

            result = CommandRouter(workspace, material_ingester=fake_ingest).handle("/ingest")

            self.assertEqual(result.kind, "ingest")
            self.assertTrue((workspace.cram_dir / "index" / "chunks.jsonl").is_file())
            self.assertIn("indexed 1 chunks", result.message)
            self.assertIn("MinerU pending 1 files", result.message)

    def test_ingest_indexes_mineru_markdown_from_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            (workspace.root / "slides.pdf").write_text("pdf placeholder", encoding="utf-8")
            parsed = workspace.cram_dir / "parsed" / "slides" / "auto.md"
            parsed.parent.mkdir(parents=True, exist_ok=True)
            parsed.write_text("Nyquist sampling theorem prevents aliasing.", encoding="utf-8")

            def fake_ingest(workspace, sources):
                return MaterialIngestResult(
                    parsed_texts=[
                        ParsedTextSource(path=parsed, source_file="slides.pdf", locator_prefix="mineru")
                    ],
                    processed_files=1,
                    failed_files=[],
                    pending_files=[],
                )

            result = CommandRouter(workspace, material_ingester=fake_ingest).handle("/ingest")

            self.assertIn("MinerU parsed 1 files", result.message)
            self.assertIn("indexed 1 chunks", result.message)
            self.assertIn("slides.pdf:mineru:1", (workspace.cram_dir / "index" / "chunks.jsonl").read_text(encoding="utf-8"))

    def test_free_text_question_includes_indexed_references_in_llm_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            (workspace.root / "notes.md").write_text(
                "Nyquist sampling theorem prevents aliasing.",
                encoding="utf-8",
            )
            CommandRouter(workspace).handle("/ingest")
            llm = FakeLLM("use cited answer")

            CommandRouter(workspace, llm=llm).handle("What prevents aliasing?")

            system_content = llm.messages[0]["content"]
            self.assertIn("notes.md:text:1", system_content)
            self.assertIn("Nyquist sampling theorem", system_content)

    def test_free_text_can_stream_llm_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            llm = FakeStreamingLLM()
            router = CommandRouter(workspace, llm=llm)

            chunks = list(router.stream("帮我讲一下采样定理"))

            self.assertEqual(chunks, ["采样", "定理"])
            events = router.memory.load_recent_session_events()
            self.assertEqual(events[-1]["role"], "agent")
            self.assertEqual(events[-1]["content"], "采样定理")

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
