"""Convert TyranoBuilder scenario flow into Ren'Py script outputs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, TypeAlias

from tyrano_tools.ks.io import read_ks_lines
from tyrano_tools.ks.tags import parse_tyrano_tag_line
from tyrano_tools.renpy.paths import (
    escape_string,
    normalize_identifier,
)
from tyrano_tools.renpy.styles import FontStyleState, build_say_args, parse_wait_value
from tyrano_tools.scenario.output import (
    StartupPlan,
    build_output_name_map,
    preferred_renpy_movie_path,
)
from tyrano_tools.scenario.shared import (
    AudioEvent,
    CharacterHideEvent,
    CharacterShowEvent,
    ConditionalEvent,
    DialogueEvent,
    JumpEvent,
    LabelEvent,
    MessageClearEvent,
    ParsedLine,
    ParseState,
    SceneEvent,
    UnsupportedEvent,
    WarningRecord,
    add_warning,
    append_line,
    build_custom_effects_file,
    build_label_name,
    build_transition_clause,
    consume_block_comment_line,
    finalize_script_block,
    handle_common_audio_or_message_tag,
    handle_common_flow_tag,
    handle_common_visual_tag,
    handle_label_definition,
    handle_script_block_line,
    handle_script_block_start,
    handle_text_block_line,
    handle_text_block_toggle,
    normalize_label_reference,
    parse_bool,
    partition_events,
    render_quake_event,
    render_script_event,
    render_wait_event,
)
from tyrano_tools.scenario.shared import (
    Event as BaseEvent,
)
from tyrano_tools.scenario.shared import (
    build_characters_file as build_shared_characters_file,
)
from tyrano_tools.scenario.shared import (
    build_images_file as build_shared_images_file,
)
from tyrano_tools.scenario.shared import (
    render_warning_report as render_shared_warning_report,
)
from tyrano_tools.scenario.traversal import (
    discover_reachable_files,
    is_system_storage,
    resolve_entry_file,
    resolve_scenario_dir,
    resolve_storage_path,
)
from tyrano_tools.version import add_version_argument

__all__ = (
    "DialogueEvent",
    "JumpEvent",
    "LabelEvent",
    "MovieEvent",
    "ParsedFile",
    "build_entry_label",
    "determine_startup_plan",
    "parse_project_file",
    "render_parsed_file",
)

SUPPORTED_TAGS = {
    "tb_start_text",
    "_tb_end_text",
    "bg",
    "chara_show",
    "chara_mod",
    "chara_hide",
    "chara_hide_all",
    "playbgm",
    "stopbgm",
    "playse",
    "quake",
    "font",
    "resetfont",
    "cm",
    "ct",
    "er",
    "wait",
    "jump",
    "call",
    "return",
    "if",
    "elsif",
    "else",
    "endif",
    "button",
    "clickable",
    "showload",
    "movie",
    "s",
}
SKIPPED_SYSTEM_TAGS = {"_tb_system_call"}


@dataclass
class ButtonEvent(ParsedLine):
    target_storage: Optional[str]
    target_label: Optional[str]
    graphic: Optional[str]
    hover_graphic: Optional[str]
    role: Optional[str]
    name: Optional[str]
    x: Optional[int]
    y: Optional[int]
    width: Optional[int]
    height: Optional[int]
    expression: Optional[str]
    is_clickable_area: bool = False


@dataclass
class ShowLoadEvent(ParsedLine):
    pass


@dataclass
class MovieEvent(ParsedLine):
    storage: Optional[str]
    skip: bool
    volume: Optional[int]
    raw_line: str


@dataclass
class StopEvent(ParsedLine):
    pass


Event: TypeAlias = BaseEvent | ButtonEvent | ShowLoadEvent | MovieEvent | StopEvent


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
class CharacterLayoutState:
    left: Optional[int] = None
    top: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    reflect: bool = False
    vertical_mode: str = "bottom"


@dataclass
class RenderState:
    indent_level: int
    index: int = 0
    screen_counter: int = 1
    character_layouts: dict[str, CharacterLayoutState] = field(default_factory=dict)


@dataclass
class RenderContext:
    parsed_file: ParsedFile
    events: Sequence[Event]
    lines: List[str]
    all_files: dict[Path, ParsedFile]
    output_name_by_source: dict[Path, str]
    screen_definitions: List[str]
    current_label_token: str
    promoted_movie_source: Optional[tuple[Path, int]]


def build_entry_label(source_path: Path) -> str:
    return f"{normalize_identifier(source_path.stem, prefix='scene')}__entry"


def remap_ui_storage(storage: str) -> str:
    return str(Path("images") / "ui" / Path(storage)).replace("\\", "/")


def merge_character_layout(
    attrs: dict[str, str],
    previous_state: Optional[CharacterLayoutState],
) -> Optional[CharacterLayoutState]:
    has_layout_attrs = any(key in attrs for key in {"left", "top", "width", "height", "reflect"})
    if not has_layout_attrs and previous_state is None:
        return None

    next_state = CharacterLayoutState()
    if previous_state is not None:
        next_state = CharacterLayoutState(
            left=previous_state.left,
            top=previous_state.top,
            width=previous_state.width,
            height=previous_state.height,
            reflect=previous_state.reflect,
            vertical_mode=previous_state.vertical_mode,
        )

    if "left" in attrs:
        next_state.left = parse_wait_value(attrs.get("left"))
    if "top" in attrs:
        next_state.top = parse_wait_value(attrs.get("top"))
        next_state.vertical_mode = "top"
    elif previous_state is None:
        next_state.vertical_mode = "bottom"
        next_state.top = None
    if "width" in attrs:
        next_state.width = parse_wait_value(attrs.get("width"))
    if "height" in attrs:
        next_state.height = parse_wait_value(attrs.get("height"))
    if "reflect" in attrs:
        next_state.reflect = parse_bool(attrs.get("reflect"), default=False)

    return next_state


def emit_character_show_statement(
    lines: List[str],
    indent_level: int,
    character_tag: str,
    variant_name: str,
    layout_state: Optional[CharacterLayoutState],
) -> None:
    if layout_state is None:
        append_line(lines, indent_level, f"show {character_tag} {variant_name}")
        return

    append_line(lines, indent_level, f"show {character_tag} {variant_name}:")

    if layout_state.reflect and layout_state.width is not None and layout_state.left is not None:
        append_line(lines, indent_level + 1, f"xpos {layout_state.left + layout_state.width}")
        append_line(lines, indent_level + 1, "xanchor 1.0")
        append_line(lines, indent_level + 1, "xzoom -1")
    else:
        if layout_state.left is not None:
            append_line(lines, indent_level + 1, f"xpos {layout_state.left}")
            append_line(lines, indent_level + 1, "xanchor 0.0")
        if layout_state.reflect:
            append_line(lines, indent_level + 1, "xzoom -1")

    if layout_state.vertical_mode == "top" and layout_state.top is not None:
        append_line(lines, indent_level + 1, f"ypos {layout_state.top}")
        append_line(lines, indent_level + 1, "yanchor 0.0")
    else:
        append_line(lines, indent_level + 1, "yalign 1.0")

    if layout_state.width is not None:
        append_line(lines, indent_level + 1, f"xsize {layout_state.width}")
    if layout_state.height is not None:
        append_line(lines, indent_level + 1, f"ysize {layout_state.height}")


def handle_system_or_unsupported_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    storage: Optional[str],
) -> bool:
    if tag_name in SKIPPED_SYSTEM_TAGS or is_system_storage(storage):
        add_warning(
            parsed_file,
            line_number,
            "skipped_system_reference",
            f"Skipped system reference during conversion: tag=`{tag_name}`, storage=`{storage}`.",
        )
        return True

    if tag_name not in SUPPORTED_TAGS:
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
            "unsupported_tag",
            f"Tag `{tag_name}` is not in the current converter v2 support set.",
        )
        return True

    return False


def handle_visual_tag(
    parsed_file: ParsedFile,
    line_number: int,
    tag_name: str,
    attrs: dict[str, str],
    storage: Optional[str],
) -> bool:
    return handle_common_visual_tag(
        parsed_file,
        line_number,
        tag_name,
        attrs,
        storage=storage,
        ignored_attr_keys={
            "name",
            "storage",
            "cond",
            "time",
            "wait",
            "width",
            "height",
            "left",
            "top",
            "reflect",
            "cross",
            "pos_mode",
        },
        warn_on_bg_missing=False,
    )


def handle_audio_or_message_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
    storage: Optional[str],
    font_style: FontStyleState,
) -> bool:
    return handle_common_audio_or_message_tag(
        parsed_file,
        line_number,
        stripped,
        tag_name,
        attrs,
        font_style,
        storage=storage,
    )


def handle_timing_or_jump_tag(
    parsed_file: ParsedFile,
    line_number: int,
    tag_name: str,
    attrs: dict[str, str],
    storage: Optional[str],
) -> bool:
    return handle_common_flow_tag(
        parsed_file,
        line_number,
        tag_name,
        attrs,
        storage=storage,
    )


def handle_button_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
    storage: Optional[str],
) -> bool:
    if tag_name != "button":
        return False

    if parse_bool(attrs.get("fix"), default=False):
        add_warning(
            parsed_file,
            line_number,
            "unsupported_fixed_button",
            (
                "Skipped Tyrano [button] with fix=true during phase 1 UI conversion; "
                "persistent overlay buttons still need a separate Ren'Py screen model."
            ),
        )
        parsed_file.events.append(
            UnsupportedEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                tag_name=tag_name,
                raw_line=stripped,
            )
        )
        return True

    role = attrs.get("role")
    if role:
        add_warning(
            parsed_file,
            line_number,
            "button_role_review",
            (
                f"Tyrano [button] role=`{role}` is not mapped yet; falling back to "
                "storage/target routing when possible."
            ),
        )
    expression = attrs.get("exp")
    if expression:
        add_warning(
            parsed_file,
            line_number,
            "button_expression_review",
            (
                "Tyrano [button] exp=... is not executed by the current Ren'Py "
                "converter and should be reviewed manually."
            ),
        )
    parsed_file.events.append(
        ButtonEvent(
            source_path=parsed_file.source_path,
            line_number=line_number,
            target_storage=storage,
            target_label=attrs.get("target"),
            graphic=attrs.get("graphic"),
            hover_graphic=attrs.get("enterimg"),
            role=role,
            name=attrs.get("name"),
            x=parse_wait_value(attrs.get("x")),
            y=parse_wait_value(attrs.get("y")),
            width=parse_wait_value(attrs.get("width")),
            height=parse_wait_value(attrs.get("height")),
            expression=expression,
        )
    )
    return True


def handle_clickable_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
    storage: Optional[str],
) -> bool:
    if tag_name != "clickable":
        return False

    expression = attrs.get("exp")
    if expression:
        add_warning(
            parsed_file,
            line_number,
            "button_expression_review",
            (
                "Tyrano [clickable] exp=... is not executed by the current Ren'Py "
                "converter and should be reviewed manually."
            ),
        )
    # `_clickable_img` is a TyranoBuilder-only attribute that points at an
    # optional preview image. When it is empty (the common case), the hotspot
    # is rendered as a transparent Null displayable in render_button_screen.
    clickable_graphic = attrs.get("_clickable_img") or None
    parsed_file.events.append(
        ButtonEvent(
            source_path=parsed_file.source_path,
            line_number=line_number,
            target_storage=storage,
            target_label=attrs.get("target"),
            graphic=clickable_graphic,
            hover_graphic=None,
            role=None,
            name=attrs.get("name"),
            x=parse_wait_value(attrs.get("x")),
            y=parse_wait_value(attrs.get("y")),
            width=parse_wait_value(attrs.get("width")),
            height=parse_wait_value(attrs.get("height")),
            expression=expression,
            is_clickable_area=True,
        )
    )
    return True


def handle_movie_or_stop_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
) -> bool:
    if tag_name == "showload":
        parsed_file.events.append(
            ShowLoadEvent(source_path=parsed_file.source_path, line_number=line_number)
        )
        return True

    if tag_name == "movie":
        movie_storage = attrs.get("storage")
        if movie_storage and preferred_renpy_movie_path(movie_storage).endswith(".webm"):
            add_warning(
                parsed_file,
                line_number,
                "movie_conversion_needed",
                (
                    "Movie tag was mapped to a Ren'Py `.webm` target for better "
                    "desktop compatibility. Convert the original Tyrano `.mp4`/`.m4v` "
                    "file with `prepare_movies_for_renpy.py` before testing playback."
                ),
            )
        if not parse_bool(attrs.get("skip"), default=False):
            add_warning(
                parsed_file,
                line_number,
                "movie_skip_semantics_changed",
                (
                    "Tyrano `[movie]` defaults to non-skippable playback, but the "
                    "current Ren'Py cutscene mapping may still allow player interruption."
                ),
            )
        volume = parse_wait_value(attrs.get("volume"))
        if volume is not None and volume != 100:
            add_warning(
                parsed_file,
                line_number,
                "movie_volume_not_preserved",
                (
                    f"Movie volume `{volume}` is not preserved by the current Ren'Py "
                    "cutscene mapping and should be reviewed manually."
                ),
            )
        parsed_file.events.append(
            MovieEvent(
                source_path=parsed_file.source_path,
                line_number=line_number,
                storage=movie_storage,
                skip=parse_bool(attrs.get("skip"), default=False),
                volume=volume,
                raw_line=stripped,
            )
        )
        return True

    if tag_name == "s":
        parsed_file.events.append(
            StopEvent(source_path=parsed_file.source_path, line_number=line_number)
        )
        return True

    return False


def handle_flow_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
    storage: Optional[str],
) -> bool:
    return (
        handle_timing_or_jump_tag(parsed_file, line_number, tag_name, attrs, storage)
        or handle_button_tag(parsed_file, line_number, stripped, tag_name, attrs, storage)
        or handle_clickable_tag(parsed_file, line_number, stripped, tag_name, attrs, storage)
        or handle_movie_or_stop_tag(parsed_file, line_number, stripped, tag_name, attrs)
    )


def handle_tag_line(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
    state: ParseState,
) -> bool:
    if handle_text_block_toggle(tag_name, state):
        return True
    if handle_script_block_start(parsed_file, line_number, tag_name, state):
        return True

    storage = attrs.get("storage")
    if handle_system_or_unsupported_tag(
        parsed_file,
        line_number,
        stripped,
        tag_name,
        storage,
    ):
        return True

    cond = attrs.get("cond")
    if cond:
        add_warning(
            parsed_file,
            line_number,
            "manual_condition_review",
            f"Tag `{tag_name}` uses cond=... and should be reviewed after conversion.",
        )

    return (
        handle_visual_tag(parsed_file, line_number, tag_name, attrs, storage)
        or handle_audio_or_message_tag(
            parsed_file,
            line_number,
            stripped,
            tag_name,
            attrs,
            storage,
            state.current_font_style,
        )
        or handle_flow_tag(parsed_file, line_number, stripped, tag_name, attrs, storage)
    )


def parse_project_file(
    source_path: Path,
    output_name: str,
    base_warnings: Sequence[WarningRecord],
) -> ParsedFile:
    parsed_file = ParsedFile(
        source_path=source_path,
        entry_label=build_entry_label(source_path),
        output_name=output_name,
        warnings=list(base_warnings),
    )
    state = ParseState()

    for line_number, raw_line in enumerate(read_ks_lines(source_path), start=1):
        stripped = raw_line.strip()

        if handle_script_block_line(parsed_file, line_number, stripped, state):
            continue
        if consume_block_comment_line(stripped, state):
            continue
        if not stripped or stripped.startswith(";"):
            continue

        if handle_label_definition(parsed_file, source_path, line_number, stripped, state):
            continue

        tag_info = parse_tyrano_tag_line(stripped)
        if tag_info:
            tag_name, attrs = tag_info

            if handle_tag_line(parsed_file, line_number, stripped, tag_name, attrs, state):
                continue

        if handle_text_block_line(
            parsed_file,
            state,
            raw_line,
            stripped,
            line_number,
            warn_on_unknown_inline_tags=False,
        ):
            continue

    finalize_script_block(parsed_file, state)
    return parsed_file


def humanize_button_label(event: ButtonEvent) -> str:
    if event.target_label:
        raw = event.target_label.lstrip("*").strip()
        if raw:
            return raw.replace("_", " ")
    if event.graphic:
        raw = Path(event.graphic).stem
        raw = raw.lstrip("0123456789_")
        if raw:
            return raw.replace("_", " ")
    return "Continue"


def build_button_screen_name(parsed_file: ParsedFile, label_token: str, cluster_index: int) -> str:
    return (
        f"tyrano_buttons_{normalize_identifier(parsed_file.source_path.stem, prefix='scene')}"
        f"_{label_token}_{cluster_index}"
    )


def build_button_result_token(button_event: ButtonEvent, index: int) -> str:
    if button_event.name:
        return normalize_identifier(button_event.name, prefix=f"button_{index}")
    if button_event.target_label:
        return normalize_identifier(button_event.target_label, prefix=f"button_{index}")
    if button_event.graphic:
        return normalize_identifier(Path(button_event.graphic).stem, prefix=f"button_{index}")
    return f"button_{index}"


def button_events_need_visual_screen(button_events: Sequence[ButtonEvent]) -> bool:
    return any(
        button_event.graphic
        or button_event.hover_graphic
        or button_event.is_clickable_area
        or button_event.x is not None
        or button_event.y is not None
        or button_event.width is not None
        or button_event.height is not None
        for button_event in button_events
    )


def render_button_image_displayable(button_event: ButtonEvent, storage: str) -> str:
    remapped_storage = escape_string(remap_ui_storage(storage))
    if button_event.width is not None and button_event.height is not None:
        return (
            f'Transform("{remapped_storage}", '
            f'xysize=({button_event.width}, {button_event.height}), fit="fill")'
        )
    return f'"{remapped_storage}"'


def render_clickable_area_displayable(button_event: ButtonEvent) -> str:
    """Render an invisible hotspot displayable for a [clickable] tag."""
    width = button_event.width if button_event.width is not None else 0
    height = button_event.height if button_event.height is not None else 0
    return f"Null({width}, {height})"


def get_label_events(parsed_file: ParsedFile, label_name: Optional[str]) -> Optional[List[Event]]:
    if not label_name:
        return None
    _, sections = partition_events(parsed_file.events)
    normalized_label = normalize_label_reference(label_name)
    for label_event, label_events in sections:
        if normalize_label_reference(label_event.label_name) == normalized_label:
            return label_events
    return None


def button_uses_load_menu(
    parsed_file: ParsedFile,
    button_event: ButtonEvent,
    all_files: dict[Path, ParsedFile],
) -> bool:
    target_file = parsed_file
    if button_event.target_storage:
        target_path = resolve_storage_path(parsed_file.source_path, button_event.target_storage)
        if target_path and target_path in all_files:
            target_file = all_files[target_path]
    label_events = get_label_events(target_file, button_event.target_label)
    if not label_events:
        return False
    return any(isinstance(event, ShowLoadEvent) for event in label_events)


def render_button_screen(
    screen_name: str,
    button_events: Sequence[ButtonEvent],
    button_actions: Sequence[str],
) -> List[str]:
    lines = [f"screen {screen_name}():", "    modal True", "    zorder 100"]
    use_fixed = any(
        button_event.x is not None or button_event.y is not None for button_event in button_events
    )
    if not use_fixed:
        lines.extend(
            ["", "    vbox:", "        xalign 0.5", "        yalign 0.5", "        spacing 24"]
        )

    for index, button_event in enumerate(button_events):
        indent_level = 1 if use_fixed else 2
        if button_event.graphic:
            append_line(lines, indent_level, "imagebutton:")
            idle_displayable = render_button_image_displayable(
                button_event,
                button_event.graphic,
            )
            append_line(
                lines,
                indent_level + 1,
                f"idle {idle_displayable}",
            )
            hover_displayable = render_button_image_displayable(
                button_event,
                button_event.hover_graphic or button_event.graphic,
            )
            append_line(
                lines,
                indent_level + 1,
                f"hover {hover_displayable}",
            )
            if button_event.x is not None:
                append_line(lines, indent_level + 1, f"xpos {button_event.x}")
            if button_event.y is not None:
                append_line(lines, indent_level + 1, f"ypos {button_event.y}")
            if button_event.width is not None and button_event.height is None:
                append_line(lines, indent_level + 1, f"xsize {button_event.width}")
            if button_event.height is not None and button_event.width is None:
                append_line(lines, indent_level + 1, f"ysize {button_event.height}")
            append_line(lines, indent_level + 1, "focus_mask True")
            append_line(lines, indent_level + 1, f"action {button_actions[index]}")
            continue

        if button_event.is_clickable_area:
            displayable = render_clickable_area_displayable(button_event)
            append_line(lines, indent_level, "imagebutton:")
            append_line(lines, indent_level + 1, f"idle {displayable}")
            append_line(lines, indent_level + 1, f"hover {displayable}")
            if button_event.x is not None:
                append_line(lines, indent_level + 1, f"xpos {button_event.x}")
            if button_event.y is not None:
                append_line(lines, indent_level + 1, f"ypos {button_event.y}")
            append_line(lines, indent_level + 1, f"action {button_actions[index]}")
            continue

        option_label = humanize_button_label(button_event)
        append_line(lines, indent_level, f'textbutton "{escape_string(option_label)}":')
        if button_event.x is not None:
            append_line(lines, indent_level + 1, f"xpos {button_event.x}")
        if button_event.y is not None:
            append_line(lines, indent_level + 1, f"ypos {button_event.y}")
        if button_event.width is not None:
            append_line(lines, indent_level + 1, f"xsize {button_event.width}")
        if button_event.height is not None:
            append_line(lines, indent_level + 1, f"ysize {button_event.height}")
        append_line(lines, indent_level + 1, f"action {button_actions[index]}")

    return lines


def has_terminal_flow(events: Sequence[Event]) -> bool:
    if not events:
        return False
    for last_event in reversed(events):
        if isinstance(last_event, StopEvent):
            continue
        if isinstance(last_event, JumpEvent):
            return not last_event.is_call
        if isinstance(last_event, ButtonEvent):
            return True
        return False
    return False


def resolve_target_label(
    parsed_file: ParsedFile,
    event_storage: Optional[str],
    event_target_label: Optional[str],
    all_files: dict[Path, ParsedFile],
    output_name_by_source: dict[Path, str],
) -> str:
    target_file_token = Path(parsed_file.output_name).stem
    normalized_target_label = (
        normalize_label_reference(event_target_label) if event_target_label else None
    )
    local_target_exists = normalized_target_label in parsed_file.label_names

    if event_storage:
        target_path = resolve_storage_path(parsed_file.source_path, event_storage)
        if target_path and target_path in all_files:
            target_file_token = Path(output_name_by_source[target_path]).stem
        else:
            add_warning(
                parsed_file,
                0,
                "unresolved_external_flow",
                (
                    "Referenced jump/call target may require another converted file or "
                    "manual routing: storage=`"
                    f"{event_storage}`, target=`{event_target_label or ''}`."
                ),
            )
            target_file_token = normalize_identifier(Path(event_storage).stem, prefix="scene")
    elif local_target_exists:
        target_file_token = Path(parsed_file.output_name).stem

    if event_target_label:
        if local_target_exists:
            target_file_token = Path(parsed_file.output_name).stem
        return f"{target_file_token}__{normalize_label_reference(event_target_label)}"

    return f"{target_file_token}__entry"


def emit_button_menu(
    parsed_file: ParsedFile,
    events: Sequence[Event],
    start_index: int,
    lines: List[str],
    indent_level: int,
    all_files: dict[Path, ParsedFile],
    output_name_by_source: dict[Path, str],
) -> tuple[int, int]:
    button_events: List[ButtonEvent] = []
    index = start_index
    while index < len(events) and isinstance(events[index], ButtonEvent):
        button_event = events[index]
        if isinstance(button_event, ButtonEvent):
            button_events.append(button_event)
        index += 1

    append_line(lines, indent_level, "menu:")
    for button_event in button_events:
        option_label = humanize_button_label(button_event)
        target_label = resolve_target_label(
            parsed_file,
            button_event.target_storage,
            button_event.target_label,
            all_files,
            output_name_by_source,
        )
        append_line(lines, indent_level + 1, f'"{escape_string(option_label)}":')
        append_line(lines, indent_level + 2, f"jump {target_label}")

    if index < len(events) and isinstance(events[index], StopEvent):
        index += 1

    return indent_level, index


def emit_button_screen(
    parsed_file: ParsedFile,
    events: Sequence[Event],
    start_index: int,
    lines: List[str],
    indent_level: int,
    all_files: dict[Path, ParsedFile],
    output_name_by_source: dict[Path, str],
    screen_definitions: List[str],
    current_label_token: str,
    screen_counter: int,
) -> tuple[int, int, int]:
    button_events: List[ButtonEvent] = []
    index = start_index
    while index < len(events) and isinstance(events[index], ButtonEvent):
        button_event = events[index]
        if isinstance(button_event, ButtonEvent):
            button_events.append(button_event)
        index += 1

    if not button_events_need_visual_screen(button_events):
        next_indent, next_index = emit_button_menu(
            parsed_file,
            events,
            start_index,
            lines,
            indent_level,
            all_files,
            output_name_by_source,
        )
        return next_indent, next_index, screen_counter

    button_results: List[tuple[str, str]] = []
    button_actions: List[str] = []
    for button_index, button_event in enumerate(button_events):
        if button_uses_load_menu(parsed_file, button_event, all_files):
            button_actions.append('ShowMenu("load")')
            continue
        result_token = build_button_result_token(button_event, button_index)
        button_actions.append(f'Return("{result_token}")')
        target_label = resolve_target_label(
            parsed_file,
            button_event.target_storage,
            button_event.target_label,
            all_files,
            output_name_by_source,
        )
        button_results.append((result_token, target_label))

    screen_name = build_button_screen_name(parsed_file, current_label_token, screen_counter)
    screen_counter += 1
    screen_definitions.append(
        "\n".join(render_button_screen(screen_name, button_events, button_actions))
    )
    append_line(lines, indent_level, "window hide")
    append_line(lines, indent_level, f"call screen {screen_name}")

    for button_index, (result_token, target_label) in enumerate(button_results):
        keyword = "if" if button_index == 0 else "elif"
        append_line(lines, indent_level, f'{keyword} _return == "{result_token}":')
        append_line(lines, indent_level + 1, f"jump {target_label}")

    if button_results:
        append_line(lines, indent_level, "else:")
        append_line(lines, indent_level + 1, "return")

    if index < len(events) and isinstance(events[index], StopEvent):
        index += 1

    return indent_level, index, screen_counter


def handle_button_or_stop_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    if isinstance(event, ButtonEvent):
        state.indent_level, state.index, state.screen_counter = emit_button_screen(
            context.parsed_file,
            context.events,
            state.index,
            context.lines,
            state.indent_level,
            context.all_files,
            context.output_name_by_source,
            context.screen_definitions,
            context.current_label_token,
            state.screen_counter,
        )
        return True

    if not isinstance(event, StopEvent):
        return False

    previous = context.events[state.index - 1] if state.index > 0 else None
    if (
        isinstance(previous, ButtonEvent)
        or isinstance(previous, ShowLoadEvent)
        or (isinstance(previous, JumpEvent) and not previous.is_call)
        or (
            state.index + 1 < len(context.events)
            and isinstance(context.events[state.index + 1], ButtonEvent)
        )
    ):
        state.index += 1
        return True

    append_line(
        context.lines,
        state.indent_level,
        "# TODO TYRANO: review standalone [s] stop behavior",
    )
    state.index += 1
    return True


def handle_dialogue_or_scene_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    if isinstance(event, DialogueEvent):
        say_args = build_say_args(event.font_style)
        if event.speaker == "NARRATION":
            if say_args:
                append_line(
                    context.lines,
                    state.indent_level,
                    f'narrator "{escape_string(event.text)}"{say_args}',
                )
            else:
                append_line(context.lines, state.indent_level, f'"{escape_string(event.text)}"')
        else:
            speaker_id = normalize_identifier(event.speaker, prefix="speaker")
            append_line(
                context.lines,
                state.indent_level,
                f'{speaker_id} "{escape_string(event.text)}"{say_args}',
            )
        state.index += 1
        return True

    if isinstance(event, MessageClearEvent):
        append_line(context.lines, state.indent_level, "window hide")
        state.index += 1
        return True

    if not isinstance(event, SceneEvent):
        return False

    bg_name = context.parsed_file.backgrounds.get(event.storage)
    if bg_name:
        append_line(context.lines, state.indent_level, f"scene bg_asset {bg_name}")
    else:
        append_line(
            context.lines,
            state.indent_level,
            f'# TODO TYRANO: missing background mapping for "{escape_string(event.storage)}"',
        )
    transition_clause = build_transition_clause(
        event.transition_method,
        event.transition_time_ms,
    )
    if transition_clause:
        append_line(context.lines, state.indent_level, f"with {transition_clause}")
    state.index += 1
    return True


def handle_character_or_audio_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    if isinstance(event, CharacterShowEvent):
        character_tag = normalize_identifier(event.character_name, prefix="char")
        variant_name = context.parsed_file.character_images.get(
            (event.character_name, event.storage)
        )
        if variant_name:
            layout_state = merge_character_layout(
                event.attributes,
                state.character_layouts.get(character_tag),
            )
            if layout_state is not None:
                state.character_layouts[character_tag] = layout_state
            emit_character_show_statement(
                context.lines,
                state.indent_level,
                character_tag,
                variant_name,
                layout_state,
            )
        else:
            append_line(
                context.lines,
                state.indent_level,
                f'# TODO TYRANO: missing character mapping for "{escape_string(event.storage)}"',
            )
        transition_clause = build_transition_clause(None, event.transition_time_ms)
        if transition_clause:
            append_line(context.lines, state.indent_level, f"with {transition_clause}")
        state.index += 1
        return True

    if isinstance(event, CharacterHideEvent):
        if event.character_name:
            character_tag = normalize_identifier(event.character_name, prefix="char")
            append_line(context.lines, state.indent_level, f"hide {character_tag}")
        else:
            state.character_layouts.clear()
            append_line(context.lines, state.indent_level, "scene black")
            add_warning(
                context.parsed_file,
                event.line_number,
                "approximate_staging",
                "Approximated [chara_hide_all] as `scene black`; review final staging intent.",
            )
        transition_clause = build_transition_clause(None, event.transition_time_ms)
        if transition_clause:
            append_line(context.lines, state.indent_level, f"with {transition_clause}")
        state.index += 1
        return True

    if not isinstance(event, AudioEvent):
        return False

    if event.command == "stop":
        append_line(context.lines, state.indent_level, f"stop {event.channel}")
    elif event.storage:
        append_line(
            context.lines,
            state.indent_level,
            f'{event.command} {event.channel} "{escape_string(event.storage)}"',
        )
    else:
        append_line(
            context.lines,
            state.indent_level,
            f"# TODO TYRANO: missing audio storage for {event.channel}",
        )
    state.index += 1
    return True


def handle_movie_or_showload_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    if isinstance(event, ShowLoadEvent):
        append_line(
            context.lines,
            state.indent_level,
            (
                "# TODO TYRANO: [showload] should be triggered from a screen/menu "
                "action so Ren'Py enters the load menu context correctly"
            ),
        )
        state.index += 1
        return True

    if not isinstance(event, MovieEvent):
        return False

    if context.promoted_movie_source == (event.source_path, event.line_number):
        append_line(
            context.lines,
            state.indent_level,
            f"# TYRANO MOVIE MOVED: {event.raw_line}",
        )
        append_line(
            context.lines,
            state.indent_level,
            (
                "# This movie was promoted to `label splashscreen` by the startup "
                "heuristic and is not played again here."
            ),
        )
    elif event.storage:
        append_line(
            context.lines,
            state.indent_level,
            f'$ renpy.movie_cutscene("{escape_string(preferred_renpy_movie_path(event.storage))}")',
        )
    else:
        append_line(
            context.lines,
            state.indent_level,
            f"# TODO TYRANO: missing movie storage for {event.raw_line}",
        )
    state.index += 1
    return True


def handle_quake_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    if not render_quake_event(context.parsed_file, event, context.lines, state.indent_level):
        return False
    state.index += 1
    return True


def handle_wait_or_jump_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    if render_wait_event(
        context.parsed_file,
        event,
        context.lines,
        state.indent_level,
        warn_on_missing_time=False,
    ):
        state.index += 1
        return True

    if not isinstance(event, JumpEvent):
        return False

    if event.target_storage is None and event.target_label is None and not event.is_call:
        append_line(context.lines, state.indent_level, "return")
        state.index += 1
        return True
    target_label = resolve_target_label(
        context.parsed_file,
        event.target_storage,
        event.target_label,
        context.all_files,
        context.output_name_by_source,
    )
    append_line(
        context.lines,
        state.indent_level,
        f"{'call' if event.is_call else 'jump'} {target_label}",
    )
    state.index += 1
    return True


def handle_conditional_or_unsupported_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    if isinstance(event, ConditionalEvent):
        if event.kind == "if":
            append_line(context.lines, state.indent_level, f"if {event.expression or 'True'}:")
            state.indent_level += 1
        elif event.kind == "elsif":
            state.indent_level = max(state.indent_level - 1, 1)
            append_line(context.lines, state.indent_level, f"elif {event.expression or 'True'}:")
            state.indent_level += 1
        elif event.kind == "else":
            state.indent_level = max(state.indent_level - 1, 1)
            append_line(context.lines, state.indent_level, "else:")
            state.indent_level += 1
        elif event.kind == "endif":
            state.indent_level = max(state.indent_level - 1, 1)
        state.index += 1
        return True

    if not isinstance(event, UnsupportedEvent):
        return False

    append_line(
        context.lines,
        state.indent_level,
        f"# TODO TYRANO: unsupported tag: {event.raw_line}",
    )
    state.index += 1
    return True


def handle_flow_control_event(
    context: RenderContext,
    state: RenderState,
    event: Event,
) -> bool:
    return (
        handle_quake_event(context, state, event)
        or handle_wait_or_jump_event(context, state, event)
        or handle_conditional_or_unsupported_event(context, state, event)
    )


def emit_event_sequence(
    parsed_file: ParsedFile,
    events: Sequence[Event],
    lines: List[str],
    starting_indent: int,
    all_files: dict[Path, ParsedFile],
    output_name_by_source: dict[Path, str],
    screen_definitions: List[str],
    current_label_token: str,
    screen_counter: int,
    promoted_movie_source: Optional[tuple[Path, int]],
) -> tuple[int, int]:
    context = RenderContext(
        parsed_file=parsed_file,
        events=events,
        lines=lines,
        all_files=all_files,
        output_name_by_source=output_name_by_source,
        screen_definitions=screen_definitions,
        current_label_token=current_label_token,
        promoted_movie_source=promoted_movie_source,
    )
    state = RenderState(indent_level=starting_indent, screen_counter=screen_counter)

    while state.index < len(events):
        event = events[state.index]
        if handle_button_or_stop_event(context, state, event):
            continue
        if handle_movie_or_showload_event(context, state, event):
            continue
        if handle_dialogue_or_scene_event(context, state, event):
            continue
        if handle_character_or_audio_event(context, state, event):
            continue
        if render_script_event(context.parsed_file, event, context.lines, state.indent_level):
            state.index += 1
            continue
        if handle_flow_control_event(context, state, event):
            continue
        state.index += 1

    return state.indent_level, state.screen_counter


def render_parsed_file(
    parsed_file: ParsedFile,
    all_files: dict[Path, ParsedFile],
    output_name_by_source: dict[Path, str],
    startup_plan: Optional[StartupPlan] = None,
) -> str:
    body_lines: List[str] = []
    screen_definitions: List[str] = []
    screen_counter = 1
    prelude, sections = partition_events(parsed_file.events)
    first_label_name = (
        build_label_name(parsed_file.source_path, sections[0][0].label_name) if sections else None
    )

    body_lines.append(f"label {parsed_file.entry_label}:")
    indent_level, screen_counter = emit_event_sequence(
        parsed_file,
        prelude,
        body_lines,
        1,
        all_files,
        output_name_by_source,
        screen_definitions,
        "entry",
        screen_counter,
        startup_plan.promoted_movie_source if startup_plan else None,
    )
    if first_label_name and not has_terminal_flow(prelude):
        append_line(body_lines, indent_level, f"jump {first_label_name}")
    elif not prelude:
        append_line(body_lines, indent_level, "return")
    body_lines.append("")

    for section_index, (label_event, label_events) in enumerate(sections):
        body_lines.append(
            f"label {build_label_name(parsed_file.source_path, label_event.label_name)}:"
        )
        indent_level, screen_counter = emit_event_sequence(
            parsed_file,
            label_events,
            body_lines,
            1,
            all_files,
            output_name_by_source,
            screen_definitions,
            normalize_label_reference(label_event.label_name),
            screen_counter,
            startup_plan.promoted_movie_source if startup_plan else None,
        )
        if indent_level == 1 and not has_terminal_flow(label_events):
            if section_index + 1 < len(sections):
                next_label_event = sections[section_index + 1][0]
                append_line(
                    body_lines,
                    indent_level,
                    "jump "
                    f"{build_label_name(parsed_file.source_path, next_label_event.label_name)}",
                )
            else:
                append_line(body_lines, indent_level, "return")
        body_lines.append("")

    lines = [f"# Generated from {parsed_file.source_path.name}", ""]
    if screen_definitions:
        lines.extend(screen_definitions)
        lines.append("")
    lines.extend(body_lines)
    return "\n".join(lines).rstrip() + "\n"


def build_characters_file(parsed_files: Sequence[ParsedFile]) -> str:
    return build_shared_characters_file(
        parsed_files,
        "# No named speakers detected in the reachable scenario set.",
    )


def build_images_file(parsed_files: Sequence[ParsedFile]) -> str:
    return build_shared_images_file(
        parsed_files,
        "# No image declarations detected in the reachable scenario set.",
    )


def render_route_map(parsed_files: Sequence[ParsedFile], entry_file: Path) -> str:
    lines = [
        "# Route Map",
        "",
        f"Entry file: `{entry_file.name}`",
        "",
        "## Reachable Scenario Files",
        "",
    ]
    for parsed_file in parsed_files:
        prefix = "-"
        if parsed_file.source_path == entry_file:
            prefix = "- (entry)"
        lines.append(
            f"{prefix} `{parsed_file.source_path.name}` -> `story/{parsed_file.output_name}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_warning_report(parsed_files: Sequence[ParsedFile]) -> str:
    return render_shared_warning_report(
        parsed_files,
        "- No warnings recorded for the current v2 conversion run.",
    )


def determine_boot_target_file(
    entry_file: ParsedFile,
    parsed_file_map: Dict[Path, ParsedFile],
) -> Optional[ParsedFile]:
    for event in entry_file.events:
        if not isinstance(event, JumpEvent) or event.is_call or not event.target_storage:
            continue
        target_path = resolve_storage_path(entry_file.source_path, event.target_storage)
        if target_path is None:
            continue
        target_file = parsed_file_map.get(target_path.resolve())
        if target_file is not None:
            return target_file
    return None


def extract_movie_storage(raw_line: str) -> Optional[str]:
    marker = 'storage="'
    start_index = raw_line.find(marker)
    if start_index == -1:
        return None
    value_start = start_index + len(marker)
    value_end = raw_line.find('"', value_start)
    if value_end == -1:
        return None
    storage = raw_line[value_start:value_end].strip()
    return storage or None


def determine_splashscreen_candidate(
    title_file: ParsedFile,
    parsed_files: Sequence[ParsedFile],
) -> Optional[tuple[str, str, int]]:
    prelude, sections = partition_events(title_file.events)
    if not sections:
        return None

    movie_events = [event for event in prelude if isinstance(event, MovieEvent)]
    non_movie_events = [event for event in prelude if not isinstance(event, MovieEvent)]
    if len(movie_events) != 1 or non_movie_events:
        return None

    first_label_event = sections[0][0]
    resume_label = build_label_name(title_file.source_path, first_label_event.label_name)
    normalized_resume_target = first_label_event.label_name.lstrip("*").strip().lower()
    later_title_returns = 0

    for parsed_file in parsed_files:
        if parsed_file.source_path == title_file.source_path:
            continue
        for event in parsed_file.events:
            if not isinstance(event, JumpEvent) or event.is_call or not event.target_storage:
                continue
            target_path = resolve_storage_path(parsed_file.source_path, event.target_storage)
            if target_path is None or target_path.resolve() != title_file.source_path:
                continue
            if (
                event.target_label
                and event.target_label.lstrip("*").strip().lower() == normalized_resume_target
            ):
                later_title_returns += 1

    if later_title_returns == 0:
        return None

    movie_storage = extract_movie_storage(movie_events[0].raw_line)
    if not movie_storage:
        return None

    movie_path = preferred_renpy_movie_path(movie_storage)
    return movie_path, resume_label, movie_events[0].line_number


def determine_startup_plan(
    parsed_files: Sequence[ParsedFile],
    entry_file: ParsedFile,
) -> StartupPlan:
    default_plan = StartupPlan(
        start_label=entry_file.entry_label,
        skip_builtin_main_menu=True,
        splashscreen_movie=None,
        confidence="translated",
        note=(
            "Skips Ren'Py's built-in main menu so the converted Tyrano flow becomes "
            "the primary startup path."
        ),
    )

    parsed_file_map = {
        parsed_file.source_path.resolve(): parsed_file for parsed_file in parsed_files
    }
    boot_target = determine_boot_target_file(entry_file, parsed_file_map)
    if boot_target is None:
        return default_plan

    splashscreen_candidate = determine_splashscreen_candidate(boot_target, parsed_files)
    if splashscreen_candidate is None:
        return default_plan

    movie_path, resume_label, movie_line_number = splashscreen_candidate
    startup_warnings: List[WarningRecord] = []
    if movie_path.endswith(".webm"):
        startup_warnings.append(
            WarningRecord(
                source_path=boot_target.source_path,
                line_number=movie_line_number,
                category="startup_movie_conversion_needed",
                message=(
                    "Startup movie was mapped to a Ren'Py `.webm` target for better "
                    "desktop compatibility. Convert the original Tyrano `.mp4`/`.m4v` "
                    "file with `prepare_movies_for_renpy.py` before testing splashscreen "
                    "playback."
                ),
            )
        )
    return StartupPlan(
        start_label=resume_label,
        skip_builtin_main_menu=True,
        splashscreen_movie=movie_path,
        confidence="heuristic",
        note=(
            "Detected a non-interactive startup movie before the converted title "
            "screen and moved it to `splashscreen`, prefers the Ren'Py target "
            f"`{movie_path}`, and then resumes at `{resume_label}` so the intro "
            "does not replay on return-to-title."
        ),
        warnings=startup_warnings,
        promoted_movie_source=(boot_target.source_path, movie_line_number),
    )


def build_start_file(startup_plan: StartupPlan) -> str:
    lines = ["# Generated startup handoff", ""]
    if startup_plan.skip_builtin_main_menu:
        lines.extend(
            [
                "label main_menu:",
                "    return",
                "",
            ]
        )
    if startup_plan.splashscreen_movie:
        lines.extend(
            [
                "label splashscreen:",
                f'    $ renpy.movie_cutscene("{startup_plan.splashscreen_movie}")',
                "    return",
                "",
            ]
        )
    lines.extend(
        [
            "label start:",
            f"    jump {startup_plan.start_label}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(
    parsed_files: Sequence[ParsedFile],
    entry_file: ParsedFile,
    output_dir: Path,
) -> List[Path]:
    game_dir = output_dir / "game"
    story_dir = game_dir / "story"
    story_dir.mkdir(parents=True, exist_ok=True)
    all_files = {parsed_file.source_path: parsed_file for parsed_file in parsed_files}
    output_name_by_source = {
        parsed_file.source_path: parsed_file.output_name for parsed_file in parsed_files
    }
    written_paths: List[Path] = []
    startup_plan = determine_startup_plan(parsed_files, entry_file)
    if startup_plan.warnings:
        entry_file.warnings.extend(startup_plan.warnings)

    start_path = game_dir / "script.rpy"
    start_path.write_text(build_start_file(startup_plan), encoding="utf-8")
    written_paths.append(start_path)

    characters_path = game_dir / "characters.rpy"
    characters_path.write_text(build_characters_file(parsed_files), encoding="utf-8")
    written_paths.append(characters_path)

    images_path = game_dir / "images.rpy"
    images_path.write_text(build_images_file(parsed_files), encoding="utf-8")
    written_paths.append(images_path)

    custom_effects_path = game_dir / "custom_effects.rpy"
    custom_effects_path.write_text(build_custom_effects_file(parsed_files), encoding="utf-8")
    written_paths.append(custom_effects_path)

    for parsed_file in parsed_files:
        output_path = story_dir / parsed_file.output_name
        output_path.write_text(
            render_parsed_file(parsed_file, all_files, output_name_by_source, startup_plan),
            encoding="utf-8",
        )
        written_paths.append(output_path)

    route_map_path = game_dir / "route_map.md"
    route_map_path.write_text(
        render_route_map(parsed_files, entry_file.source_path), encoding="utf-8"
    )
    written_paths.append(route_map_path)

    warning_report_path = game_dir / "conversion_warnings.md"
    warning_report_path.write_text(render_warning_report(parsed_files), encoding="utf-8")
    written_paths.append(warning_report_path)

    return written_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert TyranoBuilder scenario flow into script-only Ren'Py outputs. "
            "Does NOT produce options.rpy, gui.rpy, screens.rpy, or keymap.rpy. "
            "For a complete Ren'Py project scaffold use tyranobuilder_to_renpy_project.py."
        ),
    )
    add_version_argument(parser)
    parser.add_argument(
        "input",
        type=Path,
        help="TyranoBuilder project root, data/scenario directory, or entry .ks file",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Directory to write generated Ren'Py project files (default: out)",
    )
    parser.add_argument(
        "--entry",
        default=None,
        help=(
            "Override the default entry .ks file inside the scenario "
            "directory. Use this when TyranoBuilder's 'Preview from here' "
            "feature has replaced first.ks with a _preview.ks jump (for "
            "example pass --entry title_screen.ks)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario_dir = resolve_scenario_dir(args.input)
    entry_file = resolve_entry_file(scenario_dir, args.entry).resolve()
    reachable_files, traversal_warnings = discover_reachable_files(scenario_dir, entry_file)
    output_name_map = build_output_name_map(reachable_files)

    warning_map: dict[Path, List[WarningRecord]] = {}
    for warning in traversal_warnings:
        warning_map.setdefault(warning.source_path.resolve(), []).append(warning)

    parsed_files = [
        parse_project_file(path, output_name_map[path], warning_map.get(path.resolve(), []))
        for path in reachable_files
    ]
    parsed_file_map = {
        parsed_file.source_path.resolve(): parsed_file for parsed_file in parsed_files
    }
    entry_parsed_file = parsed_file_map[entry_file]
    written_paths = write_outputs(parsed_files, entry_parsed_file, args.out_dir)

    print("Wrote outputs:")
    for written_path in written_paths:
        print(f"- {written_path}")


if __name__ == "__main__":
    main()
