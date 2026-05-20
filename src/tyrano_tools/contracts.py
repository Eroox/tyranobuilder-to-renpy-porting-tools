"""Shared typed data contracts for conversion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypeAlias


@dataclass
class TextToken:
    kind: str
    value: Optional[str] = None


@dataclass
class DialogueBlock:
    speaker: str
    tokens: list[TextToken]


@dataclass
class ActionBlock:
    line: str


@dataclass
class FlowBlock:
    tag: str
    attrs: dict[str, str]


@dataclass
class ChoiceOption:
    kind: str
    label: str
    attrs: dict[str, str]


@dataclass
class ChoiceBlock:
    options: list[ChoiceOption]


@dataclass
class EngineDetailBlock:
    lines: list[str]


ScreenplayBlock: TypeAlias = (
    DialogueBlock | ActionBlock | FlowBlock | ChoiceBlock | EngineDetailBlock
)


@dataclass
class Scene:
    heading: str
    blocks: list[ScreenplayBlock]


@dataclass
class Chapter:
    title: str
    scenes: list[Scene]
