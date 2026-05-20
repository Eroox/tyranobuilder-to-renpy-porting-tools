from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from tyrano_tools.ks.io import read_ks_lines
from tyrano_tools.ks.tags import parse_bracket_tag_line

TAGGED_CHARACTER_TAGS = {
    "chara_show",
    "chara_mod",
    "chara_hide",
    "chara_hide_all",
    "chara_new",
    "chara_move",
    "chara_face",
    "chara_part",
    "fuki_chara",
}

BACKGROUND_TAGS = {"bg", "bg2"}
SPRITE_TAGS = {"chara_show", "chara_mod", "chara_new", "chara_face", "chara_part"}
BGM_TAGS = {"playbgm", "fadeinbgm", "xchgbgm"}
SFX_TAGS = {"playse", "fadeinse"}
MOVIE_TAGS = {"movie", "bgmovie"}
REFERENCED_KS_TAGS = {"jump", "call"}
SYSTEM_KS_TAGS = {"_tb_system_call"}
FONT_FACE_TAGS = {"font", "deffont"}


@dataclass
class InventoryItem:
    value: str
    tags: set[str] = field(default_factory=set)
    line_numbers: list[int] = field(default_factory=list)

    def add_reference(self, tag: str, line_number: int) -> None:
        self.tags.add(tag)
        self.line_numbers.append(line_number)

    @property
    def count(self) -> int:
        return len(self.line_numbers)


InventoryBucket = dict[str, InventoryItem]


def add_item(bucket: InventoryBucket, value: str, tag: str, line_number: int) -> None:
    cleaned_value = value.strip()
    if not cleaned_value:
        return

    item = bucket.setdefault(cleaned_value, InventoryItem(value=cleaned_value))
    item.add_reference(tag, line_number)


def build_inventory() -> dict[str, InventoryBucket]:
    return {
        "tagged_characters": {},
        "speaker_labels": {},
        "character_sprites": {},
        "backgrounds": {},
        "bgm": {},
        "sfx": {},
        "movies": {},
        "referenced_ks": {},
        "system_ks": {},
        "fonts": {},
        "other_file_references": {},
    }


def categorize_storage_reference(tag: str, storage: str) -> str:
    if tag in BACKGROUND_TAGS:
        return "backgrounds"
    if tag in SPRITE_TAGS:
        return "character_sprites"
    if tag in BGM_TAGS:
        return "bgm"
    if tag in SFX_TAGS:
        return "sfx"
    if tag in MOVIE_TAGS:
        return "movies"
    if tag in REFERENCED_KS_TAGS:
        return "referenced_ks"
    if tag in SYSTEM_KS_TAGS:
        return "system_ks"

    suffix = Path(storage).suffix.lower()
    if suffix == ".ks":
        return "other_file_references"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return "other_file_references"
    if suffix in {".mp3", ".ogg", ".wav", ".m4a"}:
        return "other_file_references"
    if suffix in {".mp4", ".webm"}:
        return "other_file_references"
    return "other_file_references"


def extract_inventory(path: Path) -> dict[str, InventoryBucket]:
    inventory = build_inventory()
    in_text_block = False

    for line_number, raw_line in enumerate(read_ks_lines(path), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        tag_info = parse_bracket_tag_line(stripped)
        if tag_info:
            tag, attrs = tag_info

            if tag == "tb_start_text":
                in_text_block = True
                continue
            if tag == "_tb_end_text":
                in_text_block = False
                continue

            if tag in TAGGED_CHARACTER_TAGS and "name" in attrs:
                add_item(inventory["tagged_characters"], attrs["name"], tag, line_number)

            if tag in FONT_FACE_TAGS and "face" in attrs:
                add_item(inventory["fonts"], attrs["face"], tag, line_number)

            storage = attrs.get("storage")
            if storage:
                bucket_name = categorize_storage_reference(tag, storage)
                add_item(inventory[bucket_name], storage, tag, line_number)

            continue

        if in_text_block and stripped.startswith("#"):
            speaker = stripped.lstrip("#").strip() or "NARRATION"
            add_item(inventory["speaker_labels"], speaker, "speaker", line_number)

    return inventory


def format_item_line(
    item: InventoryItem,
    include_counts: bool,
    include_line_numbers: bool,
) -> str:
    line = f"- `{item.value}`"
    details: list[str] = []

    if include_counts:
        suffix = "time" if item.count == 1 else "times"
        details.append(f"used {item.count} {suffix}")

    if include_line_numbers:
        joined_lines = ", ".join(str(number) for number in item.line_numbers)
        details.append(f"lines: {joined_lines}")

    if details:
        line = f"{line} ({'; '.join(details)})"

    return line


def render_section(
    title: str,
    bucket: InventoryBucket,
    include_counts: bool,
    include_line_numbers: bool,
) -> list[str]:
    lines = [f"## {title}", ""]

    if not bucket:
        lines.append("- None found")
        lines.append("")
        return lines

    for key in sorted(bucket, key=str.lower):
        lines.append(format_item_line(bucket[key], include_counts, include_line_numbers))

    lines.append("")
    return lines


def render_inventory_markdown(
    input_path: Path,
    inventory: dict[str, InventoryBucket],
    include_counts: bool,
    include_line_numbers: bool,
) -> str:
    lines: list[str] = ["# ALL_MEDIA", "", f"Source: `{input_path.name}`", ""]

    if not include_counts and not include_line_numbers:
        detail_mode = "Deduped inventory only"
    elif include_counts and include_line_numbers:
        detail_mode = "Includes usage counts and line numbers"
    elif include_counts:
        detail_mode = "Includes usage counts"
    else:
        detail_mode = "Includes line numbers"

    lines.append(f"Detail mode: {detail_mode}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")

    summary_items = [
        ("Tagged characters", "tagged_characters"),
        ("Speaker labels", "speaker_labels"),
        ("Character sprites", "character_sprites"),
        ("Backgrounds", "backgrounds"),
        ("BGM", "bgm"),
        ("SFX", "sfx"),
        ("Movies", "movies"),
        ("Referenced KS files", "referenced_ks"),
        ("System KS files", "system_ks"),
        ("Fonts / named faces", "fonts"),
        ("Other file references", "other_file_references"),
    ]

    for label, key in summary_items:
        lines.append(f"- {label}: {len(inventory[key])}")

    lines.append("")
    section_specs = [
        ("Characters (Tagged)", "tagged_characters"),
        ("Speaker Labels", "speaker_labels"),
        ("Character Sprites", "character_sprites"),
        ("Backgrounds", "backgrounds"),
        ("BGM", "bgm"),
        ("SFX", "sfx"),
        ("Movies", "movies"),
        ("Referenced KS Files", "referenced_ks"),
        ("System KS Files", "system_ks"),
        ("Fonts / Named Faces", "fonts"),
        ("Other File References", "other_file_references"),
    ]

    for title, key in section_specs:
        lines.extend(render_section(title, inventory[key], include_counts, include_line_numbers))

    return "\n".join(lines).rstrip() + "\n"
