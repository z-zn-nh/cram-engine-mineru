import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.backend.cram_app.api import create_app
from app.backend.cram_app.artifacts import save_artifact
from app.backend.cram_app.chunks import ChunkRecord, append_chunks
from app.backend.cram_app.subjects import create_subject


class FakeLLM:
    def chat(self, messages, *, stream=False):
        return "基于资料回答。"


class ApiContractTests(unittest.TestCase):
    def test_health_and_subjects(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(subjects_root=Path(tmp), llm=FakeLLM()))

            self.assertEqual(client.get("/health").json(), {"ok": True})

            created = client.post("/subjects", json={"name": "通信原理"})
            self.assertEqual(created.status_code, 200)
            self.assertEqual(created.json()["name"], "通信原理")

            listed = client.get("/subjects")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.json()[0]["name"], "通信原理")

    def test_subject_chat_returns_citations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = create_subject("通信原理", root)
            append_chunks(subject, [ChunkRecord("a", "教材.pdf", "p45", "调制 解调 载波")])
            client = TestClient(create_app(subjects_root=root, llm=FakeLLM()))

            response = client.post("/subjects/通信原理/chat", json={"message": "调制解调"})

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["message"], "基于资料回答。")
            self.assertEqual(payload["citations"][0]["citation_label"], "教材.pdf:p45")

    def test_artifacts_and_citations_endpoints_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_subject("通信原理", root)
            client = TestClient(create_app(subjects_root=root, llm=FakeLLM()))

            self.assertEqual(client.get("/subjects/通信原理/artifacts").status_code, 200)
            self.assertEqual(client.get("/subjects/通信原理/citations").status_code, 200)

    def test_artifact_content_endpoint_reads_inside_subject_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = create_subject("signals", root)
            artifact = save_artifact(
                subject,
                artifact_type="notes",
                title="chapter-1",
                content="# Signals\n\nCore notes.",
                citations=[],
                fmt="md",
            )
            client = TestClient(create_app(subjects_root=root, llm=FakeLLM()))

            response = client.get(
                "/subjects/signals/artifacts/content",
                params={"relative_path": artifact.relative_path.as_posix()},
            )

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["relative_path"], artifact.relative_path.as_posix())
            self.assertEqual(payload["content"], "# Signals\n\nCore notes.")

            escaped = client.get(
                "/subjects/signals/artifacts/content",
                params={"relative_path": "../subject.sqlite"},
            )
            self.assertEqual(escaped.status_code, 400)


if __name__ == "__main__":
    unittest.main()
