from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .workspace import CramWorkspace


VALID_HOOKS = {"acronym", "contrast", "absurd", "none"}

# Words that steer an in-progress teaching session instead of being a normal answer.
_STOP_WORDS = ("退出", "结束教学", "停一下", "停下", "不学了", "先这样", "算了", "stop", "quit")
_RETEACH_WORDS = ("再讲", "重讲", "没懂", "不懂", "没听懂", "没明白", "不太明白", "换个", "换种", "换个讲法", "再来一遍")


@dataclass
class KnowledgePoint:
    title: str
    hook: str = "none"
    status: str = "pending"  # pending | taught | mastered | stubborn

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgePoint":
        hook = str(data.get("hook", "none")).lower()
        return cls(
            title=str(data.get("title", "")).strip(),
            hook=hook if hook in VALID_HOOKS else "none",
            status=str(data.get("status", "pending")),
        )


@dataclass
class TeachingSession:
    topic: str
    points: list[KnowledgePoint] = field(default_factory=list)
    current: int = 0
    started: bool = False
    taught_since_checkin: int = 0
    stage: str = "teach"  # teach | test | remediate | done

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "points": [point.to_dict() for point in self.points],
            "current": self.current,
            "started": self.started,
            "taught_since_checkin": self.taught_since_checkin,
            "stage": self.stage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeachingSession":
        return cls(
            topic=str(data.get("topic", "")),
            points=[KnowledgePoint.from_dict(item) for item in data.get("points", [])],
            current=int(data.get("current", 0)),
            started=bool(data.get("started", False)),
            taught_since_checkin=int(data.get("taught_since_checkin", 0)),
            stage=str(data.get("stage", "teach")),
        )

    @property
    def finished(self) -> bool:
        return self.current >= len(self.points)

    def current_point(self) -> KnowledgePoint | None:
        if 0 <= self.current < len(self.points):
            return self.points[self.current]
        return None


def session_path(workspace: CramWorkspace) -> Path:
    return workspace.cram_dir / "teaching" / "session.json"


def has_active_session(workspace: CramWorkspace) -> bool:
    return session_path(workspace).exists()


def load_session(workspace: CramWorkspace) -> TeachingSession | None:
    path = session_path(workspace)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return TeachingSession.from_dict(data)


def save_session(workspace: CramWorkspace, session: TeachingSession) -> Path:
    path = session_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def clear_session(workspace: CramWorkspace) -> None:
    session_path(workspace).unlink(missing_ok=True)


def classify_teaching_input(message: str) -> str:
    """Return one of 'stop' | 'reteach' | 'advance' for an in-session user message."""
    text = message.strip().lower()
    if any(word in text for word in _STOP_WORDS):
        return "stop"
    if any(word in text for word in _RETEACH_WORDS):
        return "reteach"
    return "advance"


def parse_tree(text: str) -> list[KnowledgePoint]:
    """Parse a deconstruct response into knowledge points.

    Accepts a JSON object/array of points; falls back to treating each non-empty
    line as a point so a non-JSON model answer still yields a usable tree.
    """
    points = _parse_tree_json(text)
    if points:
        return points
    return _parse_tree_lines(text)


def _parse_tree_json(text: str) -> list[KnowledgePoint]:
    start = text.find("{")
    bracket = text.find("[")
    if bracket != -1 and (start == -1 or bracket < start):
        start = bracket
    if start == -1:
        return []
    snippet = text[start:]
    for end in range(len(snippet), 0, -1):
        chunk = snippet[:end].strip()
        if not chunk:
            continue
        try:
            data = json.loads(chunk)
        except ValueError:
            continue
        items = data.get("points") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        points = [KnowledgePoint.from_dict(item) for item in items if isinstance(item, dict)]
        return [point for point in points if point.title]
    return []


def _parse_tree_lines(text: str) -> list[KnowledgePoint]:
    points: list[KnowledgePoint] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*0123456789.、) ").strip()
        if len(line) >= 2 and not line.startswith(("#", "{", "}", "[", "]")):
            points.append(KnowledgePoint(title=line))
    return points


def render_tree(session: TeachingSession) -> str:
    hook_label = {"acronym": "口诀", "contrast": "对比", "absurd": "联想", "none": ""}
    lines = [f"知识点树：{session.topic}"]
    for index, point in enumerate(session.points, start=1):
        tag = hook_label.get(point.hook, "")
        suffix = f"  [{tag}]" if tag else ""
        lines.append(f"  {index}. {point.title}{suffix}")
    lines.append("")
    lines.append(f"共 {len(session.points)} 个知识点。回复「开始」逐点讲解，「跳过」直接检验，「退出」结束教学。")
    return "\n".join(lines)


def deconstruct_messages(topic: str, course: str, evidence_block: str) -> list[dict]:
    system_prompt = f"""你是期末速成引擎，正在为课程「{course}」拆解复习主题「{topic}」。

任务：把该主题拆成一组「5分钟能讲完」的独立知识点，并按讲解的逻辑顺序排列。
为每个知识点标注一个记忆钩子类型 hook：
- acronym：适合编口诀/缩写记忆
- contrast：与另一概念易混淆，需要对比
- absurd：抽象易忘，适合用荒诞场景锚定
- none：直接讲即可

只输出 JSON，不要任何多余文字，格式：
{{"points": [{{"title": "知识点名称", "hook": "acronym|contrast|absurd|none"}}]}}

控制在 4-8 个知识点。优先依据下方课程资料；资料不足时用通用学科知识补充。
"""
    if evidence_block:
        system_prompt += f"\n课程资料片段：\n\n{evidence_block}\n"
    else:
        system_prompt += "\n（未检索到课程资料，请基于通用学科知识拆解。）\n"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请拆解「{topic}」的知识点树。"},
    ]


def teach_messages(
    session: TeachingSession,
    user_message: str,
    course: str,
    evidence_block: str,
    *,
    reteach: bool = False,
) -> list[dict]:
    point = session.current_point()
    title = point.title if point else session.topic
    hook = point.hook if point else "none"
    tree_lines = []
    for index, item in enumerate(session.points):
        marker = "→" if index == session.current else " "
        tree_lines.append(f"{marker} {index + 1}. {item.title}")
    tree = "\n".join(tree_lines)

    system_prompt = f"""你是期末速成引擎，正在用「四步教学法」带学生复习课程「{course}」的主题「{session.topic}」。

知识点树（→ 是当前要讲的）：
{tree}

现在只讲第 {session.current + 1}/{len(session.points)} 个知识点：{title}（记忆钩子：{hook}）。

四步教学法，严格按顺序：
1. 具体优先：第一句必须是贴近大学生生活的具体场景，禁止用定义开头。
2. 分块：拆成不超过 3 个关键块，逐块讲清楚。
3. 精细加工：讲完追问「这和前面哪个知识点有关系」。
4. 生成效应：核心概念先别直接给标准定义，反问学生、让他自己先试着总结。
记忆钩子：acronym→编口诀；contrast→给对比；absurd→用荒诞场景；none→直接讲。

要求：
- 中文、口语化、不堆术语，先给一句话核心结论再展开。
- 只讲这一个知识点，结尾用一个问题收住（让学生总结或追问关系），然后停下等他回应。
- 若下方有课程资料，优先依据资料，并在用到处用方括号标注来源标签。
"""
    if reteach:
        system_prompt += "\n学生表示没太听懂，请换一个全新的场景和角度重讲这个知识点，不要重复上一次的讲法。\n"
    elif session.started:
        system_prompt += (
            f"\n学生上一条回应是：「{user_message}」。先用一两句点评他的理解"
            "（肯定对的、补正不准的），再开始讲当前这个知识点。\n"
        )
    if evidence_block:
        system_prompt += f"\n课程资料片段：\n\n{evidence_block}\n"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message or "开始"},
    ]
