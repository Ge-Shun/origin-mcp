from __future__ import annotations

import re

ORIGIN_ESCAPE_MARKERS = ("\\+(", "\\-(", "\\=(")

SUPERSCRIPT_CHARS = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "⁺": "+",
    "⁻": "-",
    "⁼": "=",
    "⁽": "(",
    "⁾": ")",
    "ⁿ": "n",
    "ⁱ": "i",
}

SUBSCRIPT_CHARS = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "₊": "+",
    "₋": "-",
    "₌": "=",
    "₍": "(",
    "₎": ")",
    "ₐ": "a",
    "ₑ": "e",
    "ₕ": "h",
    "ᵢ": "i",
    "ⱼ": "j",
    "ₖ": "k",
    "ₗ": "l",
    "ₘ": "m",
    "ₙ": "n",
    "ₒ": "o",
    "ₚ": "p",
    "ᵣ": "r",
    "ₛ": "s",
    "ₜ": "t",
    "ᵤ": "u",
    "ᵥ": "v",
    "ₓ": "x",
}

SUPERSCRIPT_PATTERN = re.compile("[" + re.escape("".join(SUPERSCRIPT_CHARS)) + "]+")
SUBSCRIPT_PATTERN = re.compile("[" + re.escape("".join(SUBSCRIPT_CHARS)) + "]+")
HTML_SUB_PATTERN = re.compile(r"<sub>(.*?)</sub>", re.IGNORECASE | re.DOTALL)
HTML_SUP_PATTERN = re.compile(r"<sup>(.*?)</sup>", re.IGNORECASE | re.DOTALL)
BRACED_SUB_PATTERN = re.compile(r"_\{([^{}]+)\}")
BRACED_SUP_PATTERN = re.compile(r"\^\{([^{}]+)\}")
NUMERIC_SUB_PATTERN = re.compile(r"_(?!\{)([+-]?\d+(?:\.\d+)?)")
NUMERIC_SUP_PATTERN = re.compile(r"\^(?!\{)([+-]?\d+(?:\.\d+)?)")
SINGLE_LETTER_SUB_PATTERN = re.compile(r"_(?!\{)([A-Za-z])(?![A-Za-z0-9_])")


def origin_rich_text(text: str) -> str:
    """Convert common subscript/superscript notation to Origin escape sequences."""

    if any(marker in text for marker in ORIGIN_ESCAPE_MARKERS):
        return normalize_label_text(text)

    formatted = normalize_label_text(text)
    formatted = HTML_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = HTML_SUP_PATTERN.sub(lambda match: _origin_super(match.group(1)), formatted)
    formatted = BRACED_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = BRACED_SUP_PATTERN.sub(lambda match: _origin_super(match.group(1)), formatted)
    formatted = SINGLE_LETTER_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = NUMERIC_SUB_PATTERN.sub(lambda match: _origin_sub(match.group(1)), formatted)
    formatted = NUMERIC_SUP_PATTERN.sub(lambda match: _origin_super(match.group(1)), formatted)
    formatted = SUBSCRIPT_PATTERN.sub(
        lambda match: _origin_sub(_translate(match.group(0), SUBSCRIPT_CHARS)),
        formatted,
    )
    formatted = SUPERSCRIPT_PATTERN.sub(
        lambda match: _origin_super(_translate(match.group(0), SUPERSCRIPT_CHARS)),
        formatted,
    )
    return formatted


def normalize_label_text(text: str) -> str:
    return text.replace("\r", " ").replace("\n", " ")


def _translate(value: str, mapping: dict[str, str]) -> str:
    return "".join(mapping.get(char, char) for char in value)


def _origin_sub(value: str) -> str:
    return f"\\-({_escape_group(value)})"


def _origin_super(value: str) -> str:
    return f"\\+({_escape_group(value)})"


def _escape_group(value: str) -> str:
    return normalize_label_text(value).replace(")", r"\)")
