"""Shared text-token helpers for KS-derived renderers."""

from __future__ import annotations

from tyrano_tools.contracts import TextToken


def append_terminal_line_break(tokens: list[TextToken]) -> None:
    if tokens and tokens[-1].kind not in {"line_break", "panel_break"}:
        tokens.append(TextToken(kind="line_break"))


def trim_trailing_empty_lines(lines: list[str]) -> list[str]:
    trimmed_lines = list(lines)
    while trimmed_lines and trimmed_lines[-1] == "":
        trimmed_lines.pop()
    return [line.rstrip() for line in trimmed_lines]
