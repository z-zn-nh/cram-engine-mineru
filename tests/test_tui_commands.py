import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.backend.cram_app.commands import CommandRouter
from app.backend.cram_app.llm import StreamEvent
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


class FakeReasoningLLM(FakeLLM):
    def stream_chat(self, messages: list[dict]):
        self.messages = messages
        yield StreamEvent("reasoning", "先回忆采样定理…")
        yield StreamEvent("content", "采样")
        yield StreamEvent("content", "定理")


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

    def test_generation_command_writes_llm_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "数字电路")
            llm = FakeLLM("# 速成计划\n1. 先掌握布尔代数化简")

            result = CommandRouter(workspace, llm=llm).handle("/plan")

            self.assertEqual(result.kind, "artifact")
            self.assertEqual(result.wrote, [workspace.output_dir / "速成计划.md"])
            written = (workspace.output_dir / "速成计划.md").read_text(encoding="utf-8")
            self.assertIn("先掌握布尔代数化简", written)  # real LLM content, not a placeholder
            self.assertNotIn("后续会接入 LLM", written)
            self.assertIn("期末速成计划", llm.messages[0]["content"])

    def test_generation_command_passes_indexed_evidence_to_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            (workspace.root / "notes.md").write_text(
                "Nyquist sampling theorem prevents aliasing.",
                encoding="utf-8",
            )
            CommandRouter(workspace).handle("/ingest")
            llm = FakeLLM("# 题库\nQ1. ...")

            CommandRouter(workspace, llm=llm).handle("/quiz")

            system_content = llm.messages[0]["content"]
            self.assertIn("notes.md:text:1", system_content)
            self.assertIn("Nyquist sampling theorem", system_content)
            self.assertNotIn("当前阶段还没有接入资料检索", system_content)

    def test_generation_command_without_llm_config_does_not_write_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "通信原理")
            config_path = Path(tmp) / "missing-llm.json"

            with patch.dict("os.environ", {"CRAM_LLM_CONFIG_PATH": str(config_path)}, clear=True):
                result = CommandRouter(workspace).handle("/plan")

            self.assertEqual(result.kind, "artifact")
            self.assertIn("CRAM_LLM_API_KEY", result.message)
            self.assertEqual(result.wrote, [])
            self.assertFalse((workspace.output_dir / "速成计划.md").exists())

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
            self.assertIn("已建立索引：1 个片段", result.message)
            self.assertIn("暂未处理：1 个文件", result.message)
            self.assertNotIn("Scanned", result.message)

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

            self.assertIn("MinerU 已解析：1 个文件", result.message)
            self.assertIn("已建立索引：1 个片段", result.message)
            self.assertIn("slides.pdf:mineru:1", (workspace.cram_dir / "index" / "chunks.jsonl").read_text(encoding="utf-8"))

    def test_ingest_warns_when_running_inside_code_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "cram-engine")
            (workspace.root / ".git").mkdir()
            (workspace.root / "README.md").write_text("# project", encoding="utf-8")

            def fake_ingest(workspace, sources):
                return MaterialIngestResult(parsed_texts=[], processed_files=0, failed_files=[], pending_files=[])

            result = CommandRouter(workspace, material_ingester=fake_ingest).handle("/ingest")

            self.assertIn("你现在可能在代码仓库里运行 cram", result.message)
            self.assertIn("请先进入某个学科资料文件夹", result.message)

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
            self.assertNotIn("当前阶段还没有接入资料检索", system_content)

    def test_free_text_can_stream_llm_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            llm = FakeStreamingLLM()
            router = CommandRouter(workspace, llm=llm)

            events = list(router.stream("帮我讲一下采样定理"))

            self.assertEqual([e.text for e in events if e.kind == "content"], ["采样", "定理"])
            events_log = router.memory.load_recent_session_events()
            self.assertEqual(events_log[-1]["role"], "agent")
            self.assertEqual(events_log[-1]["content"], "采样定理")

    def test_stream_surfaces_reasoning_then_content_and_saves_only_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp))
            router = CommandRouter(workspace, llm=FakeReasoningLLM())

            events = list(router.stream("帮我讲一下采样定理"))

            self.assertEqual(
                [(e.kind, e.text) for e in events],
                [("reasoning", "先回忆采样定理…"), ("content", "采样"), ("content", "定理")],
            )
            saved = router.memory.load_recent_session_events()[-1]
            self.assertEqual(saved["role"], "agent")
            self.assertEqual(saved["content"], "采样定理")  # reasoning is not persisted

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
