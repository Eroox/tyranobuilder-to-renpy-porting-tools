from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TypeVar

from tyrano_tools.renpy.paths import (
    escape_string,
    normalize_font_face,
    normalize_identifier,
    remap_audio_storage,
    remap_background_storage,
    remap_character_storage,
)
from tyrano_tools.renpy.styles import FontStyleState, clear_font_state, parse_wait_value
from tyrano_tools.renpy.styles import apply_font_attributes as apply_shared_font_attributes

INLINE_TOKEN_PATTERN = re.compile(r"(\[p\]|\[l\]|\[r\])")
INLINE_TAG_PATTERN = re.compile(r"\[(?!p\]|l\]|r\])(\w+)(?:\s+[^\]]*)?\]")
WINDOW_OPEN_PATTERN = re.compile(
    r"^window\.open\(\s*(['\"])(?P<url>https?://[^'\"]+)\1\s*\)\s*;?\s*$"
)


@dataclass
class WarningRecord:
    source_path: Path
    line_number: int
    category: str
    message: str


@dataclass
class ParsedLine:
    source_path: Path
    line_number: int


@dataclass
class LabelEvent(ParsedLine):
    label_name: str


@dataclass
class DialogueEvent(ParsedLine):
    speaker: str
    text: str
    font_style: Optional[FontStyleState] = None


@dataclass
class SceneEvent(ParsedLine):
    storage: str
    transition_time_ms: int = 0
    transition_method: Optional[str] = None


@dataclass
class CharacterShowEvent(ParsedLine):
    character_name: str
    storage: str
    attributes: dict[str, str]
    transition_time_ms: int = 0


@dataclass
class CharacterHideEvent(ParsedLine):
    character_name: Optional[str]
    transition_time_ms: int = 0


@dataclass
class AudioEvent(ParsedLine):
    channel: str
    storage: Optional[str]
    command: str


@dataclass
class MessageClearEvent(ParsedLine):
    kind: str


@dataclass
class QuakeEvent(ParsedLine):
    time_ms: int
    count: int
    hmax: int
    vmax: int
    wait: bool


@dataclass
class WaitEvent(ParsedLine):
    milliseconds: Optional[int]


@dataclass
class JumpEvent(ParsedLine):
    target_storage: Optional[str]
    target_label: Optional[str]
    is_call: bool


@dataclass
class ConditionalEvent(ParsedLine):
    kind: str
    expression: Optional[str] = None


@dataclass
class OpenUrlEvent(ParsedLine):
    url: str


@dataclass
class ScriptBlockEvent(ParsedLine):
    lines: List[str]


@dataclass
class UnsupportedEvent(ParsedLine):
    tag_name: str
    raw_line: str


Event = (
    LabelEvent
    | DialogueEvent
    | SceneEvent
    | CharacterShowEvent
    | CharacterHideEvent
    | AudioEvent
    | MessageClearEvent
    | QuakeEvent
    | WaitEvent
    | JumpEvent
    | ConditionalEvent
    | OpenUrlEvent
    | ScriptBlockEvent
    | UnsupportedEvent
)


@dataclass
class ParsedFile:
    source_path: Path
    entry_label: str
    output_name: str
    events: List[Event] = field(default_factory=list)
    label_names: set[str] = field(default_factory=set)
    speakers: set[str] = field(default_factory=set)
    backgrounds: Dict[str, str] = field(default_factory=dict)
    character_images: Dict[tuple[str, str], str] = field(default_factory=dict)
    font_faces: set[str] = field(default_factory=set)
    warnings: List[WarningRecord] = field(default_factory=list)


@dataclass
class ParseState:
    in_text_block: bool = False
    in_block_comment: bool = False
    in_script_block: bool = False
    script_block_start_line: int = 0
    current_script_lines: List[str] = field(default_factory=list)
    current_speaker: str = "NARRATION"
    current_font_style: FontStyleState = field(default_factory=FontStyleState)


def normalize_label_reference(label_name: str) -> str:
    return normalize_identifier(label_name.lstrip("*").strip(), prefix="label")


def build_label_name(source_path: Path, label_name: str) -> str:
    file_token = normalize_identifier(source_path.stem, prefix="scene")
    label_token = normalize_label_reference(label_name)
    return f"{file_token}__{label_token}"


def add_warning(
    parsed_file: Any,
    line_number: int,
    category: str,
    message: str,
) -> None:
    parsed_file.warnings.append(
        WarningRecord(
            source_path=parsed_file.source_path,
            line_number=line_number,
            category=category,
            message=message,
        )
    )


def apply_font_attributes(
    parsed_file: Any,
    line_number: int,
    font_state: FontStyleState,
    attrs: dict[str, str],
) -> None:
    referenced_faces = apply_shared_font_attributes(attrs, font_state)
    for raw_face in referenced_faces:
        normalized_face = normalize_font_face(raw_face)
        if raw_face not in parsed_file.font_faces and normalized_face is not None:
            parsed_file.font_faces.add(raw_face)
            add_warning(
                parsed_file,
                line_number,
                "font_face_mapping_needed",
                (
                    f"Font face `{raw_face}` was referenced by Tyrano [font]; assumed "
                    f"Ren'Py font file `{normalized_face}`. Verify that file exists or "
                    "adjust the generated font path."
                ),
            )


def split_text_fragments(text: str) -> List[tuple[str, str]]:
    fragments: List[tuple[str, str]] = []
    for part in INLINE_TOKEN_PATTERN.split(text):
        if not part:
            continue
        if part == "[p]":
            fragments.append(("page_break", ""))
        elif part == "[l]":
            fragments.append(("pause_click", ""))
        elif part == "[r]":
            fragments.append(("line_break", ""))
        else:
            fragments.append(("text", part))
    return fragments


def emit_text_events(
    parsed_file: Any,
    speaker: str,
    text: str,
    line_number: int,
    font_state: Optional[FontStyleState],
    *,
    warn_on_unknown_inline_tags: bool,
) -> None:
    fragments = split_text_fragments(text)
    current_parts: List[str] = []

    def flush() -> None:
        nonlocal current_parts
        rendered = "".join(current_parts).strip()
        if rendered:
            parsed_file.events.append(
                DialogueEvent(
                    source_path=parsed_file.source_path,
                    line_number=line_number,
                    speaker=speaker,
                    text=rendered,
                    font_style=font_state.copy()
                    if font_state and not font_state.is_empty()
                    else None,
                )
            )
        current_parts = []

    if warn_on_unknown_inline_tags:
        inline_tags = sorted({match.group(1) for match in INLINE_TAG_PATTERN.finditer(text)})
        if inline_tags:
            add_warning(
                parsed_file,
                line_number,
                "unsupported_inline_tag",
                f"Inline text tags preserved as raw text: {', '.join(inline_tags)}",
            )

    for kind, value in fragments:
        if kind == "text":
            current_parts.append(value)
        elif kind == "line_break":
            current_parts.append("\n")
        elif kind == "pause_click":
            current_parts.append("{w}")
        elif kind == "page_break":
            flush()

    flush()


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() == "true"


# Maps a Tyrano `method=` value to a Ren'Py transition expression.
# Each entry is `(template, accepts_time_param)`. When the second element is
# True, `{t}` in the template is substituted with the duration in seconds.
# When False, the template is a fixed-duration named transition and the Tyrano
# `time=` value cannot be applied to it.
TRANSITION_METHOD_MAP: dict[str, tuple[str, bool]] = {
    # Plain fades (V450+ and V450- naming both fall through to Dissolve).
    "fadeIn": ("Dissolve({t})", True),
    "fadeOut": ("Dissolve({t})", True),
    "crossfade": ("Dissolve({t})", True),
    # Slide-style entries map to Ren'Py's built-in move-in transitions. Note
    # that the time parameter is dropped because the built-in transitions use
    # a fixed duration. Tyrano direction naming: "Left"/"Right" indicates the
    # edge the new image enters from, while "Up"/"Down" describe the movement
    # direction, so "Up" enters from the bottom and "Down" from the top.
    "slideInLeft": ("moveinleft", False),
    "slideInRight": ("moveinright", False),
    "slideInUp": ("moveinbottom", False),
    "slideInDown": ("moveintop", False),
    "fadeInLeft": ("moveinleft", False),
    "fadeInRight": ("moveinright", False),
    "fadeInUp": ("moveinbottom", False),
    "fadeInDown": ("moveintop", False),
    "fadeInLeftBig": ("moveinleft", False),
    "fadeInRightBig": ("moveinright", False),
    "fadeInUpBig": ("moveinbottom", False),
    "fadeInDownBig": ("moveintop", False),
    # Zoom-style entries approximate Tyrano's grow/shrink animation through
    # Ren'Py's pixellate transition.
    "zoomIn": ("Pixellate({t}, 5)", True),
    "zoomInUp": ("Pixellate({t}, 5)", True),
    "zoomInDown": ("Pixellate({t}, 5)", True),
    "zoomInLeft": ("Pixellate({t}, 5)", True),
    "zoomInRight": ("Pixellate({t}, 5)", True),
    "zoomInUpBig": ("Pixellate({t}, 5)", True),
    "zoomInDownBig": ("Pixellate({t}, 5)", True),
    "zoomInLeftBig": ("Pixellate({t}, 5)", True),
    "zoomInRightBig": ("Pixellate({t}, 5)", True),
    # Shake-style entries map to Ren'Py's built-in punch transitions (fixed
    # duration).
    "shake": ("vpunch", False),
    # Decorative effects fall through to Dissolve as a safe approximation.
    "rotateIn": ("Dissolve({t})", True),
    "rotateInUpLeft": ("Dissolve({t})", True),
    "rotateInUpRight": ("Dissolve({t})", True),
    "rotateInDownLeft": ("Dissolve({t})", True),
    "rotateInDownRight": ("Dissolve({t})", True),
    "bounceIn": ("Dissolve({t})", True),
    "bounceInUp": ("Dissolve({t})", True),
    "bounceInDown": ("Dissolve({t})", True),
    "bounceInLeft": ("Dissolve({t})", True),
    "bounceInRight": ("Dissolve({t})", True),
    "lightSpeedIn": ("Dissolve({t})", True),
    "vanishIn": ("Dissolve({t})", True),
    "puffIn": ("Dissolve({t})", True),
    "rollIn": ("Dissolve({t})", True),
    # V450- legacy method names.
    "explode": ("Dissolve({t})", True),
    "slide": ("moveinright", False),
    "blind": ("Dissolve({t})", True),
    "bounce": ("Dissolve({t})", True),
    "clip": ("Dissolve({t})", True),
    "drop": ("Dissolve({t})", True),
    "fold": ("Dissolve({t})", True),
    "puff": ("Dissolve({t})", True),
    "scale": ("Dissolve({t})", True),
    "size": ("Dissolve({t})", True),
}


def build_transition_clause(method: Optional[str], time_ms: int) -> Optional[str]:
    """Return the Ren'Py expression for a `with` clause, or None to suppress.

    The Tyrano default method is `fadeIn`. When `time_ms` is zero (or
    negative) the transition is treated as an instant snap and no `with` clause
    is emitted, matching the runtime behavior of TyranoBuilder. Unknown method
    names fall back to `Dissolve({t})` so the conversion stays readable.
    """
    if time_ms <= 0:
        return None
    seconds = time_ms / 1000.0
    template, accepts_time = TRANSITION_METHOD_MAP.get(
        method or "fadeIn",
        ("Dissolve({t})", True),
    )
    if accepts_time:
        return template.format(t=f"{seconds:g}")
    return template


def build_quake_transition_name(axis: str, time_ms: int, count: int, amplitude: int) -> str:
    return f"tyrano_{axis}punch_{time_ms}_{count}_{amplitude}"


def classify_quake_axis(hmax: int, vmax: int) -> str:
    if hmax > 0 and vmax == 0:
        return "h"
    if vmax > 0 and hmax == 0:
        return "v"
    if hmax > 0 and vmax > 0:
        return "mixed"
    return "none"


def parse_quake_axes(attrs: dict[str, str]) -> tuple[int, int]:
    raw_hmax = parse_wait_value(attrs.get("hmax"))
    raw_vmax = parse_wait_value(attrs.get("vmax"))
    if raw_hmax is not None and raw_vmax is None:
        return raw_hmax, 0
    if raw_vmax is not None and raw_hmax is None:
        return 0, raw_vmax
    return raw_hmax or 0, raw_vmax or 10


def build_quake_transitions_file(
    parsed_files: Sequence[Any],
) -> str:
    presets: dict[tuple[str, int, int, int], None] = {}
    for parsed_file in parsed_files:
        for event in parsed_file.events:
            if not isinstance(event, QuakeEvent):
                continue
            axis = classify_quake_axis(event.hmax, event.vmax)
            if axis not in {"h", "v"}:
                continue
            amplitude = event.hmax if axis == "h" else event.vmax
            presets[(axis, event.time_ms, event.count, amplitude)] = None

    lines = ["# Generated quake transitions", ""]
    if not presets:
        lines.append("# No quake transitions were needed for this conversion run.")
        return "\n".join(lines).rstrip() + "\n"

    for axis, time_ms, count, amplitude in sorted(presets):
        transition_name = build_quake_transition_name(axis, time_ms, count, amplitude)
        offset_name = "xoffset" if axis == "h" else "yoffset"
        cycle_seconds = time_ms / 1000.0
        quarter = cycle_seconds / 4.0
        total = cycle_seconds * count
        lines.append(f"transform {transition_name}(old_widget=None, new_widget=None):")
        lines.append(f"    delay {total:g}")
        lines.append("    new_widget")
        lines.append("    events True")
        lines.append(f"    {offset_name} 0")
        for _ in range(count):
            lines.append(f"    linear {quarter:g} {offset_name} {amplitude}")
            lines.append(f"    linear {quarter:g} {offset_name} -{amplitude}")
            lines.append(f"    linear {quarter:g} {offset_name} {amplitude}")
            lines.append(f"    linear {quarter:g} {offset_name} 0")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_quake_event(
    parsed_file: Any,
    event: Any,
    lines: List[str],
    indent_level: int,
) -> bool:
    if not isinstance(event, QuakeEvent):
        return False

    axis = classify_quake_axis(event.hmax, event.vmax)
    if axis == "mixed":
        append_line(
            lines,
            indent_level,
            (
                "# TODO TYRANO: unsupported mixed-axis quake; review horizontal and "
                "vertical shake intent"
            ),
        )
        add_warning(
            parsed_file,
            event.line_number,
            "unsupported_quake_variant",
            f"Mixed-axis quake is not supported yet: hmax={event.hmax}, vmax={event.vmax}.",
        )
        return True
    if axis == "none":
        append_line(lines, indent_level, "# TODO TYRANO: quake had no effective shake axis")
        add_warning(
            parsed_file,
            event.line_number,
            "unsupported_quake_variant",
            "Quake tag had no effective horizontal or vertical amplitude.",
        )
        return True
    if not event.wait:
        add_warning(
            parsed_file,
            event.line_number,
            "nonblocking_quake_review",
            (
                "Converted quake as a blocking Ren'Py transition because wait=false "
                "is not modeled yet."
            ),
        )
    amplitude = event.hmax if axis == "h" else event.vmax
    append_line(
        lines,
        indent_level,
        f"with {build_quake_transition_name(axis, event.time_ms, event.count, amplitude)}",
    )
    return True


def render_wait_event(
    parsed_file: Any,
    event: Any,
    lines: List[str],
    indent_level: int,
    *,
    warn_on_missing_time: bool,
) -> bool:
    if not isinstance(event, WaitEvent):
        return False

    if event.milliseconds is None:
        append_line(lines, indent_level, "pause")
        if warn_on_missing_time:
            add_warning(
                parsed_file,
                event.line_number,
                "approximate_wait",
                "Converted [wait] without a numeric time to a plain `pause`.",
            )
    else:
        append_line(lines, indent_level, f"pause {event.milliseconds / 1000.0:g}")
    return True


def handle_script_block_start(
    parsed_file: Any,
    line_number: int,
    tag_name: str,
    state: ParseState,
) -> bool:
    if tag_name != "iscript":
        return False
    state.in_script_block = True
    state.script_block_start_line = line_number
    state.current_script_lines = []
    return True


def append_script_block_event(parsed_file: Any, line_number: int, lines: List[str]) -> None:
    if len(lines) == 1:
        url_match = WINDOW_OPEN_PATTERN.match(lines[0])
        if url_match:
            parsed_file.events.append(
                OpenUrlEvent(
                    source_path=parsed_file.source_path,
                    line_number=line_number,
                    url=url_match.group("url"),
                )
            )
            return

    parsed_file.events.append(
        ScriptBlockEvent(
            source_path=parsed_file.source_path,
            line_number=line_number,
            lines=list(lines),
        )
    )
    add_warning(
        parsed_file,
        line_number,
        "unsupported_script_block",
        "Tyrano [iscript] block was preserved as TODO comments for manual conversion.",
    )


def handle_script_block_line(
    parsed_file: Any,
    line_number: int,
    stripped: str,
    state: ParseState,
) -> bool:
    if not state.in_script_block:
        return False

    if stripped == "[endscript]" or stripped.startswith("@endscript"):
        append_script_block_event(
            parsed_file,
            state.script_block_start_line or line_number,
            state.current_script_lines,
        )
        state.in_script_block = False
        state.script_block_start_line = 0
        state.current_script_lines = []
        return True

    if stripped:
        state.current_script_lines.append(stripped)
    return True


def finalize_script_block(parsed_file: Any, state: ParseState) -> None:
    if not state.in_script_block:
        return

    append_script_block_event(
        parsed_file,
        state.script_block_start_line,
        state.current_script_lines,
    )
    add_warning(
        parsed_file,
        state.script_block_start_line,
        "unterminated_script_block",
        "Tyrano [iscript] block reached end of file before [endscript].",
    )
    state.in_script_block = False
    state.script_block_start_line = 0
    state.current_script_lines = []


def render_script_event(
    parsed_file: Any,
    event: Any,
    lines: List[str],
    indent_level: int,
) -> bool:
    if isinstance(event, OpenUrlEvent):
        append_line(lines, indent_level, f'$ renpy.open_url("{escape_string(event.url)}")')
        return True

    if not isinstance(event, ScriptBlockEvent):
        return False

    if event.lines:
        append_line(lines, indent_level, "# TODO TYRANO: unsupported [iscript] block:")
        for script_line in event.lines:
            append_line(lines, indent_level, f"#   {script_line}")
    else:
        append_line(lines, indent_level, "# TODO TYRANO: empty [iscript] block")
    return True


def consume_block_comment_line(stripped: str, state: ParseState) -> bool:
    if state.in_block_comment:
        if stripped == "*/":
            state.in_block_comment = False
        return True
    if stripped == "/*":
        state.in_block_comment = True
        return True
    return False


def handle_label_definition(
    parsed_file: Any,
    source_path: Path,
    line_number: int,
    stripped: str,
    state: ParseState,
) -> bool:
    if state.in_text_block or not stripped.startswith("*"):
        return False
    raw_label_name = stripped.lstrip("*").strip() or "label"
    parsed_file.label_names.add(normalize_label_reference(raw_label_name))
    parsed_file.events.append(
        LabelEvent(
            source_path=source_path,
            line_number=line_number,
            label_name=raw_label_name,
        )
    )
    state.current_speaker = "NARRATION"
    return True


def handle_text_block_toggle(tag_name: str, state: ParseState) -> bool:
    if tag_name == "tb_start_text":
        state.in_text_block = True
        state.current_speaker = "NARRATION"
        return True
    if tag_name == "_tb_end_text":
        state.in_text_block = False
        state.current_speaker = "NARRATION"
        return True
    return False


def handle_text_block_line(
    parsed_file: Any,
    state: ParseState,
    raw_line: str,
    stripped: str,
    line_number: int,
    *,
    warn_on_unknown_inline_tags: bool,
) -> bool:
    if not state.in_text_block:
        return False
    if stripped.startswith("#"):
        state.current_speaker = stripped.lstrip("#").strip() or "NARRATION"
        if state.current_speaker != "NARRATION":
            parsed_file.speakers.add(state.current_speaker)
        return True

    emit_text_events(
        parsed_file,
        state.current_speaker,
        raw_line,
        line_number,
        state.current_font_style,
        warn_on_unknown_inline_tags=warn_on_unknown_inline_tags,
    )
    if state.current_speaker != "NARRATION":
        parsed_file.speakers.add(state.current_speaker)
    return True


EventT = TypeVar("EventT")


def partition_events(
    events: Sequence[EventT],
) -> tuple[List[EventT], List[tuple[LabelEvent, List[EventT]]]]:
    prelude: List[EventT] = []
    sections: List[tuple[LabelEvent, List[EventT]]] = []
    current_label: Optional[LabelEvent] = None
    current_events: List[EventT] = []
    for event in events:
        if isinstance(event, LabelEvent):
            if current_label is None:
                if current_events:
                    prelude.extend(current_events)
            else:
                sections.append((current_label, current_events))
            current_label = event
            current_events = []
            continue
        current_events.append(event)
    if current_label is None:
        prelude.extend(current_events)
    else:
        sections.append((current_label, current_events))
    return prelude, sections


def append_line(lines: List[str], indent_level: int, content: str) -> None:
    lines.append(f"{'    ' * indent_level}{content}")


def build_characters_file(parsed_files: Sequence[Any], no_speakers_message: str) -> str:
    speakers = sorted(
        {speaker for parsed_file in parsed_files for speaker in parsed_file.speakers},
        key=str.lower,
    )
    lines = ["# Generated character definitions", ""]
    if not speakers:
        lines.append(no_speakers_message)
        return "\n".join(lines).rstrip() + "\n"

    for speaker in speakers:
        speaker_id = normalize_identifier(speaker, prefix="speaker")
        lines.append(f'define {speaker_id} = Character("{escape_string(speaker)}")')

    return "\n".join(lines).rstrip() + "\n"


def build_images_file(parsed_files: Sequence[Any], no_images_message: str) -> str:
    lines = ["# Generated image declarations", ""]
    seen_backgrounds: set[str] = set()
    seen_characters: set[tuple[str, str]] = set()

    for parsed_file in parsed_files:
        for storage, bg_name in sorted(
            parsed_file.backgrounds.items(), key=lambda item: item[0].lower()
        ):
            if storage in seen_backgrounds:
                continue
            seen_backgrounds.add(storage)
            lines.append(f'image bg_asset {bg_name} = "{escape_string(storage)}"')

        for (character_name, storage), variant_name in sorted(
            parsed_file.character_images.items(),
            key=lambda item: (item[0][0].lower(), item[0][1].lower()),
        ):
            character_tag = normalize_identifier(character_name, prefix="char")
            key = (character_tag, variant_name)
            if key in seen_characters:
                continue
            seen_characters.add(key)
            lines.append(f'image {character_tag} {variant_name} = "{escape_string(storage)}"')

    if len(lines) == 2:
        lines.append(no_images_message)

    return "\n".join(lines).rstrip() + "\n"


def render_warning_report(parsed_files: Sequence[Any], no_warnings_message: str) -> str:
    warnings = [warning for parsed_file in parsed_files for warning in parsed_file.warnings]
    lines = ["# Conversion Warnings", ""]

    if not warnings:
        lines.append(no_warnings_message)
        return "\n".join(lines).rstrip() + "\n"

    grouped: dict[str, List[WarningRecord]] = {}
    for warning in warnings:
        grouped.setdefault(warning.category, []).append(warning)

    for category in sorted(grouped):
        lines.append(f"## {category}")
        lines.append("")
        for warning in grouped[category]:
            lines.append(
                f"- `{warning.source_path.name}:{warning.line_number}` - {warning.message}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def handle_common_visual_tag(
    parsed_file: Any,
    line_number: int,
    tag_name: str,
    attrs: dict[str, str],
    *,
    storage: Optional[str],
    ignored_attr_keys: set[str],
    warn_on_bg_missing: bool,
) -> bool:
    if tag_name == "bg":
        if storage:
            remapped_storage = remap_background_storage(storage)
            bg_name = normalize_identifier(Path(storage).stem, prefix="bg")
            parsed_file.backgrounds[remapped_storage] = bg_name
            raw_time = parse_wait_value(attrs.get("time"))
            transition_time_ms = raw_time if raw_time is not None else 3000
            parsed_file.events.append(
                SceneEvent(
                    source_path=parsed_file.source_path,
                    line_number=line_number,
                    storage=remapped_storage,
                    transition_time_ms=transition_time_ms,
                    transition_method=attrs.get("method"),
                )
            )
        elif warn_on_bg_missing:
            add_warning(parsed_file, line_number, "missing_storage", "[bg] missing storage")
        return True

    if tag_name not in {"chara_show", "chara_mod", "chara_hide", "chara_hide_all"}:
        return False

    if tag_name in {"chara_show", "chara_mod"}:
        character_name = attrs.get("name") or Path(storage or "character").stem
        if not storage:
            add_warning(
                parsed_file,
                line_number,
                "missing_storage",
                f"[{tag_name}] missing storage",
            )
            return True
        remapped_storage = remap_character_storage(storage)
        variant_name = normalize_identifier(Path(storage).stem, prefix="variant")
        parsed_file.character_images[(character_name, remapped_storage)] = variant_name
        raw_time = parse_wait_value(attrs.get("time"))
        transition_time_ms = raw_time if raw_time is not None else 1000
        # [chara_mod] with cross=false is an instant swap regardless of the
        # nominal time value, so suppress the with clause for that case.
        if tag_name == "chara_mod" and not parse_bool(attrs.get("cross"), default=True):
            transition_time_ms = 0
        parsed_file.events.append(
            CharacterShowEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                character_name=character_name,
                storage=remapped_storage,
                attributes=attrs,
                transition_time_ms=transition_time_ms,
            )
        )
        ignored_attrs = sorted(attrs.keys() - ignored_attr_keys)
        if ignored_attrs:
            add_warning(
                parsed_file,
                line_number,
                "approximate_staging",
                (
                    f"[{tag_name}] ignores Tyrano-specific staging attrs for now: "
                    f"{', '.join(ignored_attrs)}"
                ),
            )
        return True

    if tag_name == "chara_hide":
        raw_time = parse_wait_value(attrs.get("time"))
        transition_time_ms = raw_time if raw_time is not None else 1000
        parsed_file.events.append(
            CharacterHideEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                character_name=attrs.get("name"),
                transition_time_ms=transition_time_ms,
            )
        )
        return True

    parsed_file.events.append(
        CharacterHideEvent(
            source_path=parsed_file.source_path,
            line_number=line_number,
            character_name=None,
        )
    )
    return True


def handle_common_audio_or_message_tag(
    parsed_file: Any,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
    font_state: FontStyleState,
    *,
    storage: Optional[str],
) -> bool:
    if tag_name == "playbgm":
        remapped_storage = remap_audio_storage(storage or "", "music") if storage else None
        parsed_file.events.append(
            AudioEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                channel="music",
                storage=remapped_storage,
                command="play",
            )
        )
        return True

    if tag_name == "stopbgm":
        parsed_file.events.append(
            AudioEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                channel="music",
                storage=None,
                command="stop",
            )
        )
        return True

    if tag_name == "playse":
        remapped_storage = remap_audio_storage(storage or "", "sound") if storage else None
        parsed_file.events.append(
            AudioEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                channel="sound",
                storage=remapped_storage,
                command="play",
            )
        )
        return True

    if tag_name == "font":
        apply_font_attributes(parsed_file, line_number, font_state, attrs)
        return True

    if tag_name == "resetfont":
        clear_font_state(font_state)
        return True

    if tag_name == "cm":
        clear_font_state(font_state)
        parsed_file.events.append(
            MessageClearEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                kind="cm",
            )
        )
        return True

    if tag_name in {"ct", "er"}:
        clear_font_state(font_state)
        parsed_file.events.append(
            UnsupportedEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                tag_name=tag_name,
                raw_line=stripped,
            )
        )
        add_warning(
            parsed_file,
            line_number,
            "message_control_review",
            (
                f"Tag `{tag_name}` resets Tyrano font state and still needs fuller "
                "message-layer conversion review."
            ),
        )
        return True

    return False


def handle_common_flow_tag(
    parsed_file: Any,
    line_number: int,
    tag_name: str,
    attrs: dict[str, str],
    *,
    storage: Optional[str],
) -> bool:
    if tag_name == "quake":
        time_ms = parse_wait_value(attrs.get("time")) or 300
        count = parse_wait_value(attrs.get("count")) or 5
        hmax, vmax = parse_quake_axes(attrs)
        parsed_file.events.append(
            QuakeEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                time_ms=time_ms,
                count=count,
                hmax=hmax,
                vmax=vmax,
                wait=parse_bool(attrs.get("wait"), default=True),
            )
        )
        return True

    if tag_name == "wait":
        parsed_file.events.append(
            WaitEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                milliseconds=parse_wait_value(attrs.get("time")),
            )
        )
        return True

    if tag_name in {"jump", "call"}:
        parsed_file.events.append(
            JumpEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                target_storage=storage,
                target_label=attrs.get("target"),
                is_call=tag_name == "call",
            )
        )
        return True

    if tag_name == "return":
        parsed_file.events.append(
            JumpEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                target_storage=None,
                target_label=None,
                is_call=False,
            )
        )
        return True

    if tag_name in {"if", "elsif", "else", "endif"}:
        parsed_file.events.append(
            ConditionalEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                kind=tag_name,
                expression=attrs.get("exp"),
            )
        )
        return True

    return False
