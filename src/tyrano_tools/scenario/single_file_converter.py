"""Convert TyranoScript KS files into a safe Ren'Py subset."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional, Sequence

from tyrano_tools.ks.io import read_ks_lines
from tyrano_tools.ks.tags import parse_tyrano_tag_line
from tyrano_tools.renpy.paths import (
    escape_string,
    normalize_identifier,
)
from tyrano_tools.renpy.styles import FontStyleState, build_say_args
from tyrano_tools.scenario.output import build_output_name_map
from tyrano_tools.scenario.shared import (
    AudioEvent,
    CharacterHideEvent,
    CharacterShowEvent,
    ConditionalEvent,
    DialogueEvent,
    Event,
    JumpEvent,
    LabelEvent,
    MessageClearEvent,
    ParsedFile,
    ParseState,
    SceneEvent,
    UnsupportedEvent,
    add_warning,
    append_line,
    build_label_name,
    build_quake_transitions_file,
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
    partition_events,
    render_quake_event,
    render_script_event,
    render_wait_event,
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
from tyrano_tools.version import add_version_argument

__all__ = (
    "DialogueEvent",
    "FontStyleState",
    "JumpEvent",
    "LabelEvent",
    "ParsedFile",
    "build_entry_label",
    "main",
    "parse_ks_file",
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
}


def build_entry_label(source_path: Path) -> str:
    return f"{normalize_identifier(source_path.stem, prefix='scene')}__start"


def expand_input_paths(inputs: Sequence[Path]) -> List[Path]:
    paths: List[Path] = []
    seen: set[Path] = set()

    for input_path in inputs:
        if not input_path.exists():
            raise FileNotFoundError(f"Input path not found: {input_path}")

        if input_path.is_dir():
            candidates = sorted(input_path.glob("*.ks"))
        else:
            candidates = [input_path]

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(candidate)

    if not paths:
        raise RuntimeError("No .ks files found in the provided input paths")

    return sorted(paths, key=lambda item: item.as_posix().lower())


def handle_unsupported_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
) -> bool:
    if tag_name in SUPPORTED_TAGS:
        return False
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
        f"Tag `{tag_name}` is not in the first safe conversion subset.",
    )
    return True


def handle_visual_tag(
    parsed_file: ParsedFile,
    line_number: int,
    tag_name: str,
    attrs: dict[str, str],
) -> bool:
    return handle_common_visual_tag(
        parsed_file,
        line_number,
        tag_name,
        attrs,
        storage=attrs.get("storage"),
        ignored_attr_keys={"name", "storage", "cond"},
        warn_on_bg_missing=True,
    )


def handle_audio_or_message_tag(
    parsed_file: ParsedFile,
    line_number: int,
    stripped: str,
    tag_name: str,
    attrs: dict[str, str],
    font_state: FontStyleState,
) -> bool:
    return handle_common_audio_or_message_tag(
        parsed_file,
        line_number,
        stripped,
        tag_name,
        attrs,
        font_state,
        storage=attrs.get("storage"),
    )


def handle_flow_tag(
    parsed_file: ParsedFile,
    line_number: int,
    tag_name: str,
    attrs: dict[str, str],
) -> bool:
    return handle_common_flow_tag(
        parsed_file,
        line_number,
        tag_name,
        attrs,
        storage=attrs.get("storage"),
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
    if handle_unsupported_tag(parsed_file, line_number, stripped, tag_name):
        return True

    if attrs.get("cond"):
        add_warning(
            parsed_file,
            line_number,
            "manual_condition_review",
            f"Tag `{tag_name}` uses cond=... and should be reviewed after conversion.",
        )

    return (
        handle_visual_tag(parsed_file, line_number, tag_name, attrs)
        or handle_audio_or_message_tag(
            parsed_file,
            line_number,
            stripped,
            tag_name,
            attrs,
            state.current_font_style,
        )
        or handle_flow_tag(parsed_file, line_number, tag_name, attrs)
    )


def parse_ks_file(source_path: Path, output_name: str) -> ParsedFile:
    parsed_file = ParsedFile(
        source_path=source_path,
        entry_label=build_entry_label(source_path),
        output_name=output_name,
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
            warn_on_unknown_inline_tags=True,
        ):
            continue
    finalize_script_block(parsed_file, state)
    return parsed_file


def handle_visual_event(
    parsed_file: ParsedFile,
    event: Event,
    lines: List[str],
    indent_level: int,
) -> Optional[int]:
    if isinstance(event, SceneEvent):
        bg_name = parsed_file.backgrounds.get(event.storage)
        if bg_name:
            append_line(lines, indent_level, f"scene bg_asset {bg_name}")
        else:
            append_line(
                lines,
                indent_level,
                f'# TODO TYRANO: missing background mapping for "{escape_string(event.storage)}"',
            )
        return indent_level

    if isinstance(event, CharacterShowEvent):
        character_tag = normalize_identifier(event.character_name, prefix="char")
        variant_name = parsed_file.character_images.get((event.character_name, event.storage))
        if variant_name:
            append_line(lines, indent_level, f"show {character_tag} {variant_name}")
        else:
            append_line(
                lines,
                indent_level,
                f'# TODO TYRANO: missing character mapping for "{escape_string(event.storage)}"',
            )
        return indent_level

    if not isinstance(event, CharacterHideEvent):
        return None

    if event.character_name:
        append_line(
            lines,
            indent_level,
            f"hide {normalize_identifier(event.character_name, prefix='char')}",
        )
    else:
        append_line(lines, indent_level, "scene black")
        add_warning(
            parsed_file,
            event.line_number,
            "approximate_staging",
            "Approximated [chara_hide_all] as `scene black`; review final staging intent.",
        )
    return indent_level


def handle_audio_or_message_event(
    event: Event,
    lines: List[str],
    indent_level: int,
) -> Optional[int]:
    if isinstance(event, AudioEvent):
        if event.command == "stop":
            append_line(lines, indent_level, f"stop {event.channel}")
        elif event.storage:
            append_line(
                lines,
                indent_level,
                f'{event.command} {event.channel} "{escape_string(event.storage)}"',
            )
        else:
            append_line(
                lines,
                indent_level,
                f"# TODO TYRANO: missing audio storage for {event.channel}",
            )
        return indent_level

    if isinstance(event, MessageClearEvent):
        append_line(lines, indent_level, "window hide")
        return indent_level

    return None


def handle_quake_or_wait_event(
    parsed_file: ParsedFile,
    event: Event,
    lines: List[str],
    indent_level: int,
) -> Optional[int]:
    if render_quake_event(parsed_file, event, lines, indent_level):
        return indent_level

    if render_wait_event(parsed_file, event, lines, indent_level, warn_on_missing_time=True):
        return indent_level

    return None


def resolve_local_storage_label(parsed_file: ParsedFile, event: JumpEvent) -> Optional[str]:
    if event.target_storage is None:
        return None
    storage_label_guess = normalize_identifier(Path(event.target_storage).stem, prefix="label")
    if storage_label_guess in parsed_file.label_names:
        return storage_label_guess
    return None


def resolve_target_file_token(
    parsed_file: ParsedFile,
    event: JumpEvent,
    output_name_by_source: dict[Path, str],
    local_target_exists: bool,
    local_storage_label: Optional[str],
) -> str:
    target_file_token = Path(parsed_file.output_name).stem
    if local_target_exists or event.target_storage is None:
        return target_file_token
    if local_storage_label:
        return target_file_token

    target_path = parsed_file.source_path.parent / event.target_storage
    target_file_token = normalize_identifier(Path(event.target_storage).stem, prefix="scene")
    if target_path in output_name_by_source:
        return Path(output_name_by_source[target_path]).stem

    add_warning(
        parsed_file,
        event.line_number,
        "unresolved_reference",
        (
            f"Referenced storage `{event.target_storage}` was not provided as "
            "converter input; using a normalized label guess."
        ),
    )
    return target_file_token


def resolve_target_label(
    parsed_file: ParsedFile,
    event: JumpEvent,
    output_name_by_source: dict[Path, str],
) -> str:
    is_single_file_mode = len(output_name_by_source) == 1
    local_target_exists = False
    if event.target_label:
        local_target_exists = (
            normalize_label_reference(event.target_label) in parsed_file.label_names
        )
    local_storage_label = None
    if is_single_file_mode:
        local_storage_label = resolve_local_storage_label(parsed_file, event)
    target_file_token = resolve_target_file_token(
        parsed_file,
        event,
        output_name_by_source,
        local_target_exists,
        local_storage_label,
    )

    if event.target_label:
        if event.target_storage and is_single_file_mode and not local_target_exists:
            add_warning(
                parsed_file,
                event.line_number,
                "unresolved_external_flow",
                (
                    "Referenced jump/call target may require another converted file or "
                    "manual routing: storage=`"
                    f"{event.target_storage}`, target=`{event.target_label}`."
                ),
            )
        return f"{target_file_token}__{normalize_label_reference(event.target_label)}"

    if local_storage_label:
        return f"{target_file_token}__{local_storage_label}"

    if event.target_storage and is_single_file_mode:
        add_warning(
            parsed_file,
            event.line_number,
            "unresolved_external_flow",
            (
                "Referenced jump/call target may require another converted file or "
                f"manual routing: storage=`{event.target_storage}`."
            ),
        )

    return f"{target_file_token}__start"


def handle_jump_or_conditional_event(
    parsed_file: ParsedFile,
    event: Event,
    lines: List[str],
    indent_level: int,
    output_name_by_source: dict[Path, str],
) -> Optional[int]:
    if isinstance(event, JumpEvent):
        if event.target_storage is None and event.target_label is None and not event.is_call:
            append_line(lines, indent_level, "return")
            return indent_level
        target_label = resolve_target_label(parsed_file, event, output_name_by_source)
        command = "call" if event.is_call else "jump"
        append_line(lines, indent_level, f"{command} {target_label}")
        return indent_level

    if isinstance(event, ConditionalEvent):
        if event.kind == "if":
            append_line(lines, indent_level, f"if {event.expression or 'True'}:")
            return indent_level + 1
        if event.kind == "elsif":
            next_indent = max(indent_level - 1, 1)
            append_line(lines, next_indent, f"elif {event.expression or 'True'}:")
            return next_indent + 1
        if event.kind == "else":
            next_indent = max(indent_level - 1, 1)
            append_line(lines, next_indent, "else:")
            return next_indent + 1
        if event.kind == "endif":
            return max(indent_level - 1, 1)
        return indent_level

    if isinstance(event, UnsupportedEvent):
        append_line(lines, indent_level, f"# TODO TYRANO: unsupported tag: {event.raw_line}")
        return indent_level

    return None


def handle_audio_or_flow_event(
    parsed_file: ParsedFile,
    event: Event,
    lines: List[str],
    indent_level: int,
    output_name_by_source: dict[Path, str],
) -> Optional[int]:
    audio_indent = handle_audio_or_message_event(event, lines, indent_level)
    if audio_indent is not None:
        return audio_indent

    quake_indent = handle_quake_or_wait_event(parsed_file, event, lines, indent_level)
    if quake_indent is not None:
        return quake_indent

    return handle_jump_or_conditional_event(
        parsed_file,
        event,
        lines,
        indent_level,
        output_name_by_source,
    )


def emit_event(
    parsed_file: ParsedFile,
    event: Event,
    lines: List[str],
    indent_level: int,
    output_name_by_source: dict[Path, str],
) -> int:
    if isinstance(event, DialogueEvent):
        say_args = build_say_args(event.font_style)
        if event.speaker == "NARRATION":
            if say_args:
                append_line(
                    lines, indent_level, f'narrator "{escape_string(event.text)}"{say_args}'
                )
            else:
                append_line(lines, indent_level, f'"{escape_string(event.text)}"')
        else:
            speaker_id = normalize_identifier(event.speaker, prefix="speaker")
            append_line(
                lines, indent_level, f'{speaker_id} "{escape_string(event.text)}"{say_args}'
            )
        return indent_level

    visual_indent = handle_visual_event(parsed_file, event, lines, indent_level)
    if visual_indent is not None:
        return visual_indent

    flow_indent = handle_audio_or_flow_event(
        parsed_file,
        event,
        lines,
        indent_level,
        output_name_by_source,
    )
    if flow_indent is not None:
        return flow_indent

    if render_script_event(parsed_file, event, lines, indent_level):
        return indent_level

    return indent_level


def render_event_block(
    parsed_file: ParsedFile,
    events: Sequence[Event],
    lines: List[str],
    output_name_by_source: dict[Path, str],
) -> int:
    indent_level = 1
    for event in events:
        indent_level = emit_event(
            parsed_file,
            event,
            lines,
            indent_level,
            output_name_by_source,
        )
    return indent_level


def has_terminal_flow(events: Sequence[Event]) -> bool:
    if not events:
        return False
    last_event = events[-1]
    if isinstance(last_event, JumpEvent):
        return not last_event.is_call
    return False


def build_characters_file(parsed_files: Sequence[ParsedFile]) -> str:
    return build_shared_characters_file(
        parsed_files,
        "# No named speakers detected in the current input set.",
    )


def build_images_file(parsed_files: Sequence[ParsedFile]) -> str:
    return build_shared_images_file(
        parsed_files,
        "# No image declarations detected in the current input set.",
    )


def render_parsed_file(
    parsed_file: ParsedFile,
    output_name_by_source: dict[Path, str],
    include_public_start: bool,
) -> str:
    lines = [f"# Generated from {parsed_file.source_path.name}", ""]
    prelude, sections = partition_events(parsed_file.events)
    first_label_name = (
        build_label_name(parsed_file.source_path, sections[0][0].label_name) if sections else None
    )

    if include_public_start:
        lines.append("label start:")
        lines.append(f"    jump {parsed_file.entry_label}")
        lines.append("")

    lines.append(f"label {parsed_file.entry_label}:")
    if prelude:
        indent_level = render_event_block(
            parsed_file,
            prelude,
            lines,
            output_name_by_source,
        )
    else:
        indent_level = 1
    if first_label_name and not has_terminal_flow(prelude):
        append_line(lines, indent_level, f"jump {first_label_name}")
    elif not prelude:
        append_line(lines, indent_level, "return")

    lines.append("")

    for label_event, events in sections:
        label_name = build_label_name(parsed_file.source_path, label_event.label_name)
        lines.append(f"label {label_name}:")
        indent_level = 1

        if not events:
            append_line(lines, indent_level, "return")
            lines.append("")
            continue

        indent_level = render_event_block(
            parsed_file,
            events,
            lines,
            output_name_by_source,
        )

        if indent_level != 1:
            add_warning(
                parsed_file,
                label_event.line_number,
                "flow_structure",
                (
                    f"Label `{label_event.label_name}` ended with an unbalanced "
                    "conditional indentation state."
                ),
            )

        if indent_level == 1 and not has_terminal_flow(events):
            append_line(lines, indent_level, "return")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_filename_map(parsed_files: Sequence[ParsedFile], single_file_mode: bool) -> str:
    lines = ["# Filename Map", "", "## Source To Output", ""]
    for parsed_file in parsed_files:
        if single_file_mode:
            lines.append(f"- `{parsed_file.source_path.name}` -> `game/script.rpy`")
        else:
            lines.append(
                f"- `{parsed_file.source_path.name}` -> `game/story/{parsed_file.output_name}`"
            )
    return "\n".join(lines).rstrip() + "\n"


def build_start_file(entry_file: ParsedFile) -> str:
    return f"# Generated startup handoff\n\nlabel start:\n    jump {entry_file.entry_label}\n"


def render_warning_report(parsed_files: Sequence[ParsedFile]) -> str:
    return render_shared_warning_report(
        parsed_files,
        "- No warnings recorded for the current safe-subset conversion run.",
    )


def write_outputs(parsed_files: Sequence[ParsedFile], output_dir: Path) -> List[Path]:
    game_dir = output_dir / "game"
    single_file_mode = len(parsed_files) == 1
    story_dir = game_dir / "story"
    game_dir.mkdir(parents=True, exist_ok=True)
    if not single_file_mode:
        story_dir.mkdir(parents=True, exist_ok=True)

    output_name_by_source = {
        parsed_file.source_path: parsed_file.output_name for parsed_file in parsed_files
    }
    written_paths: List[Path] = []

    characters_path = game_dir / "characters.rpy"
    characters_path.write_text(build_characters_file(parsed_files), encoding="utf-8")
    written_paths.append(characters_path)

    images_path = game_dir / "images.rpy"
    images_path.write_text(build_images_file(parsed_files), encoding="utf-8")
    written_paths.append(images_path)

    transitions_path = game_dir / "transitions.rpy"
    transitions_path.write_text(build_quake_transitions_file(parsed_files), encoding="utf-8")
    written_paths.append(transitions_path)

    filename_map_path = game_dir / "filename_map.md"
    filename_map_path.write_text(
        render_filename_map(parsed_files, single_file_mode),
        encoding="utf-8",
    )
    written_paths.append(filename_map_path)

    if single_file_mode:
        parsed_file = parsed_files[0]
        script_path = game_dir / "script.rpy"
        script_path.write_text(
            render_parsed_file(
                parsed_file,
                output_name_by_source,
                include_public_start=True,
            ),
            encoding="utf-8",
        )
        written_paths.append(script_path)
    else:
        start_path = game_dir / "script.rpy"
        start_path.write_text(build_start_file(parsed_files[0]), encoding="utf-8")
        written_paths.append(start_path)

        for parsed_file in parsed_files:
            output_path = story_dir / parsed_file.output_name
            output_path.write_text(
                render_parsed_file(
                    parsed_file,
                    output_name_by_source,
                    include_public_start=False,
                ),
                encoding="utf-8",
            )
            written_paths.append(output_path)

    warning_report_path = game_dir / "conversion_warnings.md"
    warning_report_path.write_text(render_warning_report(parsed_files), encoding="utf-8")
    written_paths.append(warning_report_path)

    return written_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert TyranoScript KS files into a safe Ren'Py subset.",
    )
    add_version_argument(parser)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more .ks files or directories containing .ks files",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Directory to write generated Ren'Py files (default: out)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_paths = expand_input_paths(args.inputs)
    output_name_map = build_output_name_map(input_paths)
    parsed_files = [parse_ks_file(path, output_name_map[path]) for path in input_paths]
    written_paths = write_outputs(parsed_files, args.out_dir)

    print("Wrote outputs:")
    for written_path in written_paths:
        print(f"- {written_path}")
