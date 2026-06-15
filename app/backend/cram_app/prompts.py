from __future__ import annotations

from .chunks import ChunkRecord


SOURCE_GROUNDED_RULES = """你是期末速成引擎，不是通用聊天助手。

生成必须遵守：
- 资料优先，重要结论尽量来自给定资料。
- 来源优先，回答中尽量保留来源标签。
- 整合优先，跨资料合并同一知识点，不按文件机械摘要。
- 思维导图结构优先，场景解释只在帮助理解时出现。
- 如果资料中未找到明确出处，必须说明“资料中未找到明确出处，以下为推理性解释”。
"""


def build_review_prompt(user_message: str, chunks: list[ChunkRecord]) -> str:
    evidence = "\n\n".join(
        f"[{chunk.citation_label}]\n{chunk.text}"
        for chunk in chunks
    )
    return f"""{SOURCE_GROUNDED_RULES}

用户请求：
{user_message}

可用资料：
{evidence}

请基于资料回答，并在关键结论旁标注来源标签。
"""

