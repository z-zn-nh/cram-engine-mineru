from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .llm import (
    LLMClient,
    LLMConfigurationError,
    LLMRequestError,
    OpenAICompatibleClient,
    StreamEvent,
)
from .memory import MemoryStore
from .settings import LLMSettings, load_effective_llm_config
from .workspace import CramWorkspace, discover_workspace_sources
from .workspace_ingest import MaterialIngestResult, ingest_material_sources
from .workspace_index import (
    ChunkRecord,
    index_text_sources,
    load_workspace_chunks,
    search_workspace_chunks,
)


ARTIFACT_COMMANDS = {
    "/plan": (
        "速成计划.md",
        "期末速成计划",
        "输出一份考前速成路线：按优先级列出必须先掌握的考点，给出建议的学习顺序与时间分配，突出老师强调和高频考点。",
    ),
    "/notes": (
        "知识点整合.md",
        "知识点整合",
        "把分散在各份资料里的同一知识点整合成结构化笔记，按主题归类，每个知识点给出定义、关键要点和易混淆点。",
    ),
    "/mindmap": (
        "思维导图.md",
        "思维导图",
        "用 Markdown 多级无序列表输出思维导图，体现 章节 → 概念 → 关系 → 易混点 → 高频考点 的层级结构，结构优先于细节。",
    ),
    "/quiz": (
        "题库.md",
        "题库",
        "按常见考试题型出题（如选择、判断、简答、计算），覆盖重点考点；每题给出参考答案和踩分点。",
    ),
    "/summary": (
        "考前总结.md",
        "考前总结",
        "输出考前冲刺总结：必背要点清单、最易出错的点、以及考前最后一天的复习清单。",
    ),
}

HELP_TEXT = """可用命令：
/ingest   解析并索引当前文件夹资料
/status   查看资料、记忆和输出状态
/plan     生成速成计划
/notes    生成知识点整合
/mindmap  生成思维导图
/quiz     生成题库
/summary  生成考前总结
/lint     检查记忆、输出和引用冲突
/config   重新配置 LLM
/model    切换对话模型
/help     查看命令

直接输入问题即可继续复习对话。
"""


@dataclass(frozen=True)
class CommandResult:
    kind: str
    message: str
    wrote: list[Path] = field(default_factory=list)


class CommandRouter:
    def __init__(self, workspace: CramWorkspace, *, llm: LLMClient | None = None, material_ingester=None):
        self.workspace = workspace
        self.memory = MemoryStore.open(workspace)
        self.llm = llm or _default_llm_client()
        self.material_ingester = material_ingester or ingest_material_sources

    def handle(self, text: str) -> CommandResult:
        message = text.strip()
        if not message:
            return CommandResult(kind="empty", message="")

        self.memory.append_session_event("user", message)

        command = message.split(maxsplit=1)[0].lower()
        if command == "/help":
            return self._remember(CommandResult(kind="help", message=HELP_TEXT))
        if command == "/status":
            return self._remember(self._status())
        if command == "/lint":
            return self._remember(self._lint())
        if command == "/config":
            return CommandResult(kind="config", message="")
        if command == "/model":
            return CommandResult(kind="model", message="")
        if command == "/ingest":
            return self._remember(self._ingest_status())
        if command in ARTIFACT_COMMANDS:
            return self._remember(self._write_artifact(command))

        return self._remember(self._ask_llm(message))

    def _remember(self, result: CommandResult) -> CommandResult:
        if result.message:
            self.memory.append_session_event("agent", result.message)
        return result

    def _status(self) -> CommandResult:
        sources = discover_workspace_sources(self.workspace.root)
        outputs = [path for path in self.workspace.output_dir.rglob("*") if path.is_file()]
        references = self.memory.build_reference_catalog()
        message = (
            f"{self.workspace.course_name}\n"
            f"- {len(sources)} 个资料文件\n"
            f"- {len(outputs)} 个输出产物\n"
            f"- {len(references)} 个可引用条目\n"
            f"- 记忆目录：{self.workspace.cram_dir.relative_to(self.workspace.root).as_posix()}\n"
            f"- 输出目录：{self.workspace.output_dir.relative_to(self.workspace.root).as_posix()}"
        )
        return CommandResult(kind="status", message=message)

    def _ingest_status(self) -> CommandResult:
        sources = discover_workspace_sources(self.workspace.root)
        material_result: MaterialIngestResult = self.material_ingester(self.workspace, sources)
        index_result = index_text_sources(self.workspace, extra_texts=material_result.parsed_texts)
        manifest = self.workspace.cram_dir / "raw_manifest.json"
        manifest.write_text(
            "\n".join(source.relative_path.as_posix() for source in sources),
            encoding="utf-8",
        )
        return CommandResult(
            kind="ingest",
            message=_format_ingest_message(
                workspace=self.workspace,
                total_sources=len(sources),
                material_result=material_result,
                indexed_chunks=index_result.indexed_chunks,
                indexed_files=index_result.indexed_files,
            ),
        )

    def _write_artifact(self, command: str) -> CommandResult:
        filename, title, instruction = ARTIFACT_COMMANDS[command]
        output_path = self.workspace.output_dir / filename
        evidence = self._collect_artifact_evidence()
        try:
            body = self.llm.chat(self._artifact_messages(title, instruction, evidence), stream=False)
        except LLMConfigurationError as exc:
            return CommandResult(kind="artifact", message=_llm_setup_message(exc))
        except LLMRequestError as exc:
            return CommandResult(
                kind="artifact",
                message=(
                    "生成失败，未写入文件。请检查模型服务地址、模型名和网络状态。\n"
                    f"{exc}"
                ),
            )
        output_path.write_text(self._format_artifact_file(body, evidence), encoding="utf-8")
        return CommandResult(
            kind="artifact",
            message=f"Wrote {output_path.relative_to(self.workspace.root).as_posix()}",
            wrote=[output_path],
        )

    def _collect_artifact_evidence(self, *, limit_chars: int = 12000) -> list[ChunkRecord]:
        selected: list[ChunkRecord] = []
        total = 0
        for chunk in load_workspace_chunks(self.workspace):
            if selected and total + len(chunk.text) > limit_chars:
                break
            selected.append(chunk)
            total += len(chunk.text)
        return selected

    def _artifact_messages(self, title: str, instruction: str, evidence: list[ChunkRecord]) -> list[dict]:
        system_prompt = f"""你是期末速成引擎，为课程「{self.workspace.course_name}」生成可复用的复习产物：{title}。

生成原则：
- 资料优先：结论、定义、公式、考点尽量来自下方课程资料。
- 来源优先：用到资料的地方，在句末用方括号标注来源标签，例如 [a.pdf:mineru:1]。
- 整合优先：跨文件合并同一知识点，不要按文件机械罗列。
- 找不到依据就说明：资料中没有的内容标注为「推理补充」，不要编造来源或页码。
- 直接输出 Markdown 正文，不要寒暄或自我介绍。

本次任务：{instruction}
"""
        if evidence:
            evidence_block = "\n\n".join(
                f"[{chunk.citation_label}]\n{chunk.text}" for chunk in evidence
            )
            system_prompt += f"\n课程资料片段：\n\n{evidence_block}\n"
        else:
            system_prompt += (
                "\n当前没有已索引的课程资料。请基于通用知识生成，"
                "并在开头用一句话说明：未检索到课程资料，建议先运行 /ingest 导入资料。\n"
            )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请生成《{title}》。"},
        ]

    @staticmethod
    def _format_artifact_file(body: str, evidence: list[ChunkRecord]) -> str:
        if evidence:
            labels = "\n".join(f"- {chunk.citation_label}" for chunk in evidence)
            provenance = f"## 参考资料\n\n{labels}\n"
        else:
            provenance = "## 参考资料\n\n- 未检索到课程资料（建议先运行 /ingest）\n"
        return f"{body.strip()}\n\n---\n\n{provenance}"

    def _ask_llm(self, message: str) -> CommandResult:
        try:
            answer = self.llm.chat(self._llm_messages(message), stream=False)
        except LLMConfigurationError as exc:
            answer = _llm_setup_message(exc)
        except LLMRequestError as exc:
            answer = (
                "LLM 请求失败，当前会话已保留。请检查模型服务地址、模型名和网络状态。\n"
                f"{exc}"
            )
        return CommandResult(kind="ask", message=answer)

    def stream(self, message: str):
        self.memory.append_session_event("user", message)
        if not hasattr(self.llm, "stream_chat"):
            result = self._remember(self._ask_llm(message))
            if result.message:
                yield StreamEvent("content", result.message)
            return

        content_parts: list[str] = []
        try:
            for event in self.llm.stream_chat(self._llm_messages(message)):
                if not isinstance(event, StreamEvent):
                    event = StreamEvent("content", str(event))
                if event.kind == "content":
                    content_parts.append(event.text)
                yield event
        except LLMConfigurationError as exc:
            message_text = _llm_setup_message(exc)
            self.memory.append_session_event("agent", message_text)
            yield StreamEvent("content", message_text)
        except LLMRequestError as exc:
            message_text = (
                "LLM 请求失败，当前会话已保留。请检查模型服务地址、模型名和网络状态。\n"
                f"{exc}"
            )
            self.memory.append_session_event("agent", message_text)
            yield StreamEvent("content", message_text)
        else:
            answer = "".join(content_parts)
            if answer:
                self.memory.append_session_event("agent", answer)

    def _llm_messages(self, message: str) -> list[dict]:
        system_prompt = f"""你是期末速成引擎，一个面向考前复习的中文学习 Agent。

当前课程文件夹：{self.workspace.course_name}

回答规则：
- 先帮助用户理解概念、考点和易错点。
- 用中文回答，结构清晰，适合考前快速复习。
- 如果下方提供了课程资料片段，优先基于资料回答，并用方括号引用来源标签。
- 如果没有检索到课程资料，明确建议先运行 /ingest。
- 不要编造不存在的资料来源或页码。
"""
        evidence = search_workspace_chunks(self.workspace, message, limit=5)
        if evidence:
            evidence_block = "\n\n".join(
                f"[{chunk.citation_label}]\n{chunk.text}" for chunk in evidence
            )
            system_prompt += (
                "\nIndexed course references are available below. "
                "Prefer them over memory and cite labels in square brackets.\n\n"
                f"{evidence_block}\n"
            )
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": message})
        return messages

    def _lint(self) -> CommandResult:
        conflicts = self.memory.load_conflicts()
        references = self.memory.build_reference_catalog()
        if conflicts:
            conflict_lines = "\n".join(f"- {item['title']}: {item['left']} <> {item['right']}" for item in conflicts)
        else:
            conflict_lines = "- 暂未记录冲突"
        return CommandResult(
            kind="lint",
            message=(
                "记忆健康检查\n"
                f"- 可引用条目：{len(references)}\n"
                f"- 冲突记录：{len(conflicts)}\n"
                f"{conflict_lines}"
            ),
        )


def _default_llm_client() -> LLMClient:
    config = load_effective_llm_config()
    if config:
        return OpenAICompatibleClient(
            LLMSettings(
                provider="openai-compatible",
                base_url=config.base_url,
                model=config.model,
            ),
            api_key=config.api_key,
        )
    return OpenAICompatibleClient(_llm_settings_from_env())


def _llm_settings_from_env() -> LLMSettings:
    return LLMSettings(
        provider="openai-compatible",
        base_url=os.environ.get("CRAM_LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("CRAM_LLM_MODEL", "gpt-4o-mini"),
        api_key_env=os.environ.get("CRAM_LLM_API_KEY_ENV", "CRAM_LLM_API_KEY"),
    )


def _format_ingest_message(
    *,
    workspace: CramWorkspace,
    total_sources: int,
    material_result: MaterialIngestResult,
    indexed_chunks: int,
    indexed_files: int,
) -> str:
    lines = [
        "资料扫描完成。",
        f"- 当前文件夹：{workspace.root}",
        f"- 找到资料：{total_sources} 个文件",
        f"- MinerU 已解析：{material_result.processed_files} 个文件",
        f"- 已建立索引：{indexed_chunks} 个片段，来自 {indexed_files} 个文本/解析结果",
    ]
    if material_result.pending_files:
        lines.append(f"- 暂未处理：{len(material_result.pending_files)} 个文件（{_preview_names(material_result.pending_files)}）")
    else:
        lines.append("- 暂未处理：0 个文件")
    if material_result.failed_files:
        lines.append(f"- 解析失败：{len(material_result.failed_files)} 个文件（{_preview_names(material_result.failed_files)}）")
    else:
        lines.append("- 解析失败：0 个文件")
    if _looks_like_code_repository(workspace.root):
        lines.extend(
            [
                "",
                "提示：你现在可能在代码仓库里运行 cram。",
                "请先进入某个学科资料文件夹，比如 D:\\期末资料\\通信原理，再运行 cram 和 /ingest。",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "下一步：直接提问，或输入 /notes、/mindmap、/quiz 生成复习产物。",
            ]
        )
    return "\n".join(lines)


def _looks_like_code_repository(path: Path) -> bool:
    code_markers = {
        ".git",
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
    }
    return any((path / marker).exists() for marker in code_markers)


def _preview_names(paths: list[str], *, limit: int = 3) -> str:
    shown = paths[:limit]
    suffix = "" if len(paths) <= limit else f" 等 {len(paths)} 个"
    return "、".join(shown) + suffix


def _llm_setup_message(error: Exception) -> str:
    return (
        "LLM 还没有配置好，当前问题已记录，但不会调用模型。\n\n"
        f"{error}\n\n"
        "在新终端里配置：\n"
        'setx CRAM_LLM_API_KEY "你的密钥"\n'
        'setx CRAM_LLM_BASE_URL "https://api.openai.com/v1"\n'
        'setx CRAM_LLM_MODEL "gpt-4o-mini"\n\n'
        "配置后重新打开终端，再进入学科资料文件夹运行 cram。"
    )


def main() -> int:
    workspace = CramWorkspace.open(Path.cwd())
    router = CommandRouter(workspace)
    print(router.handle("/status").message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
