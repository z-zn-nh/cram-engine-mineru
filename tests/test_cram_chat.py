import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.chat import CramChatService
from app.backend.cram_app.chunks import ChunkRecord, append_chunks
from app.backend.cram_app.subjects import create_subject


class FakeLLM:
    def __init__(self):
        self.messages = []

    def chat(self, messages, *, stream=False):
        self.messages = messages
        return "调制解调的核心是搬移频谱并恢复基带信号。"


class CramChatTests(unittest.TestCase):
    def test_chat_retrieves_chunks_and_returns_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))
            append_chunks(
                subject,
                [
                    ChunkRecord("a", "教材.pdf", "p45", "调制 解调 载波 基带信号"),
                    ChunkRecord("b", "教材.pdf", "p2", "随机过程 噪声"),
                ],
            )
            llm = FakeLLM()

            response = CramChatService(llm).review(subject, "先讲调制解调")

            self.assertIn("调制解调", response.message)
            self.assertEqual(response.citations[0]["citation_label"], "教材.pdf:p45")
            prompt = llm.messages[0]["content"]
            self.assertIn("资料优先", prompt)
            self.assertIn("来源优先", prompt)
            self.assertIn("资料中未找到明确出处", prompt)
            self.assertIn("教材.pdf:p45", prompt)

    def test_chat_returns_no_evidence_message_without_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = create_subject("通信原理", Path(tmp))
            llm = FakeLLM()

            response = CramChatService(llm).review(subject, "讲一下调制解调")

            self.assertIn("资料中未找到明确出处", response.message)
            self.assertEqual(response.citations, [])
            self.assertEqual(llm.messages, [])


if __name__ == "__main__":
    unittest.main()
