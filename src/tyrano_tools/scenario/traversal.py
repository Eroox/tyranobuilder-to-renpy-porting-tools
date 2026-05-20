from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

from tyrano_tools.ks.io import read_ks_lines
from tyrano_tools.ks.tags import parse_tyrano_tag_line
from tyrano_tools.scenario.shared import WarningRecord

TRAVERSAL_TAGS = {"jump", "call", "button", "link", "glink", "clickable"}
DEFAULT_EXCLUDED_FILES = {"config.ks", "make.ks"}


@dataclass
class TraversalReference:
    source_path: Path
    line_number: int
    tag_name: str
    storage: str | None
    target_label: str | None


def resolve_scenario_dir(input_path: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() != ".ks":
            raise RuntimeError(
                f"Expected a .ks file, project root, or scenario directory: {input_path}"
            )
        return input_path.parent

    if input_path.name == "scenario":
        return input_path

    scenario_dir = input_path / "data" / "scenario"
    if scenario_dir.exists() and scenario_dir.is_dir():
        return scenario_dir

    raise RuntimeError(
        f"Could not find a TyranoBuilder scenario directory from input: {input_path}"
    )


def resolve_entry_file(scenario_dir: Path, explicit_entry: str | None) -> Path:
    if explicit_entry:
        candidate = scenario_dir / explicit_entry
        if not candidate.exists():
            raise FileNotFoundError(f"Entry file not found in scenario directory: {candidate}")
        return candidate

    first_path = scenario_dir / "first.ks"
    if first_path.exists():
        return first_path

    candidates = sorted(scenario_dir.glob("*.ks"))
    if not candidates:
        raise RuntimeError(f"No .ks files found in scenario directory: {scenario_dir}")
    return candidates[0]


def is_system_storage(storage: str | None) -> bool:
    if not storage:
        return False
    normalized = storage.replace("\\", "/")
    return normalized.startswith("system/")


def resolve_storage_path(base_path: Path, storage: str | None) -> Path | None:
    if not storage:
        return None
    return (base_path.parent / storage).resolve()


def scan_references(path: Path) -> list[TraversalReference]:
    references: list[TraversalReference] = []
    for line_number, raw_line in enumerate(read_ks_lines(path), start=1):
        tag_info = parse_tyrano_tag_line(raw_line.strip())
        if not tag_info:
            continue
        tag_name, attrs = tag_info
        if tag_name not in TRAVERSAL_TAGS:
            continue
        references.append(
            TraversalReference(
                source_path=path,
                line_number=line_number,
                tag_name=tag_name,
                storage=attrs.get("storage"),
                target_label=attrs.get("target"),
            )
        )
    return references


def discover_reachable_files(
    scenario_dir: Path,
    entry_file: Path,
) -> tuple[list[Path], list[WarningRecord]]:
    reachable: list[Path] = []
    warnings: list[WarningRecord] = []
    queue: deque[Path] = deque([entry_file.resolve()])
    seen: set[Path] = set()
    scenario_files = {path.resolve() for path in scenario_dir.glob("*.ks")}

    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        reachable.append(current)

        for ref in scan_references(current):
            if is_system_storage(ref.storage):
                warnings.append(
                    WarningRecord(
                        source_path=ref.source_path,
                        line_number=ref.line_number,
                        category="skipped_system_reference",
                        message=(
                            f"Skipped traversal into system reference: storage=`{ref.storage}`."
                        ),
                    )
                )
                continue

            if not ref.storage:
                continue

            target_path = resolve_storage_path(ref.source_path, ref.storage)
            if target_path is None:
                continue
            if target_path not in scenario_files:
                warnings.append(
                    WarningRecord(
                        source_path=ref.source_path,
                        line_number=ref.line_number,
                        category="unresolved_traversal_reference",
                        message=(
                            "Traversal reference points outside the known scenario set: "
                            f"storage=`{ref.storage}`."
                        ),
                    )
                )
                continue

            if target_path.name in DEFAULT_EXCLUDED_FILES and target_path != entry_file.resolve():
                warnings.append(
                    WarningRecord(
                        source_path=ref.source_path,
                        line_number=ref.line_number,
                        category="excluded_utility_file",
                        message=f"Skipping utility file during traversal: `{target_path.name}`.",
                    )
                )
                continue

            queue.append(target_path)

    return sorted(reachable, key=lambda item: item.as_posix().lower()), warnings
