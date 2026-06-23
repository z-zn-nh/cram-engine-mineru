from __future__ import annotations

import re

try:
    from pylatexenc.latex2text import LatexNodes2Text

    _CONVERTER = LatexNodes2Text()
except ImportError:  # pragma: no cover - optional dependency
    _CONVERTER = None


# Private-use delimiter for stashing sub/superscripts past pylatexenc (it preserves U+E000).
_MARK = chr(0xE000)

_SUPERSCRIPT = dict(
    zip(
        "0123456789+-=()abcdefghijklmnoprstuvwxy",
        "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸ",
    )
)
_SUBSCRIPT = dict(
    zip(
        "0123456789+-=()aehijklmnoprstuvx",
        "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ",
    )
)


def render_math(text: str) -> str:
    """Convert LaTeX math spans ($...$, $$...$$, \\(...\\), \\[...\\]) to Unicode.

    Code spans and fenced code blocks are protected so a literal '$' in code is left
    alone. Returns the text unchanged when pylatexenc is unavailable or there is no math.
    """
    if _CONVERTER is None:
        return text
    if "$" not in text and "\\(" not in text and "\\[" not in text:
        return text

    protected: list[str] = []

    def protect(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"\x00{len(protected) - 1}\x00"

    text = re.sub(r"```.*?```", protect, text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", protect, text)

    text = re.sub(r"\$\$(.+?)\$\$", lambda m: latex_to_unicode(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r"\\\[(.+?)\\\]", lambda m: latex_to_unicode(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r"\\\((.+?)\\\)", lambda m: latex_to_unicode(m.group(1)), text)
    text = re.sub(r"(?<!\\)\$(?!\s)([^$\n]+?)(?<!\s)\$", lambda m: latex_to_unicode(m.group(1)), text)

    return re.sub(r"\x00(\d+)\x00", lambda m: protected[int(m.group(1))], text)


def latex_to_unicode(latex: str) -> str:
    # Stash sub/superscripts as U+E000-delimited placeholders first, so pylatexenc converts the
    # \commands (Greek, operators) without seeing converted scripts (it would mangle "\sum<sub>"),
    # and so braces are not stripped before we map multi-char scripts like _{max}.
    scripts: list[str] = []

    def stash(replacement: str) -> str:
        scripts.append(replacement)
        return f"{_MARK}{len(scripts) - 1}{_MARK}"

    s = re.sub(r"\^\{([^{}]*)\}", lambda m: stash(_script(m.group(1), _SUPERSCRIPT, m.group(0))), latex)
    s = re.sub(r"_\{([^{}]*)\}", lambda m: stash(_script(m.group(1), _SUBSCRIPT, m.group(0))), s)
    s = re.sub(r"\^(\w)", lambda m: stash(_SUPERSCRIPT.get(m.group(1), m.group(0))), s)
    s = re.sub(r"_(\w)", lambda m: stash(_SUBSCRIPT.get(m.group(1), m.group(0))), s)

    if _CONVERTER is not None:
        try:
            s = _CONVERTER.latex_to_text(s)
        except Exception:  # pragma: no cover - defensive
            pass

    return re.sub(f"{_MARK}(\\d+){_MARK}", lambda m: scripts[int(m.group(1))], s).strip()


def _script(content: str, table: dict[str, str], fallback: str) -> str:
    out = []
    for char in content:
        mapped = table.get(char)
        if mapped is None:
            return fallback  # leave the whole group raw if any char can't be mapped
        out.append(mapped)
    return "".join(out)
