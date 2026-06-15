from __future__ import annotations

from dataclasses import dataclass

from .chunks import ChunkRecord, search_chunks
from .llm import LLMClient
from .prompts import build_review_prompt
from .subjects import Subject


@dataclass(frozen=True)
class CramChatResponse:
    message: str
    citations: list[dict]
    artifacts: list[dict]


def _citation_payload(chunks: list[ChunkRecord]) -> list[dict]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "source_file": chunk.source_file,
            "locator": chunk.locator,
            "citation_label": chunk.citation_label,
            "excerpt": chunk.text,
        }
        for chunk in chunks
    ]


class CramChatService:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def review(self, subject: Subject, message: str) -> CramChatResponse:
        chunks = search_chunks(subject, message, limit=5)
        if not chunks:
            return CramChatResponse(
                message="资料中未找到明确出处，以下为推理性解释：当前学科还没有可检索资料，请先导入并解析课程资料。",
                citations=[],
                artifacts=[],
            )

        prompt = build_review_prompt(message, chunks)
        answer = self.llm.chat([{"role": "system", "content": prompt}], stream=False)
        return CramChatResponse(message=answer, citations=_citation_payload(chunks), artifacts=[])

