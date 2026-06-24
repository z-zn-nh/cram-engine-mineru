from __future__ import annotations

import html
import re
from dataclasses import dataclass, field


@dataclass
class MindNode:
    label: str
    children: list["MindNode"] = field(default_factory=list)


# Headings rank 1-6; list items always rank deeper (100+indent) so they nest under the
# nearest heading, and relative indent gives nesting among themselves. This unified
# depth lets one stack parse mixed headings + bullet lists.
_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET = re.compile(r"^(\s*)[-*+]\s+(.+)$")


def parse_outline(text: str) -> MindNode:
    """Parse a markdown outline (headings and/or nested bullets) into a tree.

    Returns a synthetic root (label "") whose children are the top-level nodes.
    """
    root = MindNode("")
    stack: list[tuple[int, MindNode]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip():
            continue
        heading = _HEADING.match(raw.strip())
        if heading:
            depth = len(heading.group(1))
            label = _clean_label(heading.group(2))
        else:
            bullet = _BULLET.match(raw)
            if not bullet:
                continue
            indent = len(bullet.group(1).replace("\t", "  "))
            depth = 100 + indent
            label = _clean_label(bullet.group(2))
        if not label:
            continue
        node = MindNode(label)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        stack[-1][1].children.append(node)
        stack.append((depth, node))
    return root


def _clean_label(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [t](url) -> t
    text = re.sub(r"[*_`]+", "", text)  # drop md emphasis / code marks
    return text.strip()


def normalize_root(tree: MindNode, topic: str) -> MindNode:
    """Ensure a single titled root: collapse a synthetic root, or wrap multiple tops under topic."""
    children = [c for c in tree.children] if tree.label == "" else [tree]
    if len(children) == 1:
        return children[0]
    return MindNode(_clean_label(topic) or "思维导图", children)


def count_nodes(node: MindNode) -> int:
    return sum(1 + count_nodes(child) for child in node.children)


def max_depth(node: MindNode) -> int:
    if not node.children:
        return 0
    return 1 + max(max_depth(child) for child in node.children)


def validate_mindmap(tree: MindNode, *, min_nodes: int = 4) -> list[str]:
    """Return a list of problems; empty means the outline is a usable mind map."""
    errors: list[str] = []
    real = [c for c in tree.children] if tree.label == "" else [tree]
    if not real:
        return ["输出里没有解析到任何知识点"]
    total = sum(count_nodes(node) + 1 for node in real)
    if total < min_nodes:
        errors.append(f"知识点太少（{total} 个，至少 {min_nodes} 个）")
    if max(max_depth(node) for node in real) < 1:
        errors.append("没有层级结构（应该是一棵有分支的树，而不是平铺一行）")
    if _has_empty(MindNode("", real)):
        errors.append("存在空节点")
    return errors


def _has_empty(node: MindNode) -> bool:
    for child in node.children:
        if not child.label.strip():
            return True
        if _has_empty(child):
            return True
    return False


def to_markdown(root: MindNode) -> str:
    lines: list[str] = []

    def walk(node: MindNode, depth: int) -> None:
        if depth == 0:
            lines.append(f"# {node.label}")
        else:
            lines.append(f"{'  ' * (depth - 1)}- {node.label}")
        for child in node.children:
            walk(child, depth + 1)

    walk(root, 0)
    return "\n".join(lines) + "\n"


def to_opml(root: MindNode, title: str) -> str:
    def outline(node: MindNode, depth: int) -> str:
        indent = "  " * depth
        text = html.escape(node.label, quote=True)
        if node.children:
            inner = "".join(outline(child, depth + 1) for child in node.children)
            return f'{indent}<outline text="{text}">\n{inner}{indent}</outline>\n'
        return f'{indent}<outline text="{text}"/>\n'

    body = outline(root, 2)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<opml version="2.0">\n'
        f"  <head><title>{html.escape(title, quote=True)}</title></head>\n"
        "  <body>\n"
        f"{body}"
        "  </body>\n"
        "</opml>\n"
    )


def to_markmap_html(markdown: str, title: str) -> str:
    # markmap-autoloader reads the markdown from the inner <script type="text/template">.
    # Only a literal "</script" could close it early; neutralize that (won't appear in a mind map).
    safe = re.sub(r"</(script)", r"<\\/\1", markdown, flags=re.IGNORECASE)
    return (
        "<!DOCTYPE html>\n<html lang=\"zh\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{html.escape(title)}</title>\n"
        "<style>html,body{margin:0;height:100%;background:#0f1115}"
        ".markmap{position:fixed;inset:0}.markmap>svg{width:100%;height:100%}</style>\n"
        "</head>\n<body>\n"
        '<div class="markmap"><script type="text/template">\n'
        f"{safe}\n"
        "</script></div>\n"
        '<script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@latest"></script>\n'
        "</body>\n</html>\n"
    )
