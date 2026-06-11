from __future__ import annotations

import hashlib
import re
from pathlib import Path


def normalize_identifier(value: str, prefix: str = "id") -> str:
    # function lowercases ``value``, replaces any non-ASCII-alphanumeric
    # run with a single underscore, and trims leading/trailing underscores.
    # When the resulting slug is empty a deterministic suffix
    # derived from the SHA-1 hash of the original stripped input is appended
    #   to ``prefix`` to form a distinct identifier.
    stripped_value = value.strip()
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", stripped_value.lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        # Input had no ASCII alphanumerics. Without a deterministic suffix
        # every such input would collapse to ``prefix`` and collide with
        # every other non-ASCII input that shares the prefix.
        digest = hashlib.sha1(stripped_value.encode("utf-8")).hexdigest()[:8]
        normalized = f"{prefix}_{digest}"
    if normalized.startswith("00"):
        normalized = f"{prefix}_{normalized}"
    if not normalized[0].isalnum():
        normalized = f"{prefix}_{normalized}"
    if normalized[0].isdigit():
        normalized = f"n_{normalized}"
    return normalized


def escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def normalize_font_face(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() == "default":
        return None
    if "." in Path(stripped).name:
        return f"fonts/{stripped}"
    return f"fonts/{stripped}.ttf"


def remap_background_storage(storage: str) -> str:
    return f"images/backgrounds/{Path(storage).name}"


def remap_character_storage(storage: str) -> str:
    storage_path = Path(storage)
    parts = list(storage_path.parts)
    if parts and parts[0].lower() == "chara":
        parts = parts[1:]
    relative_path = Path(*parts) if parts else Path(storage_path.name)
    return str(Path("images") / "character" / relative_path).replace("\\", "/")


def remap_audio_storage(storage: str, channel: str) -> str:
    filename = Path(storage).name
    audio_subdir = "bgm" if channel == "music" else "sfx"
    return f"audio/{audio_subdir}/{filename}"


def remap_movie_storage(storage: str) -> str:
    return f"movies/{Path(storage).name}"
