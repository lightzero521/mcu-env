"""Terminal prompt prefix formatting."""

from __future__ import annotations

PROMPT_PREFIX = "mcuenv"
PROMPT_STYLE = "bold green"

_ATTR_CODES = {
    "bold": "1",
    "dim": "2",
    "italic": "3",
    "underline": "4",
}

_COLOR_CODES = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "brightblack": "90",
    "brightred": "91",
    "brightgreen": "92",
    "brightyellow": "93",
    "brightblue": "94",
    "brightmagenta": "95",
    "brightcyan": "96",
    "brightwhite": "97",
}


def _ansi_codes(style: str) -> str:
    codes: list[str] = []
    for token in style.lower().split():
        if token in _ATTR_CODES:
            codes.append(_ATTR_CODES[token])
        elif token in _COLOR_CODES:
            codes.append(_COLOR_CODES[token])
    return ";".join(codes)


def format_prompt_segment() -> str:
    label = f"({PROMPT_PREFIX})"
    codes = _ansi_codes(PROMPT_STYLE)
    return f"\x1b[{codes}m{label}\x1b[0m "


def format_prompt_bash() -> str:
    label = f"({PROMPT_PREFIX})"
    codes = _ansi_codes(PROMPT_STYLE)
    return rf"\[\e[{codes}m\]{label}\[\e[0m\] "
