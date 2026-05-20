from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from tyrano_tools.renpy.paths import normalize_identifier

if TYPE_CHECKING:
    from tyrano_tools.scenario.shared import WarningRecord


@dataclass
class StartupPlan:
    start_label: str
    skip_builtin_main_menu: bool
    splashscreen_movie: str | None
    confidence: str
    note: str
    warnings: list[WarningRecord] = field(default_factory=list)
    promoted_movie_source: tuple[Path, int] | None = None


def preferred_renpy_movie_path(source_value: str) -> str:
    source_path = Path(source_value)
    if source_path.suffix.lower() in {".mp4", ".m4v"}:
        return f"movies/{source_path.with_suffix('.webm').name}"
    return f"movies/{source_path.name}"


def build_output_name_map(paths: Sequence[Path]) -> dict[Path, str]:
    counts: dict[str, int] = {}
    output_names: dict[Path, str] = {}
    for path in sorted(paths, key=lambda item: item.as_posix().lower()):
        base_name = normalize_identifier(path.stem, prefix="scene")
        count = counts.get(base_name, 0) + 1
        counts[base_name] = count
        resolved_name = base_name if count == 1 else f"{base_name}_{count}"
        output_names[path] = f"{resolved_name}.rpy"
    return output_names
