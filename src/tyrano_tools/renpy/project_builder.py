#!/usr/bin/env python3
"""Build a Ren'Py project scaffold from a TyranoBuilder project."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

from tyrano_tools.inventory.media import extract_inventory
from tyrano_tools.renpy.paths import (
    remap_audio_storage,
    remap_background_storage,
    remap_character_storage,
)
from tyrano_tools.scenario.converter import (
    determine_startup_plan,
    parse_project_file,
    write_outputs,
)
from tyrano_tools.scenario.output import (
    StartupPlan,
    build_output_name_map,
    preferred_renpy_movie_path,
)
from tyrano_tools.scenario.traversal import (
    discover_reachable_files,
    resolve_entry_file,
    resolve_scenario_dir,
)
from tyrano_tools.version import add_version_argument

PROJECT_OUTPUT_DIRNAME = "game"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

ASSET_DIRECTORIES = [
    "images/backgrounds",
    "images/character",
    "images/ui",
    "audio/bgm",
    "audio/sfx",
    "movies",
    "fonts",
    "gui",
    "gui/button",
    "gui/overlay",
    "gui/bar",
    "gui/scrollbar",
    "gui/slider",
    "gui/phone",
    "gui/phone/button",
    "gui/phone/overlay",
    "gui/phone/bar",
    "gui/phone/scrollbar",
    "gui/phone/slider",
]

RENPY_DEFAULT_MESSAGE_LAYOUT = {
    "textbox_height": 278,
    "name_xpos": 360,
    "name_ypos": 0,
    "namebox_width": None,
    "namebox_height": None,
    "dialogue_xpos": 402,
    "dialogue_ypos": 75,
    "dialogue_width": 1116,
}

DEFAULT_NAME_COLOR = "#fcfcfc"

KEYCODE_TO_RENPY_KEYSYMS = {
    "13": ["K_RETURN", "K_KP_ENTER"],
    "16": ["K_LSHIFT", "K_RSHIFT"],
    "17": ["K_LCTRL", "K_RCTRL"],
    "27": ["K_ESCAPE"],
    "32": ["K_SPACE"],
    "49": ["K_1"],
    "76": ["K_l"],
    "Tab": ["K_TAB"],
    "ArrowUp": ["K_UP"],
    "ArrowDown": ["K_DOWN"],
    "ArrowLeft": ["K_LEFT"],
    "ArrowRight": ["K_RIGHT"],
}


@dataclass
class KeymapBuildState:
    imported: List[str] = field(default_factory=list)
    ignored: List[str] = field(default_factory=list)
    deferred: List[str] = field(default_factory=list)
    builtin_events: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "game_menu": [],
            "dismiss": [],
            "skip": [],
            "focus_up": [],
            "focus_down": [],
            "focus_left": [],
            "focus_right": [],
        }
    )
    custom_events: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "tb_toggle_auto": [],
            "tb_show_load": [],
            "tb_show_history": [],
            "tb_show_save": [],
        }
    )


@dataclass(frozen=True)
class GuiBuildValues:
    width: int
    height: int
    text_size: int
    name_text_size: int
    interface_text_size: int
    label_text_size: int
    notify_text_size: int
    title_text_size: int
    text_font: str
    text_color: str
    accent_color: str
    name_color: str
    history_length: int
    message_layout: Dict[str, Any]
    choice_spacing: int
    file_slot_cols: int
    file_slot_rows: int
    quick_menu_background_alpha: int


@dataclass(frozen=True)
class ScreenStyleValues:
    default_bold: bool
    default_shadow: bool
    default_edge: bool
    shadow_color: str
    edge_color: str


@dataclass(frozen=True)
class ConfigMappingValues:
    message_layout: Dict[str, Any]
    text_cps: int
    afm_time: int
    save_slot_count: int
    save_slot_cols: int
    save_slot_rows: int
    config_window_mode: str
    assumed_font: str
    choice_spacing: int


def parse_keyconfig_js(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None

    raw_text = path.read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\})\s*$", raw_text, flags=re.DOTALL)
    if match is None:
        raise RuntimeError(f"Could not parse KeyConfig.js object literal from: {path}")

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to decode KeyConfig.js as JSON-compatible data: {path}"
        ) from exc


def extract_tyrano_action(raw_action: Any) -> str:
    if not isinstance(raw_action, str):
        return ""
    stripped = raw_action.strip()
    if not stripped:
        return ""
    return stripped.split()[0]


def map_tyrano_keyboard_binding(binding: str) -> List[str]:
    return KEYCODE_TO_RENPY_KEYSYMS.get(binding, [])


def append_unique(sequence: List[str], value: str) -> None:
    if value not in sequence:
        sequence.append(value)


def build_keymap_action_targets(
    state: KeymapBuildState,
) -> Dict[str, tuple[str, Dict[str, List[str]]]]:
    return {
        "ok": ("dismiss", state.builtin_events),
        "auto": ("tb_toggle_auto", state.custom_events),
        "skip": ("skip", state.builtin_events),
        "menu": ("game_menu", state.builtin_events),
        "load": ("tb_show_load", state.custom_events),
        "backlog": ("tb_show_history", state.custom_events),
        "focus_up": ("focus_up", state.builtin_events),
        "focus_down": ("focus_down", state.builtin_events),
        "focus_left": ("focus_left", state.builtin_events),
        "focus_right": ("focus_right", state.builtin_events),
    }


def record_keymap_binding(
    state: KeymapBuildState,
    action_targets: Dict[str, tuple[str, Dict[str, List[str]]]],
    raw_key: str,
    action: str,
    keysyms: List[str],
) -> None:
    if action == "save" and "K_ESCAPE" in keysyms:
        state.ignored.append("keyboard `Escape` -> `save` (kept Ren'Py `game_menu`)")
        return

    if action == "save":
        target_name, target_bucket = ("tb_show_save", state.custom_events)
    else:
        target = action_targets.get(action)
        if target is None:
            state.deferred.append(f"keyboard `{raw_key}` -> `{action}`")
            return
        target_name, target_bucket = target

    for keysym in keysyms:
        normalized_keysym = keysym
        if action == "skip" and keysym in {"K_LCTRL", "K_RCTRL"}:
            normalized_keysym = f"anymod_{keysym}"
        append_unique(target_bucket[target_name], normalized_keysym)
    state.imported.append(f"keyboard `{raw_key}` -> `{action}`")


def ingest_keyboard_bindings(
    state: KeymapBuildState,
    keyconfig: Dict[str, Any],
    action_targets: Dict[str, tuple[str, Dict[str, List[str]]]],
) -> None:
    for raw_key, raw_action in keyconfig.get("key", {}).items():
        action = extract_tyrano_action(raw_action)
        if not action:
            continue
        keysyms = map_tyrano_keyboard_binding(str(raw_key))
        if not keysyms:
            state.deferred.append(f"keyboard `{raw_key}` -> `{action}`")
            continue
        record_keymap_binding(state, action_targets, str(raw_key), action, keysyms)


def ingest_mouse_bindings(state: KeymapBuildState, keyconfig: Dict[str, Any]) -> None:
    right_mouse_action = extract_tyrano_action(keyconfig.get("mouse", {}).get("right"))
    if right_mouse_action == "save":
        append_unique(state.custom_events["tb_show_save"], "mouseup_3")
        state.imported.append("mouse `right` -> `save`")
    elif right_mouse_action:
        state.deferred.append(f"mouse `right` -> `{right_mouse_action}`")

    for mouse_name in ("center", "next", "prev"):
        action = extract_tyrano_action(keyconfig.get("mouse", {}).get(mouse_name))
        if action:
            state.deferred.append(f"mouse `{mouse_name}` -> `{action}`")


def ingest_deferred_categories(state: KeymapBuildState, keyconfig: Dict[str, Any]) -> None:
    for category_name in ("gesture", "gamepad"):
        category = keyconfig.get(category_name, {})
        if category:
            state.deferred.append(f"{category_name} bindings deferred for later design")


def render_keymap_support_functions() -> List[str]:
    return [
        "init python:",
        "    def _tb_add_key(event_name, keysym):",
        "        bindings = config.keymap.setdefault(event_name, [])",
        "        if keysym not in bindings:",
        "            bindings.append(keysym)",
        "",
        "    def _tb_remove_key(event_name, keysym):",
        "        bindings = config.keymap.get(event_name, [])",
        "        if keysym in bindings:",
        "            bindings.remove(keysym)",
        "",
    ]


def render_keymap_event_bindings(state: KeymapBuildState) -> List[str]:
    lines: List[str] = []
    if state.custom_events["tb_show_save"]:
        lines.append('    _tb_remove_key("game_menu", "mouseup_3")')
    for event_name, keysyms in state.builtin_events.items():
        for keysym in keysyms:
            lines.append(f'    _tb_add_key("{event_name}", "{keysym}")')
    for event_name, keysyms in state.custom_events.items():
        for keysym in keysyms:
            lines.append(f'    _tb_add_key("{event_name}", "{keysym}")')
    if any(state.custom_events[event_name] for event_name in state.custom_events):
        lines.extend(
            [
                '    if "tyrano_keymap_router" not in config.overlay_screens:',
                '        config.overlay_screens.append("tyrano_keymap_router")',
            ]
        )
    lines.append("    renpy.clear_keymap_cache()")
    return lines


def render_keymap_router(state: KeymapBuildState) -> List[str]:
    if not any(state.custom_events[event_name] for event_name in state.custom_events):
        return []

    lines = ["", "screen tyrano_keymap_router():"]
    custom_actions = {
        "tb_toggle_auto": 'Preference("auto-forward", "toggle")',
        "tb_show_load": 'ShowMenu("load")',
        "tb_show_history": 'ShowMenu("history")',
        "tb_show_save": 'ShowMenu("save")',
    }
    for event_name, action in custom_actions.items():
        if state.custom_events[event_name]:
            lines.append(f'    key "{event_name}" action {action}')
    return lines


def build_keymap_report(state: KeymapBuildState) -> Dict[str, List[str]]:
    return {
        "imported": state.imported,
        "ignored": state.ignored,
        "deferred": state.deferred,
    }


def build_keymap_rpy(keyconfig: Optional[Dict[str, Any]]) -> tuple[str, Dict[str, List[str]]]:
    state = KeymapBuildState()
    action_targets = build_keymap_action_targets(state)

    if keyconfig is not None:
        ingest_keyboard_bindings(state, keyconfig, action_targets)
        ingest_mouse_bindings(state, keyconfig)
        ingest_deferred_categories(state, keyconfig)

    lines = ["# Generated keymap policy", ""]
    lines.extend(render_keymap_support_functions())
    lines.extend(render_keymap_event_bindings(state))
    lines.extend(render_keymap_router(state))

    lines.append("")
    return "\n".join(lines).rstrip() + "\n", build_keymap_report(state)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Ren'Py project scaffold from a TyranoBuilder project.",
    )
    add_version_argument(parser)
    parser.add_argument("input", type=Path, help="Path to a TyranoBuilder project root")
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Directory to write the generated Ren'Py project scaffold (default: out)",
    )
    parser.add_argument(
        "--entry",
        default=None,
        help="Override the default entry .ks file inside data/scenario",
    )
    return parser.parse_args()


def parse_scalar(raw_value: str) -> Any:
    value = raw_value.strip()
    lowered = value.lower()

    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if re.fullmatch(r"-?\d+", value):
        return int(value)

    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)

    if re.fullmatch(r"[0-9+\-*/ ().]+", value):
        try:
            return int(eval(value, {"__builtins__": {}}, {}))
        except Exception:
            return value

    return value


def parse_config_tjs(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config.tjs not found: {path}")

    settings: Dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith(";") or "=" not in line:
            continue
        key, raw_value = line[1:].split("=", 1)
        settings[key.strip()] = parse_scalar(raw_value)
    return settings


def as_int(settings: Dict[str, Any], key: str, default: int) -> int:
    value = settings.get(key, default)
    return int(value) if isinstance(value, (int, float)) else default


def as_bool(settings: Dict[str, Any], key: str, default: bool) -> bool:
    value = settings.get(key, default)
    return bool(value) if isinstance(value, bool) else default


def normalize_color(value: Any, default: str) -> str:
    if not isinstance(value, str):
        return default
    lowered = value.strip().lower()
    if lowered.startswith("0x"):
        return f"#{lowered[2:]}"
    if lowered.startswith("#"):
        return lowered
    return default


def assumed_font_filename(value: Any, default: str) -> str:
    if not isinstance(value, str):
        return default
    stripped = value.strip()
    if not stripped:
        return default
    if "." in Path(stripped).name:
        return stripped
    return f"{stripped}.ttf"


def sanitize_build_name(value: str) -> str:
    build_name = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return build_name or "ConvertedTyranoProject"


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def field_uses_renpy_fallback(
    field_value: int,
    minimum_safe_value: int,
    maximum_safe_value: int,
) -> bool:
    return not (minimum_safe_value <= field_value <= maximum_safe_value)


def derive_message_layout_from_tyrano_config(settings: Dict[str, Any]) -> Dict[str, Any]:
    screen_width = as_int(settings, "scWidth", 1920)
    screen_height = as_int(settings, "scHeight", 1080)
    default_font_size = as_int(settings, "defaultFontSize", 30)
    textbox_top_padding = as_int(settings, "marginT", 8)
    textbox_bottom_padding = as_int(settings, "marginB", 8)
    tyrano_message_left = as_int(settings, "ml", 16)
    tyrano_message_top = as_int(settings, "mt", 16)
    tyrano_message_width = as_int(settings, "mw", 960)
    tyrano_message_height = as_int(settings, "mh", 640)

    raw_namebox_width = int(max(default_font_size * 6, tyrano_message_width * 0.25))
    raw_namebox_height = int(default_font_size + textbox_top_padding + textbox_bottom_padding + 14)
    raw_dialogue_xpos = tyrano_message_left * 10
    raw_dialogue_width = tyrano_message_width
    raw_name_xpos = tyrano_message_left * 10
    raw_name_ypos = 0
    raw_dialogue_ypos = max(
        tyrano_message_top + raw_namebox_height,
        tyrano_message_top + default_font_size + 28,
    )
    raw_textbox_height = screen_height - (
        tyrano_message_top + tyrano_message_height + textbox_bottom_padding
    )

    maximum_safe_textbox_height = screen_height
    minimum_safe_namebox_width = max(int(default_font_size * 5), 180)
    maximum_safe_namebox_width = int(screen_width * 0.5)
    minimum_safe_namebox_height = default_font_size + textbox_top_padding + 8
    maximum_safe_namebox_height = int(default_font_size * 3.5)
    minimum_safe_dialogue_width = max(int(screen_width * 0.2), default_font_size * 8)
    maximum_safe_dialogue_width = screen_width

    derived = {
        "textbox_height": raw_textbox_height,
        "name_xpos": raw_name_xpos,
        "name_ypos": raw_name_ypos,
        "namebox_width": raw_namebox_width,
        "namebox_height": raw_namebox_height,
        "dialogue_xpos": raw_dialogue_xpos,
        "dialogue_ypos": raw_dialogue_ypos,
        "dialogue_width": raw_dialogue_width,
    }

    fallback_reasons = {
        "textbox_height": raw_textbox_height <= 0
        or raw_textbox_height > maximum_safe_textbox_height,
        "name_xpos": raw_name_xpos < 0 or raw_name_xpos > screen_width,
        "namebox_width": field_uses_renpy_fallback(
            raw_namebox_width,
            minimum_safe_namebox_width,
            maximum_safe_namebox_width,
        ),
        "namebox_height": field_uses_renpy_fallback(
            raw_namebox_height,
            minimum_safe_namebox_height,
            maximum_safe_namebox_height,
        ),
        "dialogue_xpos": raw_dialogue_xpos < 0 or raw_dialogue_xpos > screen_width,
        "dialogue_ypos": raw_dialogue_ypos < 0 or raw_dialogue_ypos > screen_height,
        "dialogue_width": field_uses_renpy_fallback(
            raw_dialogue_width,
            minimum_safe_dialogue_width,
            maximum_safe_dialogue_width,
        ),
    }

    resolved: Dict[str, Any] = {}
    fallbacks: Dict[str, str] = {}
    for key, value in derived.items():
        if fallback_reasons.get(key, False):
            resolved[key] = RENPY_DEFAULT_MESSAGE_LAYOUT[key]
            fallbacks[key] = (
                "fell back to Ren'Py default because the derived value was invalid "
                "for the current screen"
            )
        else:
            resolved[key] = value

    if resolved["namebox_width"] is not None:
        resolved["namebox_width"] = clamp_int(
            int(resolved["namebox_width"]),
            minimum_safe_namebox_width,
            maximum_safe_namebox_width,
        )
    if resolved["namebox_height"] is not None:
        resolved["namebox_height"] = clamp_int(
            int(resolved["namebox_height"]),
            minimum_safe_namebox_height,
            maximum_safe_namebox_height,
        )

    return {
        "raw": derived,
        "resolved": resolved,
        "fallbacks": fallbacks,
    }


def replace_define(content: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count == 0:
        raise RuntimeError(f"Failed to replace template pattern: {pattern}")
    return updated


def resolve_save_directory_timestamp() -> int:
    raw_value = os.environ.get("TB_RENPY_PROJECT_SAVE_TIMESTAMP")
    if raw_value is None:
        return int(time.time())
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            "Environment variable `TB_RENPY_PROJECT_SAVE_TIMESTAMP` must be an integer timestamp."
        ) from exc


def build_gui_values(settings: Dict[str, Any]) -> GuiBuildValues:
    width = as_int(settings, "scWidth", 1920)
    height = as_int(settings, "scHeight", 1080)
    text_size = as_int(settings, "defaultFontSize", 30)
    save_slots = max(as_int(settings, "configSaveSlotNum", 6), 1)
    file_slot_cols = min(3, save_slots)

    return GuiBuildValues(
        width=width,
        height=height,
        text_size=text_size,
        name_text_size=text_size,
        interface_text_size=text_size,
        label_text_size=text_size + 6,
        notify_text_size=max(text_size - 6, 18),
        title_text_size=text_size + 42,
        text_font=assumed_font_filename(settings.get("userFace"), "DejaVuSans.ttf"),
        text_color=normalize_color(settings.get("defaultChColor"), "#ffffff"),
        accent_color=normalize_color(settings.get("defaultLinkColor"), "#9933ff"),
        name_color=DEFAULT_NAME_COLOR,
        history_length=as_int(settings, "maxBackLogNum", 50),
        message_layout=derive_message_layout_from_tyrano_config(settings)["resolved"],
        choice_spacing=max(as_int(settings, "defaultLineSpacing", 8) + 16, 20),
        file_slot_cols=file_slot_cols,
        file_slot_rows=max((save_slots + file_slot_cols - 1) // file_slot_cols, 1),
        quick_menu_background_alpha=as_int(settings, "frameOpacity", 128),
    )


def insert_gui_name_color(content: str, name_color: str) -> str:
    updated_content, count = re.subn(
        r"^(define gui\.hover_color = .*)$",
        lambda match: cast(str, match.group(1)) + f"\ndefine gui.name_color = '{name_color}'",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        raise RuntimeError("Failed to insert gui.name_color in gui.rpy")
    return updated_content


def apply_gui_define_replacements(content: str, values: GuiBuildValues) -> str:
    replacements = (
        (r"gui\.init\([^\)]*\)", f"gui.init({values.width}, {values.height})"),
        (r"^define gui\.accent_color = .*$", f"define gui.accent_color = '{values.accent_color}'"),
        (r"^define gui\.text_color = .*$", f"define gui.text_color = '{values.text_color}'"),
        (
            r"^define gui\.interface_text_color = .*$",
            f"define gui.interface_text_color = '{values.text_color}'",
        ),
        (r"^define gui\.text_font = .*$", f'define gui.text_font = "{values.text_font}"'),
        (
            r"^define gui\.name_text_font = .*$",
            f'define gui.name_text_font = "{values.text_font}"',
        ),
        (
            r"^define gui\.interface_text_font = .*$",
            f'define gui.interface_text_font = "{values.text_font}"',
        ),
        (r"^define gui\.text_size = .*$", f"define gui.text_size = {values.text_size}"),
        (
            r"^define gui\.name_text_size = .*$",
            f"define gui.name_text_size = {values.name_text_size}",
        ),
        (
            r"^define gui\.interface_text_size = .*$",
            f"define gui.interface_text_size = {values.interface_text_size}",
        ),
        (
            r"^define gui\.label_text_size = .*$",
            f"define gui.label_text_size = {values.label_text_size}",
        ),
        (
            r"^define gui\.notify_text_size = .*$",
            f"define gui.notify_text_size = {values.notify_text_size}",
        ),
        (
            r"^define gui\.title_text_size = .*$",
            f"define gui.title_text_size = {values.title_text_size}",
        ),
        (
            r"^define config\.history_length = .*$",
            f"define config.history_length = {values.history_length}",
        ),
        (
            r"^define gui\.textbox_height = .*$",
            f"define gui.textbox_height = {values.message_layout['textbox_height']}",
        ),
        (
            r"^define gui\.name_xpos = .*$",
            f"define gui.name_xpos = {values.message_layout['name_xpos']}",
        ),
        (
            r"^define gui\.name_ypos = .*$",
            f"define gui.name_ypos = {values.message_layout['name_ypos']}",
        ),
        (
            r"^define gui\.namebox_width = .*$",
            "define gui.namebox_width = "
            + (
                "None"
                if values.message_layout["namebox_width"] is None
                else str(values.message_layout["namebox_width"])
            ),
        ),
        (
            r"^define gui\.namebox_height = .*$",
            "define gui.namebox_height = "
            + (
                "None"
                if values.message_layout["namebox_height"] is None
                else str(values.message_layout["namebox_height"])
            ),
        ),
        (
            r"^define gui\.dialogue_xpos = .*$",
            f"define gui.dialogue_xpos = {values.message_layout['dialogue_xpos']}",
        ),
        (
            r"^define gui\.dialogue_ypos = .*$",
            f"define gui.dialogue_ypos = {values.message_layout['dialogue_ypos']}",
        ),
        (
            r"^define gui\.dialogue_width = .*$",
            f"define gui.dialogue_width = {values.message_layout['dialogue_width']}",
        ),
        (
            r"^define gui\.choice_spacing = .*$",
            f"define gui.choice_spacing = {values.choice_spacing}",
        ),
        (
            r"^define gui\.file_slot_cols = .*$",
            f"define gui.file_slot_cols = {values.file_slot_cols}",
        ),
        (
            r"^define gui\.file_slot_rows = .*$",
            f"define gui.file_slot_rows = {values.file_slot_rows}",
        ),
    )

    updated_content = content
    for pattern, replacement in replacements:
        updated_content = replace_define(updated_content, pattern, replacement)
    return updated_content


def insert_gui_custom_block(content: str, values: GuiBuildValues) -> str:
    custom_gui_block = (
        "define gui.choice_ypos = 405\n"
        "define gui.quick_menu_yalign = 1.0\n"
        f"define gui.quick_menu_background_alpha = {values.quick_menu_background_alpha}\n\n\n"
        "## Main and Game Menus"
    )
    return content.replace("## Main and Game Menus", custom_gui_block, 1)


def build_screen_style_values(settings: Dict[str, Any]) -> ScreenStyleValues:
    return ScreenStyleValues(
        default_bold=as_bool(settings, "defaultBold", False),
        default_shadow=as_bool(settings, "defaultShadow", False),
        default_edge=as_bool(settings, "defaultEdge", False),
        shadow_color=normalize_color(settings.get("defaultShadowColor"), "#000000"),
        edge_color=normalize_color(settings.get("defaultEdgeColor"), "#000000"),
    )


def build_say_dialogue_append_lines(values: ScreenStyleValues) -> List[str]:
    lines: List[str] = []
    if values.default_bold:
        lines.append("    bold True")
    if values.default_shadow:
        lines.append("    drop_shadow (1, 1)")
        lines.append(f'    drop_shadow_color "{values.shadow_color}"')
    if values.default_edge:
        lines.append(f'    outlines [(1, "{values.edge_color}", 0, 0)]')
    return lines


def patch_say_dialogue_style(content: str, say_dialogue_append: List[str]) -> str:
    if not say_dialogue_append:
        return content

    updated_content, count = re.subn(
        r"(style say_dialogue:\r?\n(?:.*\r?\n)*?\s+adjust_spacing False)",
        lambda match: cast(str, match.group(1)) + "\n" + "\n".join(say_dialogue_append),
        content,
        count=1,
    )
    if count == 0:
        raise RuntimeError("Failed to patch say_dialogue style block in screens.rpy")
    return updated_content


def patch_quick_menu_yalign(content: str) -> str:
    updated_content, count = re.subn(
        r"(style quick_menu:\r?\n\s+xalign 0\.5\r?\n\s+yalign )1\.0",
        r"\1gui.quick_menu_yalign",
        content,
        count=1,
    )
    if count == 0:
        raise RuntimeError("Failed to patch quick_menu style block in screens.rpy")
    return updated_content


def insert_say_screen_note(content: str) -> str:
    say_screen_note = (
        "screen say(who, what):\n\n"
        "    # Patched from TyranoBuilder config values with a Tyrano-first layout pass.\n"
    )
    return content.replace("screen say(who, what):\n\n", say_screen_note, 1)


def patch_say_label_name_color(content: str) -> str:
    updated_content, count = re.subn(
        r'properties gui\.text_properties\("name", accent=True\)',
        'properties gui.text_properties("name")\n    color gui.name_color',
        content,
        count=1,
    )
    if count == 0:
        raise RuntimeError("Failed to patch say_label name color in screens.rpy")
    return updated_content


def insert_choice_screen_note(content: str) -> str:
    choice_note = (
        "screen choice(items):\n"
        "    # Current builder keeps the Ren'Py choice screen structure, but positions\n"
        "    # and spacing are nudged toward the TyranoBuilder message layout.\n"
    )
    return content.replace("screen choice(items):\n", choice_note, 1)


def build_config_mapping_values(settings: Dict[str, Any]) -> ConfigMappingValues:
    message_layout = derive_message_layout_from_tyrano_config(settings)
    save_slot_count = max(as_int(settings, "configSaveSlotNum", 6), 1)
    save_slot_cols = min(3, save_slot_count)

    return ConfigMappingValues(
        message_layout=message_layout,
        text_cps=max(1, round(1000 / max(as_int(settings, "chSpeed", 30), 1))),
        afm_time=max(0, min(30, round(as_int(settings, "autoSpeed", 1300) / 100))),
        save_slot_count=save_slot_count,
        save_slot_cols=save_slot_cols,
        save_slot_rows=max((save_slot_count + save_slot_cols - 1) // save_slot_cols, 1),
        config_window_mode=(
            "show" if as_bool(settings, "initialMessageLayerVisible", True) else "hide"
        ),
        assumed_font=assumed_font_filename(settings.get("userFace"), "DejaVuSans.ttf"),
        choice_spacing=max(as_int(settings, "defaultLineSpacing", 8) + 16, 20),
    )


def build_config_mapping_rows(
    settings: Dict[str, Any],
    startup_plan: StartupPlan,
    values: ConfigMappingValues,
) -> List[tuple[str, Any, str]]:
    resolved = values.message_layout["resolved"]
    return [
        (
            "global.config_version",
            settings.get("global.config_version"),
            "Metadata only; not used for Ren'Py config.version",
        ),
        ("System.title", settings.get("System.title"), "options.rpy -> config.name"),
        (
            "projectID",
            settings.get("projectID"),
            "options.rpy -> build.name / config.save_directory",
        ),
        ("game_version", settings.get("game_version"), "options.rpy -> config.version"),
        (
            "configVisible",
            settings.get("configVisible"),
            "Reported only for now; not mapped directly to `gui.show_name`",
        ),
        ("scWidth", settings.get("scWidth"), "gui.rpy -> gui.init(width, height)"),
        ("scHeight", settings.get("scHeight"), "gui.rpy -> gui.init(width, height)"),
        ("chSpeed", settings.get("chSpeed"), "options.rpy -> preferences.text_cps (approximate)"),
        (
            "autoSpeed",
            settings.get("autoSpeed"),
            "options.rpy -> preferences.afm_time (approximate)",
        ),
        (
            "maxBackLogNum",
            settings.get("maxBackLogNum"),
            "options.rpy / gui.rpy -> config.history_length",
        ),
        (
            "defaultFontSize",
            settings.get("defaultFontSize"),
            "gui.rpy -> text and interface size defaults",
        ),
        ("userFace", settings.get("userFace"), "gui.rpy -> assumed font filename"),
        ("defaultChColor", settings.get("defaultChColor"), "gui.rpy -> gui.text_color"),
        (
            "speaker name color",
            DEFAULT_NAME_COLOR,
            "gui.rpy / screens.rpy -> gui.name_color (project default)",
        ),
        ("defaultBold", settings.get("defaultBold"), "screens.rpy -> say dialogue bold default"),
        (
            "defaultShadow",
            settings.get("defaultShadow"),
            "screens.rpy -> say dialogue drop shadow default",
        ),
        (
            "defaultEdge",
            settings.get("defaultEdge"),
            "screens.rpy -> say dialogue outlines default",
        ),
        (
            "defaultLinkColor",
            settings.get("defaultLinkColor"),
            "gui.rpy -> gui.accent_color",
        ),
        (
            "KeyConfig.js",
            "partial import",
            "keymap.rpy -> supported safe gameplay bindings only",
        ),
        (
            "configSaveSlotNum",
            settings.get("configSaveSlotNum"),
            "gui.rpy -> file slot rows/cols approximation",
        ),
        (
            "ml / mt / mw / mh",
            (
                f"{settings.get('ml')}, {settings.get('mt')}, "
                f"{settings.get('mw')}, {settings.get('mh')}"
            ),
            "gui.rpy / screens.rpy -> textbox and dialogue area approximation",
        ),
        (
            "derived message layout",
            (
                f"textbox={resolved['textbox_height']}, name_x={resolved['name_xpos']}, "
                f"namebox_w={resolved['namebox_width']}, dialogue_x={resolved['dialogue_xpos']}, "
                f"dialogue_y={resolved['dialogue_ypos']}, dialogue_w={resolved['dialogue_width']}"
            ),
            (
                "gui.rpy / screens.rpy -> Tyrano-first message layout with heuristic "
                "x-offset and invalid-value fallback"
            ),
        ),
        (
            "startup flow",
            startup_plan.note,
            (
                f"script.rpy -> start at `{startup_plan.start_label}`, skip built-in "
                "main menu="
                f"{startup_plan.skip_builtin_main_menu}, splashscreen="
                f"{startup_plan.splashscreen_movie or 'none'}"
            ),
        ),
    ]


def append_config_mapping_notes(
    lines: List[str],
    startup_plan: StartupPlan,
) -> None:
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- These mappings are intentionally conservative and may need manual tuning.",
            (
                "- `game_version` is used for Ren'Py `config.version`; "
                "`global.config_version` is treated as source-engine metadata only."
            ),
            (
                "- `config.save_directory` now uses the sanitized project ID plus a "
                "generation-time timestamp suffix to keep saves distinct, similar "
                "to fresh Ren'Py projects."
            ),
            (
                "- Message geometry now uses a direct Tyrano-style vertical mapping, "
                "plus a heuristic horizontal inset that scales `ml` for Ren'Py's "
                "stock textbox model."
            ),
            "- Font face names are assumed to map to `.ttf` filenames until verified.",
            (
                "- `screens.rpy` is currently generated from the Ren'Py example "
                "baseline with conservative layout and style patching from Tyrano "
                "config values."
            ),
            (
                f"- Speaker names now use a generated `gui.name_color` default of "
                f"`{DEFAULT_NAME_COLOR}` instead of inheriting the GUI accent color."
            ),
            (
                "- KeyConfig.js import is currently partial: Escape remains Ren'Py "
                "menu, right-click can become save in gameplay, and virtual-mouse / "
                "gesture / advanced gamepad mappings remain deferred."
            ),
        ]
    )
    if startup_plan.splashscreen_movie and startup_plan.splashscreen_movie.endswith(".webm"):
        lines.append(
            "- Startup movies sourced from Tyrano `.mp4`/`.m4v` files now prefer "
            "a Ren'Py `.webm` target path. Run `prepare_movies_for_renpy.py` "
            "before testing splashscreen playback."
        )


def append_message_layout_section(
    lines: List[str],
    settings: Dict[str, Any],
    values: ConfigMappingValues,
) -> None:
    resolved = values.message_layout["resolved"]
    raw = values.message_layout["raw"]
    lines.extend(
        [
            "",
            "## Message Layout Translation",
            "",
            (
                "The builder now keeps Tyrano message geometry much closer to a "
                "1-to-1 port without replacing Ren'Py's stock say screen."
            ),
            (
                "Vertical sizing follows Tyrano message bounds more directly, while "
                "horizontal inset uses a simple heuristic scale so the text lands "
                "closer to the original visual position inside Ren'Py's textbox."
            ),
            "",
            "### Tyrano Inputs Used",
            "",
            f"- `ml` = `{settings.get('ml')}` -> left edge of the Tyrano message text area",
            f"- `mt` = `{settings.get('mt')}` -> top edge of the Tyrano message text area",
            f"- `mw` = `{settings.get('mw')}` -> width of the Tyrano message text area",
            f"- `mh` = `{settings.get('mh')}` -> height of the Tyrano message text area",
            (
                f"- `defaultFontSize` = `{settings.get('defaultFontSize')}` -> used "
                "to estimate namebox size and spacing"
            ),
            (
                f"- `marginT` / `marginB` = `{settings.get('marginT')}` / "
                f"`{settings.get('marginB')}` -> used as textbox padding hints"
            ),
            "",
            "### Translation Rules",
            "",
            (
                "- `dialogue_xpos` now uses `ml * 10` as a practical Ren'Py inset "
                "heuristic so the text lands closer to the Tyrano look inside the "
                "stock textbox"
            ),
            (
                "- `name_xpos` uses the same `ml * 10` heuristic so speaker names "
                "stay aligned with dialogue text"
            ),
            (
                "- `dialogue_width` now follows Tyrano `mw` directly unless it "
                "becomes invalid for the current screen width"
            ),
            (
                "- `namebox_width` is derived from both font size and message width "
                "so the speaker name has room without dominating the textbox"
            ),
            (
                "- `dialogue_ypos` is pushed below the derived namebox height so "
                "dialogue does not overlap the speaker name"
            ),
            (
                "- `textbox_height` now comes from `scHeight - (mt + mh + marginB)` "
                "so the bottom-aligned Ren'Py textbox starts where the Tyrano "
                "message region ends"
            ),
            "",
            "### Raw vs Final Message Layout",
            "",
            "| Field | Derived From Tyrano | Final Generated Value |",
            "| --- | --- | --- |",
            f"| `textbox_height` | `{raw['textbox_height']}` | `{resolved['textbox_height']}` |",
            f"| `name_xpos` | `{raw['name_xpos']}` | `{resolved['name_xpos']}` |",
            f"| `name_ypos` | `{raw['name_ypos']}` | `{resolved['name_ypos']}` |",
            f"| `namebox_width` | `{raw['namebox_width']}` | `{resolved['namebox_width']}` |",
            f"| `namebox_height` | `{raw['namebox_height']}` | `{resolved['namebox_height']}` |",
            f"| `dialogue_xpos` | `{raw['dialogue_xpos']}` | `{resolved['dialogue_xpos']}` |",
            f"| `dialogue_ypos` | `{raw['dialogue_ypos']}` | `{resolved['dialogue_ypos']}` |",
            f"| `dialogue_width` | `{raw['dialogue_width']}` | `{resolved['dialogue_width']}` |",
        ]
    )


def append_other_derived_mappings(
    lines: List[str],
    settings: Dict[str, Any],
    startup_plan: StartupPlan,
    values: ConfigMappingValues,
) -> None:
    resolved = values.message_layout["resolved"]
    lines.extend(
        [
            "",
            "## Other Derived Mappings",
            "",
            "| Area | Tyrano Input | Ren'Py Output | Confidence | Notes |",
            "| --- | --- | --- | --- | --- |",
            (
                f"| Text speed | `chSpeed={settings.get('chSpeed')}` | "
                f"`preferences.text_cps={values.text_cps}` | `heuristic` | "
                "Converts Tyrano character speed into an approximate "
                "characters-per-second value. |"
            ),
            (
                f"| Auto speed | `autoSpeed={settings.get('autoSpeed')}` | "
                f"`preferences.afm_time={values.afm_time}` | `heuristic` | "
                "Converts Tyrano auto speed into an approximate Ren'Py "
                "auto-forward delay. |"
            ),
            (
                "| Save layout | "
                f"`configSaveSlotNum={settings.get('configSaveSlotNum')}` | "
                f"`gui.file_slot_cols={values.save_slot_cols}`, "
                f"`gui.file_slot_rows={values.save_slot_rows}` | `heuristic` | "
                "Builds a simple grid layout from the total number of save slots. |"
            ),
            (
                "| Window visibility | "
                f"`initialMessageLayerVisible={settings.get('initialMessageLayerVisible')}` | "
                f'`config.window="{values.config_window_mode}"` | `translated` | '
                "Uses initial Tyrano message-layer visibility to choose a safe "
                "Ren'Py window mode. |"
            ),
            (
                f"| Font face | `userFace={settings.get('userFace')}` | "
                f'`gui.text_font="{values.assumed_font}"` | `heuristic` | '
                "Assumes the Tyrano face name maps to a `.ttf` filename that the "
                "user must verify. |"
            ),
            (
                "| Speaker name color | `no Tyrano name-color setting found` | "
                f'`gui.name_color="{DEFAULT_NAME_COLOR}"` | `fallback` | '
                "Uses a clean default speaker-name color instead of tying names "
                "to Ren'Py accent/link color. |"
            ),
            (
                "| KeyConfig.js import | `system key map` | `game/keymap.rpy` | "
                "`translated` | Imports only safe bindings now: keeps Escape on "
                "menu, allows right-click save, and defers virtual mouse, gesture, "
                "and advanced gamepad behavior. |"
            ),
            (
                f"| Horizontal text inset | `ml={settings.get('ml')}` | "
                f"`gui.dialogue_xpos={resolved['dialogue_xpos']}`, "
                f"`gui.name_xpos={resolved['name_xpos']}` | `heuristic` | "
                "Multiplies Tyrano `ml` by 10 so text and speaker names land "
                "closer to the Tyrano layout inside Ren'Py's stock textbox. |"
            ),
            (
                "| Choice spacing | "
                f"`defaultLineSpacing={settings.get('defaultLineSpacing')}` | "
                f"`gui.choice_spacing={values.choice_spacing}` | `heuristic` | "
                "Uses line spacing as a rough input for menu choice spacing. |"
            ),
            (
                "| Dialogue font styling | "
                f"`defaultBold={settings.get('defaultBold')}`, "
                f"`defaultShadow={settings.get('defaultShadow')}`, "
                f"`defaultEdge={settings.get('defaultEdge')}` | "
                "`screens.rpy` say style patch | `translated` | Applies safe "
                "default styling to dialogue text in the generated say screen. |"
            ),
            (
                "| Startup flow | `entry scenario` | `script.rpy` startup handoff | "
                f"`{startup_plan.confidence}` | {startup_plan.note} |"
            ),
        ]
    )


def append_keyconfig_report(lines: List[str], keymap_report: Dict[str, List[str]]) -> None:
    if not any(keymap_report.values()):
        return
    lines.extend(["", "## KeyConfig Import", ""])
    if keymap_report["imported"]:
        lines.append("### Imported Now")
        lines.extend(f"- {item}" for item in keymap_report["imported"])
        lines.append("")
    if keymap_report["ignored"]:
        lines.append("### Intentionally Ignored")
        lines.extend(f"- {item}" for item in keymap_report["ignored"])
        lines.append("")
    if keymap_report["deferred"]:
        lines.append("### Deferred")
        lines.extend(f"- {item}" for item in keymap_report["deferred"])
        lines.append("")


def append_message_layout_fallbacks(lines: List[str], fallbacks: Dict[str, str]) -> None:
    if not fallbacks:
        return
    lines.extend(["", "## Message Layout Fallbacks", ""])
    for key in sorted(fallbacks):
        lines.append(f"- `{key}`: {fallbacks[key]}")


def build_options_rpy(template: str, settings: Dict[str, Any]) -> str:
    project_title = str(
        settings.get("System.title")
        or settings.get("projectID")
        or "Converted TyranoBuilder Project"
    )
    project_id = str(settings.get("projectID") or sanitize_build_name(project_title))
    version = str(settings.get("game_version") or "0.0")
    source_config_version = str(settings.get("global.config_version") or "unknown")
    build_name = sanitize_build_name(project_id)
    save_directory = f"{build_name}-{resolve_save_directory_timestamp()}"
    text_cps = max(1, round(1000 / max(as_int(settings, "chSpeed", 30), 1)))
    afm_time = max(0, min(30, round(as_int(settings, "autoSpeed", 1300) / 100)))
    history_length = as_int(settings, "maxBackLogNum", 50)
    has_music = True
    has_sound = True
    has_voice = False
    default_music_volume = as_int(settings, "defaultBgmVolume", 100) / 100.0
    default_sound_volume = as_int(settings, "defaultSeVolume", 100) / 100.0
    config_window_mode = "show" if as_bool(settings, "initialMessageLayerVisible", True) else "hide"

    content = template
    content = replace_define(
        content, r"^define config\.name = .*$", f'define config.name = _("{project_title}")'
    )
    content = replace_define(
        content, r"^define config\.version = .*$", f'define config.version = "{version}"'
    )
    content = replace_define(
        content, r"^define build\.name = .*$", f'define build.name = "{build_name}"'
    )
    content = replace_define(
        content, r"^define config\.has_sound = .*$", f"define config.has_sound = {str(has_sound)}"
    )
    content = replace_define(
        content, r"^define config\.has_music = .*$", f"define config.has_music = {str(has_music)}"
    )
    content = replace_define(
        content, r"^define config\.has_voice = .*$", f"define config.has_voice = {str(has_voice)}"
    )
    content = replace_define(
        content, r"^define config\.window = .*$", f'define config.window = "{config_window_mode}"'
    )
    content = replace_define(
        content,
        r"^default preferences\.text_cps = .*$",
        f"default preferences.text_cps = {text_cps}",
    )
    content = replace_define(
        content,
        r"^default preferences\.afm_time = .*$",
        f"default preferences.afm_time = {afm_time}",
    )
    content = replace_define(
        content,
        r"^define config\.save_directory = .*$",
        f'define config.save_directory = "{save_directory}"',
    )

    version_block = (
        f'define config.version = "{version}"\n'
        f"# Source Tyrano config version: {source_config_version}"
    )
    content = content.replace(f'define config.version = "{version}"', version_block, 1)

    history_block = (
        f"define config.history_length = {history_length}\n"
        "default preferences.skip_unseen = True\n"
        f"default preferences.music_volume = {default_music_volume:.2f}\n"
        f"default preferences.sound_volume = {default_sound_volume:.2f}\n"
        f"# Source Tyrano movie volume default: "
        f"{as_int(settings, 'defaultMovieVolume', 100)}\n\n\n## Save directory"
    )
    content = content.replace("## Save directory", history_block, 1)
    return content


def build_gui_rpy(template: str, settings: Dict[str, Any]) -> str:
    values = build_gui_values(settings)
    content = apply_gui_define_replacements(template, values)
    content = insert_gui_name_color(content, values.name_color)
    return insert_gui_custom_block(content, values)


def build_screens_rpy(template: str, settings: Dict[str, Any]) -> str:
    style_values = build_screen_style_values(settings)
    content = template.replace("ypos 405", "ypos gui.choice_ypos", 1)
    content = patch_say_dialogue_style(content, build_say_dialogue_append_lines(style_values))
    content = patch_quick_menu_yalign(content)
    content = insert_say_screen_note(content)
    content = patch_say_label_name_color(content)
    return insert_choice_screen_note(content)


def ensure_asset_directories(game_dir: Path) -> List[Path]:
    created: List[Path] = []
    for relative_path in ASSET_DIRECTORIES:
        directory = game_dir / relative_path
        directory.mkdir(parents=True, exist_ok=True)
        created.append(directory)
    return created


def infer_media_target_path(bucket: str, source_value: str) -> str:
    if bucket == "backgrounds":
        return remap_background_storage(source_value)
    if bucket == "character_sprites":
        return remap_character_storage(source_value)
    if bucket == "bgm":
        return remap_audio_storage(source_value, "music")
    if bucket == "sfx":
        return remap_audio_storage(source_value, "sound")
    if bucket == "movies":
        return preferred_renpy_movie_path(source_value)
    if bucket == "fonts":
        filename = (
            Path(source_value).name if "." in Path(source_value).name else source_value + ".ttf"
        )
        return f"fonts/{filename}"
    if bucket == "other_file_references":
        suffix = Path(source_value).suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            return f"images/ui/{Path(source_value).name}"
        if suffix in {".mp3", ".ogg", ".wav", ".m4a"}:
            return remap_audio_storage(source_value, "sound")
        if suffix in {".mp4", ".m4v", ".webm", ".ogv"}:
            return preferred_renpy_movie_path(source_value)
    return source_value


def merge_inventory(paths: Iterable[Path]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    combined: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for path in paths:
        inventory = extract_inventory(path)
        for bucket, items in inventory.items():
            bucket_target = combined.setdefault(bucket, {})
            for value, item in items.items():
                entry = bucket_target.setdefault(
                    value,
                    {
                        "count": 0,
                        "sources": [],
                        "tags": [],
                        "target_path": infer_media_target_path(bucket, value),
                    },
                )
                entry["count"] += item.count
                source_marker = f"{path.name}:{','.join(str(line) for line in item.line_numbers)}"
                if source_marker not in entry["sources"]:
                    entry["sources"].append(source_marker)
                for tag in sorted(item.tags):
                    if tag not in entry["tags"]:
                        entry["tags"].append(tag)
    return combined


def render_needed_media_markdown(inventory: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
    section_labels = [
        ("backgrounds", "Backgrounds"),
        ("character_sprites", "Character Sprites"),
        ("bgm", "BGM"),
        ("sfx", "SFX"),
        ("movies", "Movies"),
        ("fonts", "Fonts / Faces"),
        ("other_file_references", "Other File References"),
    ]
    lines = [
        "# Needed Media",
        "",
        "Reachable media references extracted from the traversed scenario set.",
        "",
    ]
    for key, title in section_labels:
        lines.append(f"## {title}")
        lines.append("")
        items = inventory.get(key, {})
        if not items:
            lines.append("- None found")
            lines.append("")
            continue
        for value in sorted(items, key=str.lower):
            entry = items[value]
            lines.append(
                f"- `{value}` -> `game/{entry['target_path']}` (used {entry['count']} times)"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_asset_plan_markdown(inventory: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
    lines = [
        "# Asset Migration Plan",
        "",
        "The builder created the target directories below, but it did not copy assets yet.",
        "Use this plan to move or verify files before testing the generated Ren'Py project.",
        "",
        "## Suggested Directories",
        "",
    ]
    for relative_path in ASSET_DIRECTORIES:
        lines.append(f"- `game/{relative_path}/`")
    lines.extend(
        [
            "",
            "## Category Hints",
            "",
            "- Backgrounds -> `game/images/backgrounds/`",
            "- Character sprites -> `game/images/character/`",
            (
                "- UI/button/title/config art -> `game/images/ui/` or `game/gui/` "
                "depending on how you want to organize Ren'Py assets"
            ),
            "- BGM -> `game/audio/bgm/`",
            "- SFX -> `game/audio/sfx/`",
            "- Movies -> `game/movies/`",
            "- Fonts -> `game/fonts/`",
            "",
            "## Current Reachable Counts",
            "",
        ]
    )
    for key, label in [
        ("backgrounds", "Backgrounds"),
        ("character_sprites", "Character sprites"),
        ("bgm", "BGM"),
        ("sfx", "SFX"),
        ("movies", "Movies"),
        ("fonts", "Fonts / faces"),
    ]:
        lines.append(f"- {label}: {len(inventory.get(key, {}))}")
    return "\n".join(lines).rstrip() + "\n"


def render_config_mapping_markdown(
    settings: Dict[str, Any],
    startup_plan: StartupPlan,
    keymap_report: Dict[str, List[str]],
) -> str:
    values = build_config_mapping_values(settings)
    mapped_rows = build_config_mapping_rows(settings, startup_plan, values)
    lines = [
        "# Project Config Mapping",
        "",
        (
            "Values extracted from `data/system/Config.tjs` and mapped into "
            "generated Ren'Py project files."
        ),
        "",
        "| Tyrano Key | Value | Generated Target |",
        "| --- | --- | --- |",
    ]
    for key, value, target in mapped_rows:
        lines.append(f"| `{key}` | `{value}` | `{target}` |")
    append_config_mapping_notes(lines, startup_plan)
    append_message_layout_section(lines, settings, values)
    append_other_derived_mappings(lines, settings, startup_plan, values)
    append_keyconfig_report(lines, keymap_report)
    append_message_layout_fallbacks(lines, values.message_layout["fallbacks"])
    return "\n".join(lines).rstrip() + "\n"


def build_startup_script(startup_plan: StartupPlan) -> str:
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


def load_template(project_root: Path, relative_path: str) -> str:
    template_path = project_root / relative_path
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    return template_path.read_text(encoding="utf-8-sig")


def write_project_files(
    game_dir: Path,
    project_root: Path,
    settings: Dict[str, Any],
    startup_plan: StartupPlan,
    keyconfig: Optional[Dict[str, Any]],
) -> List[Path]:
    options_template = load_template(project_root, "examples/RenpyDefaultGame/game/options.rpy")
    gui_template = load_template(project_root, "examples/RenpyDefaultGame/game/gui.rpy")
    screens_template = load_template(project_root, "examples/RenpyDefaultGame/game/screens.rpy")

    options_path = game_dir / "options.rpy"
    options_path.write_text(build_options_rpy(options_template, settings), encoding="utf-8")

    gui_path = game_dir / "gui.rpy"
    gui_path.write_text(build_gui_rpy(gui_template, settings), encoding="utf-8")

    screens_path = game_dir / "screens.rpy"
    screens_path.write_text(build_screens_rpy(screens_template, settings), encoding="utf-8")

    script_path = game_dir / "script.rpy"
    script_path.write_text(build_startup_script(startup_plan), encoding="utf-8")

    keymap_path = game_dir / "keymap.rpy"
    keymap_content, _ = build_keymap_rpy(keyconfig)
    keymap_path.write_text(keymap_content, encoding="utf-8")

    return [options_path, gui_path, screens_path, script_path, keymap_path]


def build_project(input_path: Path, output_dir: Path, explicit_entry: Optional[str]) -> List[Path]:
    project_root = input_path.resolve()
    scenario_dir = resolve_scenario_dir(input_path)
    entry_file = resolve_entry_file(scenario_dir, explicit_entry).resolve()
    reachable_files, traversal_warnings = discover_reachable_files(scenario_dir, entry_file)
    output_name_map = build_output_name_map(reachable_files)

    warning_map: Dict[Path, List[Any]] = {}
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
    written_paths = write_outputs(parsed_files, entry_parsed_file, output_dir)

    game_dir = output_dir / PROJECT_OUTPUT_DIRNAME
    created_dirs = ensure_asset_directories(game_dir)

    config_path = project_root / "data" / "system" / "Config.tjs"
    settings = parse_config_tjs(config_path)
    keyconfig = parse_keyconfig_js(project_root / "data" / "system" / "KeyConfig.js")
    startup_plan = determine_startup_plan(parsed_files, entry_parsed_file)
    _, keymap_report = build_keymap_rpy(keyconfig)
    written_paths.extend(
        write_project_files(game_dir, REPOSITORY_ROOT, settings, startup_plan, keyconfig)
    )

    inventory = merge_inventory(reachable_files)
    media_doc_path = game_dir / "NEEDED_MEDIA.md"
    media_doc_path.write_text(render_needed_media_markdown(inventory), encoding="utf-8")
    written_paths.append(media_doc_path)

    media_raw_path = game_dir / "NEEDED_MEDIA_RAW.json"
    media_raw_path.write_text(json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")
    written_paths.append(media_raw_path)

    asset_plan_path = game_dir / "ASSET_MIGRATION_PLAN.md"
    asset_plan_path.write_text(render_asset_plan_markdown(inventory), encoding="utf-8")
    written_paths.append(asset_plan_path)

    config_mapping_path = game_dir / "PROJECT_CONFIG_MAPPING.md"
    config_mapping_path.write_text(
        render_config_mapping_markdown(settings, startup_plan, keymap_report),
        encoding="utf-8",
    )
    written_paths.append(config_mapping_path)

    scaffold_doc_path = game_dir / "DIRECTORY_SCAFFOLD.md"
    scaffold_doc_path.write_text(
        "# Directory Scaffold\n\n"
        "These empty directories were created for future manual or automated asset migration.\n\n"
        + "\n".join(f"- `game/{path.relative_to(game_dir)}/`" for path in created_dirs)
        + "\n",
        encoding="utf-8",
    )
    written_paths.append(scaffold_doc_path)

    return written_paths


def main() -> None:
    args = parse_args()
    written_paths = build_project(args.input, args.out_dir, args.entry)
    print("Wrote outputs:")
    for written_path in written_paths:
        print(f"- {written_path}")


if __name__ == "__main__":
    main()
