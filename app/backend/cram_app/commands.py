from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .llm import LLMClient, LLMConfigurationError, LLMRequestError, OpenAICompatibleClient
from .memory import MemoryStore
from .settings import LLMSettings, load_effective_llm_config
from .workspace import CramWorkspace, discover_workspace_sources


ARTIFACT_COMMANDS = {
    "/plan": ("速成计划.md", "期末速成计划"),
    "/notes": ("知识点整合.md", "知识点整合"),
    "/mindmap": ("思维导图.md", "思维导图"),
    "/quiz": ("题库.md", "题库"),
    "/summary": ("考前总结.md", "考前总结"),
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
/help     查看命令

直接输入问题即可继续复习对话。
"""


@dataclass(frozen=True)
class CommandResult:
    kind: str
    message: str
    wrote: list[Path] = field(default_factory=list)


class CommandRouter:
    def __init__(self, workspace: CramWorkspace, *, llm: LLMClient | None = None):
        self.workspace = workspace
        self.memory = MemoryStore.open(workspace)
        self.llm = llm or _default_llm_client()

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
        manifest = self.workspace.cram_dir / "raw_manifest.json"
        manifest.write_text(
            "\n".join(source.relative_path.as_posix() for source in sources),
            encoding="utf-8",
        )
        return CommandResult(
            kind="ingest",
            message=(
                f"已扫描 {len(sources)} 个资料文件。第一版会先记录清单；"
                "后续接入 MinerU 后会解析 PDF/PPT/图片并建立索引。\n"
                f"Wrote {manifest.relative_to(self.workspace.root).as_posix()}"
            ),
            wrote=[manifest],
        )

    def _write_artifact(self, command: str) -> CommandResult:
        filename, title = ARTIFACT_COMMANDS[command]
        output_path = self.workspace.output_dir / filename
        references = self.memory.build_reference_catalog()
        reference_lines = "\n".join(f"- {reference.label}" for reference in references[:10])
        content = f"""# {title}

> 当前文件夹：{self.workspace.course_name}

本文件由期末速成 TUI Agent 生成。第一版先建立稳定输出位置和引用回流机制，后续会接入 LLM 正式生成内容。

## 可用引用

{reference_lines or "- 资料中未找到明确出处"}
"""
        output_path.write_text(content, encoding="utf-8")
        return CommandResult(
            kind="artifact",
            message=f"Wrote {output_path.relative_to(self.workspace.root).as_posix()}",
            wrote=[output_path],
        )

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

    def _llm_messages(self, message: str) -> list[dict]:
        system_prompt = f"""你是期末速成引擎，一个面向考前复习的中文学习 Agent。

当前课程文件夹：{self.workspace.course_name}

回答规则：
- 先帮助用户理解概念、考点和易错点。
- 用中文回答，结构清晰，适合考前快速复习。
- 当前阶段还没有接入资料检索；如果需要引用课程资料，明确说明需要先运行 /ingest。
- 不要编造不存在的资料来源或页码。
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

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
