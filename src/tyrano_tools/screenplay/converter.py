"""Convert TyranoBuilder KS scripts to text and screenplay formats."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from tyrano_tools.contracts import (
    ActionBlock,
    Chapter,
    ChoiceBlock,
    ChoiceOption,
    DialogueBlock,
    EngineDetailBlock,
    FlowBlock,
    Scene,
    TextToken,
)
from tyrano_tools.ks.io import read_ks_lines
from tyrano_tools.ks.tags import parse_tag_attributes, parse_tyrano_tag_line
from tyrano_tools.ks.text import append_terminal_line_break, trim_trailing_empty_lines
from tyrano_tools.version import add_version_argument

TOKEN_PATTERN = re.compile(
    r"(\[p\]|\[l\]|\[r\]|\[ruby\s+[^\]]+\]|\[graph\s+[^\]]+\]|\[mark(?:\s+[^\]]+)?\]|\[endmark\]|\[emb\s+[^\]]+\])"
)
INLINE_LINK_PATTERN = re.compile(r"^\[link\s*(.*?)\](.*?)\[endlink\]\s*$")

DEFAULT_CHAPTER_TITLE = "UNLABELED"
DEFAULT_SCENE_TITLE = "UNKNOWN SCENE"

TAG_LABELS = {
    "3d_init": "3D INIT",
    "3d_scene": "3D SCENE",
    "3d_close": "3D CLOSE",
    "3d_canvas_show": "3D CANVAS SHOW",
    "3d_canvas_hide": "3D CANVAS HIDE",
    "3d_camera": "3D CAMERA",
    "3d_gyro": "3D GYRO",
    "3d_gyro_stop": "3D GYRO STOP",
    "3d_fps_control": "3D FPS CONTROL",
    "3d_model_new": "3D MODEL NEW",
    "3d_cylinder_new": "3D CYLINDER NEW",
    "3d_sphere_new": "3D SPHERE NEW",
    "3d_sprite_new": "3D SPRITE NEW",
    "3d_box_new": "3D BOX NEW",
    "3d_image_new": "3D IMAGE NEW",
    "3d_text_new": "3D TEXT NEW",
    "3d_show": "3D SHOW",
    "3d_hide": "3D HIDE",
    "3d_hide_all": "3D HIDE ALL",
    "3d_delete": "3D DELETE",
    "3d_delete_all": "3D DELETE ALL",
    "3d_new_group": "3D NEW GROUP",
    "3d_add_group": "3D ADD GROUP",
    "3d_anim": "3D ANIMATION",
    "3d_anim_stop": "3D ANIMATION STOP",
    "3d_motion": "3D MOTION",
    "3d_event": "3D EVENT",
    "3d_event_delete": "3D EVENT DELETE",
    "3d_event_start": "3D EVENT START",
    "3d_event_stop": "3D EVENT STOP",
    "3d_sound": "3D SOUND",
    "apply_local_patch": "LOCAL PATCH APPLY",
    "autoconfig": "AUTO CONFIG",
    "autostart": "AUTO START",
    "autostop": "AUTO STOP",
    "backlay": "BACK LAYER COPY",
    "bgcamera": "BACKGROUND CAMERA",
    "playbgm": "BGM PLAY",
    "bgmopt": "BGM CONFIG",
    "bgmovie": "BACKGROUND MOVIE PLAY",
    "body": "BODY CONFIG",
    "button": "CHOICE BUTTON",
    "check_web_patch": "WEB PATCH CHECK",
    "close": "WINDOW CLOSE",
    "closeconfirm_off": "CLOSE CONFIRM OFF",
    "closeconfirm_on": "CLOSE CONFIRM ON",
    "commit": "INPUT COMMIT",
    "config_record_label": "READ LABEL CONFIG",
    "cursor": "CURSOR CONFIG",
    "dialog": "DIALOG",
    "dialog_config": "DIALOG CONFIG",
    "dialog_config_filter": "DIALOG FILTER CONFIG",
    "dialog_config_ng": "DIALOG CANCEL CONFIG",
    "dialog_config_ok": "DIALOG OK CONFIG",
    "edit": "INPUT EDIT",
    "endhtml": "HTML END",
    "stopbgm": "BGM STOP",
    "breakgame": "GAME STATE CLEAR",
    "camera": "CAMERA",
    "cancelskip": "SKIP CANCEL",
    "chara_config": "CHARACTER CONFIG",
    "chara_face": "CHARACTER FACE",
    "chara_move": "CHARACTER MOVE",
    "chara_new": "CHARACTER DEFINE",
    "chara_part": "CHARACTER PART",
    "chara_ptext": "CHARACTER NAME TEXT",
    "playse": "SFX PLAY",
    "stopse": "SFX STOP",
    "changevol": "AUDIO VOLUME",
    "clearstack": "STACK CLEAR",
    "clearsysvar": "SYSTEM VARIABLES CLEAR",
    "clearvar": "VARIABLES CLEAR",
    "cm": "MESSAGE CLEAR ALL",
    "configdelay": "DEFAULT TEXT DELAY",
    "ct": "MESSAGE RESET",
    "current": "MESSAGE LAYER SELECT",
    "deffont": "DEFAULT FONT",
    "delay": "TEXT DELAY",
    "endignore": "IGNORE END",
    "endlink": "CHOICE END",
    "endnolog": "BACKLOG RESUME",
    "endnowait": "INSTANT TEXT STOP",
    "erasemacro": "MACRO DELETE",
    "er": "MESSAGE CLEAR",
    "eval": "EVAL",
    "fadeinbgm": "BGM FADE IN",
    "fadeinse": "SFX FADE IN",
    "fadeoutbgm": "BGM FADE OUT",
    "fadeoutse": "SFX FADE OUT",
    "filter": "FILTER",
    "font": "FONT",
    "free": "OBJECT FREE",
    "freeimage": "LAYER CLEAR",
    "fuki_chara": "SPEECH_BUBBLE TARGET",
    "fuki_start": "SPEECH_BUBBLE START",
    "fuki_stop": "SPEECH_BUBBLE STOP",
    "glyph": "CLICK GLYPH CONFIG",
    "glyph_auto": "AUTO GLYPH CONFIG",
    "glyph_skip": "SKIP GLYPH CONFIG",
    "glink": "GRAPHICAL CHOICE",
    "glink_config": "GRAPHICAL CHOICE CONFIG",
    "bg": "BACKGROUND",
    "bg2": "BACKGROUND",
    "hidemessage": "WINDOW TEMP HIDE",
    "hidemenubutton": "MENU BUTTON HIDE",
    "html": "HTML START",
    "ignore": "IGNORE START",
    "image": "IMAGE SHOW",
    "jump": "JUMP TO",
    "lang_set": "LANGUAGE SET",
    "layopt": "LAYER CONFIG",
    "link": "CHOICE START",
    "loadjs": "JAVASCRIPT LOAD",
    "loadcss": "CSS LOAD",
    "loading_log": "LOADING LOG",
    "locate": "POSITION SET",
    "macro": "MACRO START",
    "endmacro": "MACRO END",
    "message_config": "MESSAGE CONFIG",
    "mode_effect": "MODE EFFECT",
    "movie": "MOVIE",
    "nolog": "BACKLOG PAUSE",
    "nowait": "INSTANT TEXT START",
    "pausebgm": "BGM PAUSE",
    "pausese": "SFX PAUSE",
    "mtext": "MOTION TEXT",
    "ptext": "POSITIONED TEXT",
    "plugin": "PLUGIN LOAD",
    "position": "WINDOW CONFIG",
    "position_filter": "WINDOW FILTER CONFIG",
    "preload": "PRELOAD",
    "pushlog": "BACKLOG ADD",
    "qr_config": "QR CONFIG",
    "qr_define": "QR DEFINE",
    "call": "CALL SUBROUTINE",
    "clickable": "CLICKABLE AREA",
    "rollback": "ROLLBACK",
    "save_img": "SAVE IMAGE CONFIG",
    "savesnap": "SAVE SNAPSHOT",
    "screen_full": "FULLSCREEN",
    "set_resizecall": "RESIZE CALLBACK",
    "showload": "LOAD SCREEN SHOW",
    "showlog": "BACKLOG SHOW",
    "showmenu": "MENU SHOW",
    "showmenubutton": "MENU BUTTON SHOW",
    "showsave": "SAVE SCREEN SHOW",
    "s": "GAME STOP",
    "speak_off": "SPEECH OFF",
    "speak_on": "SPEECH ON",
    "start_keyconfig": "KEYCONFIG START",
    "wait": "WAIT",
    "wait_cancel": "WAIT CANCEL",
    "wait_bgmovie": "BACKGROUND MOVIE WAIT",
    "wait_camera": "CAMERA WAIT",
    "wait_preload": "PRELOAD WAIT",
    "wa": "ANIMATION WAIT",
    "web": "WEB OPEN",
    "wbgm": "BGM WAIT",
    "wse": "SFX WAIT",
    "quake": "SHAKE",
    "chara_show": "CHARACTER SHOW",
    "chara_hide": "CHARACTER HIDE",
    "chara_mod": "CHARACTER MOD",
    "chara_hide_all": "CHARACTERS HIDE ALL",
    "popopo": "VOICE BEEP PLAY",
    "resetdelay": "TEXT DELAY RESET",
    "resetfont": "FONT RESET",
    "resumebgm": "BGM RESUME",
    "resumese": "SFX RESUME",
    "return": "RETURN",
    "seopt": "SFX CONFIG",
    "skipstart": "SKIP START",
    "skipstop": "SKIP STOP",
    "sleepgame": "GAME SUSPEND",
    "stop_bgcamera": "BACKGROUND CAMERA STOP",
    "stop_bgmovie": "BACKGROUND MOVIE STOP",
    "stop_keyconfig": "KEYCONFIG STOP",
    "sysview": "SYSTEM VIEW CONFIG",
    "tb_show_message_window": "WINDOW SHOW",
    "tb_hide_message_window": "WINDOW HIDE",
    "title": "TITLE CONFIG",
    "trans": "TRANSITION",
    "trace": "TRACE",
    "unload": "UNLOAD",
    "awakegame": "GAME RESUME",
    "voconfig": "VOICE CONFIG",
    "vostart": "VOICE AUTO START",
    "vostop": "VOICE AUTO STOP",
    "wt": "TRANSITION WAIT",
    "xchgbgm": "BGM CROSSFADE",
    "if": "IF",
    "elsif": "ELSE IF",
    "else": "ELSE",
    "endif": "END IF",
}

ACTION_CUE_TAGS = {
    "backlay",
    "bg",
    "bg2",
    "bgmovie",
    "bgmopt",
    "camera",
    "changevol",
    "chara_config",
    "chara_face",
    "chara_hide",
    "chara_hide_all",
    "chara_mod",
    "chara_move",
    "chara_new",
    "chara_part",
    "chara_ptext",
    "chara_show",
    "fadeinbgm",
    "fadeinse",
    "fadeoutbgm",
    "fadeoutse",
    "filter",
    "font",
    "free",
    "freeimage",
    "fuki_chara",
    "fuki_start",
    "fuki_stop",
    "hidemessage",
    "deffont",
    "image",
    "jump",
    "layopt",
    "locate",
    "movie",
    "mtext",
    "pausebgm",
    "pausese",
    "playbgm",
    "playse",
    "ptext",
    "position",
    "popopo",
    "quake",
    "resetfont",
    "resumebgm",
    "resumese",
    "seopt",
    "stop_bgmovie",
    "stopbgm",
    "stopse",
    "tb_hide_message_window",
    "tb_show_message_window",
    "trans",
    "wait",
    "wait_bgmovie",
    "wait_camera",
    "wa",
    "wbgm",
    "wse",
    "wt",
    "xchgbgm",
}

FLOW_CONTROL_TAGS = {
    "call",
    "clearstack",
    "else",
    "elsif",
    "endif",
    "endignore",
    "endmacro",
    "if",
    "ignore",
    "jump",
    "macro",
    "return",
}

CHOICE_TAGS = {"button", "clickable", "glink", "link"}

MESSAGE_CONTROL_TAGS = {
    "awakegame",
    "autoload",
    "autosave",
    "autoconfig",
    "autostart",
    "autostop",
    "breakgame",
    "cancelskip",
    "checkpoint",
    "clearvar",
    "clear_checkpoint",
    "cm",
    "commit",
    "config_record_label",
    "configdelay",
    "ct",
    "current",
    "deffont",
    "delay",
    "edit",
    "endnolog",
    "endnowait",
    "eval",
    "er",
    "message_config",
    "nolog",
    "nowait",
    "pushlog",
    "resetdelay",
    "rollback",
    "s",
    "speak_off",
    "speak_on",
    "sleepgame",
    "skipstart",
    "skipstop",
    "voconfig",
    "vostart",
    "vostop",
    "wait_cancel",
}

ENGINE_DETAIL_TAGS = {
    "3d_add_group",
    "3d_anim",
    "3d_anim_stop",
    "3d_box_new",
    "3d_camera",
    "3d_canvas_hide",
    "3d_canvas_show",
    "3d_close",
    "3d_cylinder_new",
    "3d_delete",
    "3d_delete_all",
    "3d_event",
    "3d_event_delete",
    "3d_event_start",
    "3d_event_stop",
    "3d_fps_control",
    "3d_gyro",
    "3d_gyro_stop",
    "3d_image_new",
    "3d_init",
    "3d_model_new",
    "3d_motion",
    "3d_new_group",
    "3d_scene",
    "3d_show",
    "3d_hide",
    "3d_hide_all",
    "3d_sound",
    "3d_sphere_new",
    "3d_sprite_new",
    "3d_text_new",
    "apply_local_patch",
    "bgcamera",
    "body",
    "check_web_patch",
    "close",
    "closeconfirm_off",
    "closeconfirm_on",
    "clearsysvar",
    "cursor",
    "dialog",
    "dialog_config",
    "dialog_config_filter",
    "dialog_config_ng",
    "dialog_config_ok",
    "endhtml",
    "endscript",
    "erasemacro",
    "glyph",
    "glyph_auto",
    "glyph_skip",
    "glink_config",
    "hidemenubutton",
    "html",
    "iscript",
    "loadjs",
    "loadcss",
    "plugin",
    "position_filter",
    "preload",
    "qr_config",
    "qr_define",
    "save_img",
    "savesnap",
    "screen_full",
    "set_resizecall",
    "showload",
    "showlog",
    "showmenu",
    "showmenubutton",
    "showsave",
    "start_keyconfig",
    "stop_bgcamera",
    "stop_keyconfig",
    "sysview",
    "title",
    "unload",
    "wait_preload",
    "web",
}


@dataclass
class ParseState:
    current_chapter: Chapter
    current_scene: Optional[Scene] = None
    in_text_block: bool = False
    in_engine_script_block: bool = False
    in_engine_html_block: bool = False
    current_speaker: str = "NARRATION"
    current_tokens: list[TextToken] = field(default_factory=list)
    current_choice_options: list[ChoiceOption] = field(default_factory=list)
    current_engine_detail_lines: list[str] = field(default_factory=list)


def parse_inline_link_choice(line: str) -> Optional[ChoiceOption]:
    match = INLINE_LINK_PATTERN.match(line.strip())
    if not match:
        return None

    attrs = parse_tag_attributes(match.group(1))
    label = match.group(2).strip() or "Choice option"
    return ChoiceOption(kind="link", label=label, attrs=attrs)


def parse_text_tokens(text: str) -> List[TextToken]:
    tokens: List[TextToken] = []
    parts = TOKEN_PATTERN.split(text)

    for part in parts:
        if not part:
            continue
        if part == "[p]":
            tokens.append(TextToken(kind="panel_break"))
        elif part == "[l]":
            tokens.append(TextToken(kind="pause"))
        elif part == "[r]":
            tokens.append(TextToken(kind="line_break"))
        elif part.startswith("[ruby"):
            attrs = parse_tag_attributes(part[1:-1].partition(" ")[2])
            tokens.append(TextToken(kind="ruby", value=attrs.get("text", "")))
        elif part.startswith("[graph"):
            attrs = parse_tag_attributes(part[1:-1].partition(" ")[2])
            storage = attrs.get("storage") or attrs.get("text") or attrs.get("name") or "inline"
            tokens.append(TextToken(kind="graph", value=storage))
        elif part.startswith("[mark"):
            attrs = parse_tag_attributes(part[1:-1].partition(" ")[2])
            details = ", ".join(f"{key}={attrs[key]}" for key in sorted(attrs))
            tokens.append(TextToken(kind="mark_start", value=details or None))
        elif part == "[endmark]":
            tokens.append(TextToken(kind="mark_end"))
        elif part.startswith("[emb"):
            attrs = parse_tag_attributes(part[1:-1].partition(" ")[2])
            embed_value = attrs.get("exp") or attrs.get("text") or attrs.get("name") or "embed"
            tokens.append(TextToken(kind="embed", value=embed_value))
        else:
            tokens.append(TextToken(kind="text", value=part))

    return tokens


def apply_ruby_annotation(text_value: str, ruby_text: str) -> str:
    if not text_value:
        return f"{{ruby:{ruby_text}}}"

    first_char = text_value[0]
    if re.match(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", first_char):
        return f"{first_char}{{ruby:{ruby_text}}}{text_value[1:]}"

    match = re.match(r"(\S+)(\s.*)?$", text_value)
    if not match:
        return f"{{ruby:{ruby_text}}}{text_value}"

    base_text = match.group(1)
    remainder = match.group(2) or ""
    return f"{base_text}{{ruby:{ruby_text}}}{remainder}"


def append_panel_break(lines: list[str], panel_marker: Optional[str]) -> None:
    lines.append("")
    if panel_marker:
        lines.append(panel_marker)
    lines.append("")


def append_special_token_line(
    lines: list[str],
    token: TextToken,
    include_pauses: bool,
) -> Optional[str]:
    if token.kind == "pause":
        if include_pauses:
            lines[-1] += "[PAUSE]"
        return None
    if token.kind == "ruby":
        return token.value or ""
    if token.kind == "graph":
        lines[-1] += f"[INLINE_IMAGE: {token.value or 'inline'}]"
        return None
    if token.kind == "mark_start":
        lines[-1] += f"[MARK {token.value}]" if token.value else "[MARK]"
        return None
    if token.kind == "mark_end":
        lines[-1] += "[/MARK]"
        return None
    if token.kind == "embed":
        lines[-1] += f"[EMBED: {token.value or 'embed'}]"
        return None
    return None


def tokens_to_lines(
    tokens: Sequence[TextToken],
    include_pauses: bool,
    panel_marker: Optional[str],
) -> List[str]:
    lines: List[str] = [""]
    pending_ruby: Optional[str] = None

    for token in tokens:
        if token.kind == "text":
            text_value = token.value or ""
            if pending_ruby and text_value:
                lines[-1] += apply_ruby_annotation(text_value, pending_ruby)
                pending_ruby = None
            else:
                lines[-1] += text_value
        elif token.kind == "line_break":
            lines.append("")
        elif token.kind == "panel_break":
            append_panel_break(lines, panel_marker)
        else:
            next_pending_ruby = append_special_token_line(lines, token, include_pauses)
            if next_pending_ruby is not None:
                pending_ruby = next_pending_ruby

    if pending_ruby:
        lines[-1] += f"{{ruby:{pending_ruby}}}"

    return trim_trailing_empty_lines(lines)


def get_tag_label(tag: str) -> str:
    return TAG_LABELS.get(tag, tag.replace("_", " ").upper())


def format_action_line(tag: str, attrs: dict[str, str]) -> str:
    label = get_tag_label(tag)
    details: List[str]

    if tag == "ptext":
        text_value = attrs.get("text", "")
        details = []
        if "cond" in attrs:
            details.append(f"cond={attrs['cond']}")
        suffix = f", {', '.join(details)}" if details else ""
        return f'VISIBLE_TEXT PTEXT: "{text_value}"{suffix}'

    if tag == "mtext":
        text_value = attrs.get("text", "")
        details = []
        if "in_effect" in attrs:
            details.append(f"in_effect={attrs['in_effect']}")
        if "cond" in attrs:
            details.append(f"cond={attrs['cond']}")
        suffix = f", {', '.join(details)}" if details else ""
        return f'VISIBLE_TEXT MTEXT: "{text_value}"{suffix}'

    if tag == "fuki_chara":
        target = attrs.get("name", "UNKNOWN")
        details = []
        if "cond" in attrs:
            details.append(f"cond={attrs['cond']}")
        suffix = f", {', '.join(details)}" if details else ""
        return f"{label}: {target}{suffix}"

    details = []

    if "name" in attrs:
        details.append(attrs["name"])
    if "storage" in attrs:
        details.append(attrs["storage"])

    for key in sorted(attrs.keys() - {"name", "storage"}):
        details.append(f"{key}={attrs[key]}")

    if details:
        return f"{label}: {', '.join(details)}"

    return label


def append_attr_details(
    base_line: str,
    attrs: dict[str, str],
    excluded_keys: set[str],
) -> str:
    details: List[str] = []

    for key in sorted(attrs.keys() - excluded_keys):
        details.append(f"{key}={attrs[key]}")

    if not details:
        return base_line

    separator = ", " if ": " in base_line else ": "
    return f"{base_line}{separator}{', '.join(details)}"


def format_engine_detail_content(tag: str, attrs: dict[str, str]) -> str:
    label = get_tag_label(tag)
    details: List[str] = []

    if "name" in attrs:
        details.append(attrs["name"])
    if "storage" in attrs:
        details.append(attrs["storage"])

    for key in sorted(attrs.keys() - {"name", "storage"}):
        details.append(f"{key}={attrs[key]}")

    return label if not details else f"{label}: {', '.join(details)}"


def render_engine_detail_lines(contents: Sequence[str], output_format: str) -> List[str]:
    lines: List[str] = []

    for content in contents:
        if output_format == "markdown":
            lines.append(f"> ENGINE: {content}")
        elif output_format == "fountain":
            lines.append(f"[[ENGINE: {content}]]")
        else:
            lines.append(f"// ENGINE: {content}")

    return lines


def normalize_section_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lstrip("*").lower())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_") or "section"


def build_anchor_lookup(chapters: Sequence[Chapter]) -> dict[str, str]:
    seen: dict[str, int] = {}
    lookup: dict[str, str] = {}

    for chapter in chapters:
        if not chapter.title or chapter.title == DEFAULT_CHAPTER_TITLE:
            continue
        base_id = normalize_section_id(chapter.title)
        seen[base_id] = seen.get(base_id, 0) + 1
        anchor_id = base_id if seen[base_id] == 1 else f"{base_id}_{seen[base_id]}"
        lookup.setdefault(chapter.title, anchor_id)

    return lookup


def build_chapter_anchor_id(title: str, seen: dict[str, int]) -> str:
    base_id = normalize_section_id(title)
    seen[base_id] = seen.get(base_id, 0) + 1
    if seen[base_id] == 1:
        return base_id
    return f"{base_id}_{seen[base_id]}"


def format_reference_title(attrs: dict[str, str]) -> Optional[str]:
    target = attrs.get("target", "").strip()
    storage = attrs.get("storage", "").strip()

    if target:
        return target.lstrip("*") or None
    if storage:
        return Path(storage).stem

    return None


def format_reference_value(
    attrs: dict[str, str],
    output_format: str,
    anchor_lookup: Optional[dict[str, str]] = None,
) -> Optional[str]:
    title = format_reference_title(attrs)
    if not title:
        return None

    section_id = (
        anchor_lookup.get(title, normalize_section_id(title))
        if anchor_lookup
        else normalize_section_id(title)
    )

    if output_format == "plaintext":
        return f"_{section_id}"
    if output_format == "markdown":
        return f"[{title}](#chapter_{section_id})"
    return title


def format_flow_line(
    tag: str,
    attrs: dict[str, str],
    output_format: str,
    anchor_lookup: Optional[dict[str, str]] = None,
) -> str:
    label = get_tag_label(tag)

    if tag in {"jump", "call"}:
        details: List[str] = []
        target = format_reference_value(attrs, output_format, anchor_lookup)
        if target:
            details.append(target)
        for key in sorted(attrs.keys() - {"storage", "target"}):
            details.append(f"{key}={attrs[key]}")
        if details:
            return f"{label}: {', '.join(details)}"
        return label

    if tag in {"if", "elsif"}:
        expression = attrs.get("exp")
        if expression:
            return append_attr_details(f"{label}: {expression}", attrs, {"exp"})
        return append_attr_details(label, attrs, set())

    if tag in {"else", "endif", "return"}:
        return append_attr_details(label, attrs, set())

    return append_attr_details(label, attrs, set())


def build_choice_option(tag: str, attrs: dict[str, str]) -> ChoiceOption:
    if tag == "glink":
        label = attrs.get("text", "Graphical choice")
    elif tag == "button":
        label = attrs.get("text", "Choice button")
    elif tag == "clickable":
        coords: List[str] = []
        for key, short_key in (("x", "x"), ("y", "y"), ("width", "w"), ("height", "h")):
            if key in attrs:
                coords.append(f"{short_key}={attrs[key]}")
        label = "Clickable area"
        if coords:
            label = f"Clickable area ({' '.join(coords)})"
    else:
        label = attrs.get("text", "Choice option")

    return ChoiceOption(kind=tag, label=label, attrs=attrs)


def render_choice_option(
    option: ChoiceOption,
    output_format: str,
    anchor_lookup: Optional[dict[str, str]] = None,
) -> str:
    target = format_reference_value(option.attrs, output_format, anchor_lookup)
    line = option.label
    if target:
        line = f"{line} -> {target}"
    condition = option.attrs.get("cond")
    if condition:
        line = f"{line} [cond={condition}]"

    return f"- {line}"


def classify_tag(
    tag: str,
    include_action_cues: bool,
    include_flow_control: bool,
    include_message_control: bool,
    include_game_engine_details: bool,
) -> Optional[str]:
    if include_flow_control and tag in CHOICE_TAGS:
        return "choice"
    if include_flow_control and tag in FLOW_CONTROL_TAGS:
        return "flow"
    if include_message_control and tag in MESSAGE_CONTROL_TAGS:
        return "message_control"
    if include_game_engine_details and tag in ENGINE_DETAIL_TAGS:
        return "engine_detail"
    if include_action_cues and tag in ACTION_CUE_TAGS:
        return "action"

    return None


def build_scene_heading(attrs: dict[str, str]) -> str:
    heading = attrs.get("storage", DEFAULT_SCENE_TITLE)
    condition = attrs.get("cond")
    if condition:
        return f"{heading} [cond={condition}]"

    return heading


def ensure_chapter(chapters: List[Chapter], title: str) -> Chapter:
    chapter = Chapter(title=title, scenes=[])
    chapters.append(chapter)
    return chapter


def ensure_scene(chapter: Chapter, heading: str) -> Scene:
    scene = Scene(heading=heading, blocks=[])
    chapter.scenes.append(scene)
    return scene


def flush_dialogue(state: ParseState) -> None:
    if not state.current_tokens:
        return
    if state.current_scene is None:
        state.current_scene = ensure_scene(state.current_chapter, DEFAULT_SCENE_TITLE)
    state.current_scene.blocks.append(
        DialogueBlock(speaker=state.current_speaker, tokens=state.current_tokens)
    )
    state.current_tokens = []


def flush_choices(state: ParseState) -> None:
    if not state.current_choice_options:
        return
    if state.current_scene is None:
        state.current_scene = ensure_scene(state.current_chapter, DEFAULT_SCENE_TITLE)
    state.current_scene.blocks.append(ChoiceBlock(options=state.current_choice_options))
    state.current_choice_options = []


def flush_engine_details(state: ParseState) -> None:
    if not state.current_engine_detail_lines:
        return
    if state.current_scene is None:
        state.current_scene = ensure_scene(state.current_chapter, DEFAULT_SCENE_TITLE)
    state.current_scene.blocks.append(EngineDetailBlock(lines=state.current_engine_detail_lines))
    state.current_engine_detail_lines = []


def flush_non_choice_blocks(state: ParseState) -> None:
    flush_dialogue(state)
    flush_engine_details(state)


def flush_all_blocks(state: ParseState) -> None:
    flush_dialogue(state)
    flush_choices(state)
    flush_engine_details(state)


def handle_engine_script_line(stripped: str, state: ParseState) -> bool:
    if not state.in_engine_script_block:
        return False
    tag_info = parse_tyrano_tag_line(stripped) if stripped else None
    if tag_info and tag_info[0] == "endscript":
        state.current_engine_detail_lines.append(
            format_engine_detail_content("endscript", tag_info[1])
        )
        flush_engine_details(state)
        state.in_engine_script_block = False
    elif stripped:
        state.current_engine_detail_lines.append(stripped)
    return True


def handle_engine_html_line(stripped: str, state: ParseState) -> bool:
    if not state.in_engine_html_block:
        return False
    tag_info = parse_tyrano_tag_line(stripped) if stripped else None
    if tag_info and tag_info[0] == "endhtml":
        state.current_engine_detail_lines.append(
            format_engine_detail_content("endhtml", tag_info[1])
        )
        flush_engine_details(state)
        state.in_engine_html_block = False
    elif stripped:
        state.current_engine_detail_lines.append(stripped)
    return True


def handle_section_heading(stripped: str, chapters: list[Chapter], state: ParseState) -> bool:
    if state.in_text_block or not stripped.startswith("*"):
        return False
    flush_all_blocks(state)
    state.current_chapter = ensure_chapter(
        chapters, stripped.lstrip("*").strip() or DEFAULT_CHAPTER_TITLE
    )
    state.current_scene = None
    return True


def handle_inline_choice_line(stripped: str, include_flow_control: bool, state: ParseState) -> bool:
    if not include_flow_control:
        return False
    inline_choice = parse_inline_link_choice(stripped)
    if inline_choice is None:
        return False
    flush_non_choice_blocks(state)
    state.current_choice_options.append(inline_choice)
    return True


def handle_choice_tag(tag: str, attrs: dict[str, str], state: ParseState) -> None:
    flush_engine_details(state)
    state.current_choice_options.append(build_choice_option(tag, attrs))


def handle_engine_detail_tag(tag: str, attrs: dict[str, str], state: ParseState) -> None:
    flush_choices(state)
    state.current_engine_detail_lines.append(format_engine_detail_content(tag, attrs))
    if tag == "iscript":
        state.in_engine_script_block = True
    elif tag == "html":
        state.in_engine_html_block = True
    else:
        flush_engine_details(state)


def handle_action_or_flow_tag(
    tag: str,
    attrs: dict[str, str],
    tag_kind: str,
    state: ParseState,
) -> None:
    flush_dialogue(state)
    if state.current_scene is None:
        state.current_scene = ensure_scene(state.current_chapter, DEFAULT_SCENE_TITLE)
    if tag_kind == "flow":
        flush_choices(state)
        state.current_scene.blocks.append(FlowBlock(tag=tag, attrs=attrs))
        return
    if tag_kind == "choice":
        handle_choice_tag(tag, attrs, state)
        return
    if tag_kind == "engine_detail":
        handle_engine_detail_tag(tag, attrs, state)
        return
    flush_choices(state)
    flush_engine_details(state)
    state.current_scene.blocks.append(ActionBlock(line=format_action_line(tag, attrs)))


def handle_tag_line(
    tag: str,
    attrs: dict[str, str],
    state: ParseState,
    include_action_cues: bool,
    include_flow_control: bool,
    include_message_control: bool,
    include_game_engine_details: bool,
) -> None:
    if tag == "tb_start_text":
        flush_choices(state)
        flush_engine_details(state)
        state.in_text_block = True
        state.current_speaker = "NARRATION"
        return
    if tag == "_tb_end_text":
        flush_dialogue(state)
        state.in_text_block = False
        state.current_speaker = "NARRATION"
        return
    if tag == "bg":
        flush_choices(state)
        flush_engine_details(state)
        state.current_scene = ensure_scene(state.current_chapter, build_scene_heading(attrs))
        return

    tag_kind = classify_tag(
        tag,
        include_action_cues=include_action_cues,
        include_flow_control=include_flow_control,
        include_message_control=include_message_control,
        include_game_engine_details=include_game_engine_details,
    )
    if tag_kind is not None:
        handle_action_or_flow_tag(tag, attrs, tag_kind, state)


def handle_text_line(stripped: str, line: str, state: ParseState) -> None:
    if not state.in_text_block:
        flush_choices(state)
        flush_engine_details(state)
        return
    if stripped.startswith("#"):
        flush_all_blocks(state)
        state.current_speaker = stripped.lstrip("#").strip() or "NARRATION"
        return

    tokens = parse_text_tokens(line)
    if tokens:
        state.current_tokens.extend(tokens)
        append_terminal_line_break(state.current_tokens)


def parse_ks(
    path: Path,
    include_action_cues: bool,
    include_flow_control: bool,
    include_message_control: bool,
    include_game_engine_details: bool,
) -> List[Chapter]:
    chapters: List[Chapter] = [Chapter(title=DEFAULT_CHAPTER_TITLE, scenes=[])]
    state = ParseState(current_chapter=chapters[0])

    for raw_line in read_ks_lines(path):
        line = raw_line
        stripped = line.strip()

        if handle_engine_script_line(stripped, state):
            continue
        if handle_engine_html_line(stripped, state):
            continue

        if not stripped:
            continue
        if handle_section_heading(stripped, chapters, state):
            continue
        if handle_inline_choice_line(stripped, include_flow_control, state):
            continue

        tag_info = parse_tyrano_tag_line(stripped)
        if tag_info:
            tag, attrs = tag_info
            handle_tag_line(
                tag,
                attrs,
                state,
                include_action_cues=include_action_cues,
                include_flow_control=include_flow_control,
                include_message_control=include_message_control,
                include_game_engine_details=include_game_engine_details,
            )
            continue

        handle_text_line(stripped, line, state)

    flush_all_blocks(state)
    return chapters


def render_plaintext(
    chapters: Sequence[Chapter],
    include_pauses: bool,
    panel_marker: Optional[str],
) -> str:
    output_lines: List[str] = []
    anchor_lookup = build_anchor_lookup(chapters)
    chapter_anchor_seen: dict[str, int] = {}

    for chapter in chapters:
        if chapter.title and chapter.title != DEFAULT_CHAPTER_TITLE:
            output_lines.append(f"CHAPTER: {chapter.title}")
            output_lines.append(f"_{build_chapter_anchor_id(chapter.title, chapter_anchor_seen)}")
            output_lines.append("")

        for scene in chapter.scenes:
            output_lines.append(f"SCENE: {scene.heading}")
            output_lines.append("")
            for block in scene.blocks:
                if isinstance(block, ActionBlock):
                    output_lines.append(f"ACTION: {block.line}")
                elif isinstance(block, FlowBlock):
                    output_lines.append(
                        format_flow_line(block.tag, block.attrs, "plaintext", anchor_lookup)
                    )
                elif isinstance(block, ChoiceBlock):
                    output_lines.append("CHOICE:")
                    for option in block.options:
                        output_lines.append(
                            render_choice_option(option, "plaintext", anchor_lookup)
                        )
                elif isinstance(block, EngineDetailBlock):
                    output_lines.extend(render_engine_detail_lines(block.lines, "plaintext"))
                else:
                    output_lines.append(block.speaker)
                    output_lines.extend(tokens_to_lines(block.tokens, include_pauses, panel_marker))
                output_lines.append("")

    return "\n".join(output_lines).rstrip() + "\n"


def render_screenplay_markdown(
    chapters: Sequence[Chapter],
    include_pauses: bool,
    panel_marker: Optional[str],
) -> str:
    output_lines: List[str] = []
    anchor_lookup = build_anchor_lookup(chapters)
    chapter_anchor_seen: dict[str, int] = {}

    for chapter in chapters:
        if chapter.title and chapter.title != DEFAULT_CHAPTER_TITLE:
            chapter_anchor = build_chapter_anchor_id(chapter.title, chapter_anchor_seen)
            output_lines.append(f'<a id="chapter_{chapter_anchor}"></a>')
            output_lines.append(f"## Chapter: {chapter.title}")
            output_lines.append("")

        for scene in chapter.scenes:
            output_lines.append(f"### Scene: {scene.heading}")
            output_lines.append("")
            for block in scene.blocks:
                if isinstance(block, ActionBlock):
                    output_lines.append(block.line)
                elif isinstance(block, FlowBlock):
                    output_lines.append(
                        format_flow_line(block.tag, block.attrs, "markdown", anchor_lookup)
                    )
                elif isinstance(block, ChoiceBlock):
                    output_lines.append("CHOICE:")
                    for option in block.options:
                        output_lines.append(render_choice_option(option, "markdown", anchor_lookup))
                elif isinstance(block, EngineDetailBlock):
                    output_lines.extend(render_engine_detail_lines(block.lines, "markdown"))
                else:
                    output_lines.append(block.speaker.upper())
                    output_lines.extend(tokens_to_lines(block.tokens, include_pauses, panel_marker))
                output_lines.append("")

    return "\n".join(output_lines).rstrip() + "\n"


def render_fountain(
    chapters: Sequence[Chapter],
    include_pauses: bool,
    panel_marker: Optional[str],
) -> str:
    output_lines: List[str] = []
    anchor_lookup = build_anchor_lookup(chapters)

    for chapter in chapters:
        if chapter.title and chapter.title != DEFAULT_CHAPTER_TITLE:
            output_lines.append(f"## Chapter: {chapter.title}")
            output_lines.append("")

        for scene in chapter.scenes:
            output_lines.append(f"EXT./INT. {scene.heading}")
            output_lines.append("")
            for block in scene.blocks:
                if isinstance(block, ActionBlock):
                    output_lines.append(block.line)
                elif isinstance(block, FlowBlock):
                    output_lines.append(
                        format_flow_line(block.tag, block.attrs, "fountain", anchor_lookup)
                    )
                elif isinstance(block, ChoiceBlock):
                    output_lines.append("CHOICE:")
                    for option in block.options:
                        output_lines.append(render_choice_option(option, "fountain", anchor_lookup))
                elif isinstance(block, EngineDetailBlock):
                    output_lines.extend(render_engine_detail_lines(block.lines, "fountain"))
                else:
                    output_lines.append(block.speaker.upper())
                    output_lines.extend(tokens_to_lines(block.tokens, include_pauses, panel_marker))
                output_lines.append("")

    return "\n".join(output_lines).rstrip() + "\n"


def build_flag_suffix(
    include_pauses: bool,
    include_panel_marker: bool,
    include_action_cues: bool,
    include_flow_control: bool,
    include_message_control: bool,
    include_game_engine_details: bool,
) -> str:
    suffix = ""

    if include_pauses:
        suffix += "p"
    if include_panel_marker:
        suffix += "m"
    if include_action_cues:
        suffix += "n"
    if include_flow_control:
        suffix += "f"
    if include_message_control:
        suffix += "c"
    if include_game_engine_details:
        suffix += "g"

    return f"-{suffix}" if suffix else ""


def build_output_paths(input_path: Path, out_dir: Path, flag_suffix: str) -> dict[str, Path]:
    stem = input_path.stem
    return {
        "plaintext": out_dir / f"{stem}-plaintext{flag_suffix}.txt",
        "markdown": out_dir / f"{stem}-screenplay{flag_suffix}.md",
        "fountain": out_dir / f"{stem}-screenplay{flag_suffix}.fountain",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert TyranoBuilder KS scripts to text and screenplay formats.",
    )
    add_version_argument(parser)
    parser.add_argument("input", type=Path, help="Path to the .ks file")
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Directory to write outputs; enabled flags are appended to filenames (default: out)",
    )
    parser.add_argument(
        "-p",
        "--include-pauses",
        action="store_true",
        help="Include [PAUSE] markers for [l] tags",
    )
    parser.add_argument(
        "-m",
        "--panel-marker",
        action="store_true",
        help="Include [PANEL] markers for [p] tags",
    )
    parser.add_argument(
        "-n",
        "--include-non-dialogue",
        action="store_true",
        help="Include staging and action-cue tags as action lines",
    )
    parser.add_argument(
        "-f",
        "--include-flow-control",
        action="store_true",
        help="Include structural flow tags such as jumps, calls, conditionals, and choices",
    )
    parser.add_argument(
        "-c",
        "--include-message-control",
        action="store_true",
        help="Include message-layer, backlog, auto, skip, and text-speed control tags",
    )
    parser.add_argument(
        "-g",
        "--include-game-engine-details",
        action="store_true",
        help=(
            "Include low-value engine, UI, plugin, and runtime-detail tags; "
            "usually not useful for script reading"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path: Path = args.input

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    panel_marker = "[PANEL]" if args.panel_marker else None
    flag_suffix = build_flag_suffix(
        include_pauses=args.include_pauses,
        include_panel_marker=args.panel_marker,
        include_action_cues=args.include_non_dialogue,
        include_flow_control=args.include_flow_control,
        include_message_control=args.include_message_control,
        include_game_engine_details=args.include_game_engine_details,
    )

    chapters = parse_ks(
        input_path,
        include_action_cues=args.include_non_dialogue,
        include_flow_control=args.include_flow_control,
        include_message_control=args.include_message_control,
        include_game_engine_details=args.include_game_engine_details,
    )
    output_paths = build_output_paths(input_path, args.out_dir, flag_suffix)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    output_paths["plaintext"].write_text(
        render_plaintext(chapters, args.include_pauses, panel_marker),
        encoding="utf-8",
    )
    output_paths["markdown"].write_text(
        render_screenplay_markdown(chapters, args.include_pauses, panel_marker),
        encoding="utf-8",
    )
    output_paths["fountain"].write_text(
        render_fountain(chapters, args.include_pauses, panel_marker),
        encoding="utf-8",
    )

    print("Wrote outputs:")
    for path in output_paths.values():
        print(f"- {path}")


if __name__ == "__main__":
    main()
