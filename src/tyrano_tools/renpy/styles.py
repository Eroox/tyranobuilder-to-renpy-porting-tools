from __future__ import annotations

from dataclasses import dataclass

from tyrano_tools.renpy.paths import escape_string, normalize_font_face


@dataclass
class FontStyleState:
    size: int | None = None
    color: str | None = None
    face: str | None = None
    bold: bool | None = None
    italic: bool | None = None

    def copy(self) -> "FontStyleState":
        return FontStyleState(
            size=self.size,
            color=self.color,
            face=self.face,
            bold=self.bold,
            italic=self.italic,
        )

    def is_empty(self) -> bool:
        return all(
            value is None for value in (self.size, self.color, self.face, self.bold, self.italic)
        )


def normalize_tyrano_color(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    if stripped == "default":
        return None
    if stripped.startswith("0x"):
        return f"#{stripped[2:]}"
    if stripped.startswith("#"):
        return stripped
    return value


def build_say_args(font_style: FontStyleState | None) -> str:
    if font_style is None or font_style.is_empty():
        return ""
    parts: list[str] = []
    if font_style.face:
        parts.append(f'what_font="{escape_string(font_style.face)}"')
    if font_style.size is not None:
        parts.append(f"what_size={font_style.size}")
    if font_style.color:
        parts.append(f'what_color="{font_style.color}"')
    if font_style.bold is not None:
        parts.append(f"what_bold={str(font_style.bold)}")
    if font_style.italic is not None:
        parts.append(f"what_italic={str(font_style.italic)}")
    if not parts:
        return ""
    return f" ({', '.join(parts)})"


def apply_font_attributes(attrs: dict[str, str], font_state: FontStyleState) -> list[str]:
    referenced_faces: list[str] = []
    if "size" in attrs:
        size = parse_wait_value(attrs.get("size"))
        font_state.size = None if attrs.get("size", "").strip().lower() == "default" else size
    if "color" in attrs:
        font_state.color = normalize_tyrano_color(attrs.get("color"))
    if "face" in attrs:
        raw_face = attrs.get("face")
        normalized_face = normalize_font_face(raw_face)
        font_state.face = normalized_face
        if raw_face and normalized_face:
            referenced_faces.append(raw_face)
    if "bold" in attrs:
        raw_bold = attrs.get("bold", "").strip().lower()
        font_state.bold = None if raw_bold == "default" else raw_bold == "true"
    if "italic" in attrs:
        raw_italic = attrs.get("italic", "").strip().lower()
        font_state.italic = None if raw_italic == "default" else raw_italic == "true"
    return referenced_faces


def clear_font_state(font_state: FontStyleState) -> None:
    font_state.size = None
    font_state.color = None
    font_state.face = None
    font_state.bold = None
    font_state.italic = None


def parse_wait_value(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(float(stripped))
    except ValueError:
        return None
