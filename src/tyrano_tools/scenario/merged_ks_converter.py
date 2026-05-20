"""Merge reachable TyranoBuilder scenario files into one intact .ks output."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from tyrano_tools.ks.io import read_ks_lines
from tyrano_tools.scenario.traversal import (
    DEFAULT_EXCLUDED_FILES,
    WarningRecord,
    discover_reachable_files,
    is_system_storage,
    resolve_entry_file,
    resolve_scenario_dir,
    resolve_storage_path,
    scan_references,
)
from tyrano_tools.version import add_version_argument

DEFAULT_OUTPUT_BASENAME = "TyranoBuilder"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge reachable TyranoBuilder scenario files into one intact .ks file.",
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
        help="Directory to write the merged .ks and reports (default: out)",
    )
    parser.add_argument(
        "--entry",
        default=None,
        help="Override the default entry .ks file inside the scenario directory",
    )
    parser.add_argument(
        "-c",
        "--custom-name",
        default=None,
        help="Custom basename for the merged .ks output, without needing to add .ks",
    )
    parser.add_argument(
        "--order",
        choices=("dfs", "sorted"),
        default="dfs",
        help=(
            "Merge ordering mode: `dfs` follows one branch to the end before the "
            "next, while `sorted` uses deterministic path ordering (default: dfs)"
        ),
    )
    return parser.parse_args()


def build_output_filename(custom_name: Optional[str]) -> str:
    basename = (custom_name or DEFAULT_OUTPUT_BASENAME).strip()
    if not basename:
        basename = DEFAULT_OUTPUT_BASENAME
    if basename.lower().endswith(".ks"):
        return basename
    return f"{basename}.ks"


def render_merged_ks(reachable_files: Sequence[Path], scenario_dir: Path) -> str:
    sections: list[str] = []
    total = len(reachable_files)
    for index, path in enumerate(reachable_files, start=1):
        relative_name = path.relative_to(scenario_dir).as_posix()
        sections.append(f"; ==== BEGIN {relative_name} ({index}/{total}) ====")
        sections.extend(read_ks_lines(path))
        sections.append(f"; ==== END {relative_name} ====")
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"


def display_scenario_dir(scenario_dir: Path) -> str:
    if scenario_dir.name == "scenario":
        return "data/scenario"
    return scenario_dir.as_posix()


def render_route_map(reachable_files: Sequence[Path], scenario_dir: Path, entry_file: Path) -> str:
    lines = [
        "# Route Map",
        "",
        f"- Scenario directory: `{display_scenario_dir(scenario_dir)}`",
        f"- Entry file: `{entry_file.relative_to(scenario_dir).as_posix()}`",
        f"- Reachable file count: `{len(reachable_files)}`",
        "",
        "## Merge Order",
        "",
    ]
    for index, path in enumerate(reachable_files, start=1):
        lines.append(f"{index}. `{path.relative_to(scenario_dir).as_posix()}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_warning_report(warnings: Sequence[WarningRecord]) -> str:
    lines = ["# Merge Warnings", ""]
    if not warnings:
        lines.append("- No traversal warnings were recorded.")
        lines.append("")
        return "\n".join(lines)

    for warning in warnings:
        lines.append(
            f"- `{warning.source_path.name}:{warning.line_number}` "
            f"[{warning.category}] {warning.message}"
        )
    lines.append("")
    return "\n".join(lines)


def discover_reachable_files_depth_first(
    scenario_dir: Path,
    entry_file: Path,
) -> tuple[list[Path], list[WarningRecord]]:
    reachable: list[Path] = []
    warnings: list[WarningRecord] = []
    seen: set[Path] = set()
    scenario_files = {path.resolve() for path in scenario_dir.glob("*.ks")}
    entry_resolved = entry_file.resolve()

    def visit(current: Path) -> None:
        current = current.resolve()
        if current in seen:
            return
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
                            "Traversal reference points outside the known scenario "
                            f"set: storage=`{ref.storage}`."
                        ),
                    )
                )
                continue

            if target_path.name in DEFAULT_EXCLUDED_FILES and target_path != entry_resolved:
                warnings.append(
                    WarningRecord(
                        source_path=ref.source_path,
                        line_number=ref.line_number,
                        category="excluded_utility_file",
                        message=f"Skipping utility file during traversal: `{target_path.name}`.",
                    )
                )
                continue

            visit(target_path)

    visit(entry_resolved)
    return reachable, warnings


def write_outputs(
    reachable_files: Sequence[Path],
    scenario_dir: Path,
    entry_file: Path,
    warnings: Sequence[WarningRecord],
    out_dir: Path,
    output_filename: str,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    merged_path = out_dir / output_filename
    merged_path.write_text(render_merged_ks(reachable_files, scenario_dir), encoding="utf-8")

    route_map_path = out_dir / "route_map.md"
    route_map_path.write_text(
        render_route_map(reachable_files, scenario_dir, entry_file),
        encoding="utf-8",
    )

    warnings_path = out_dir / "merge_warnings.md"
    warnings_path.write_text(render_warning_report(warnings), encoding="utf-8")

    return [merged_path, route_map_path, warnings_path]


def main() -> None:
    args = parse_args()
    scenario_dir = resolve_scenario_dir(args.input).resolve()
    entry_file = resolve_entry_file(scenario_dir, args.entry).resolve()
    if args.order == "dfs":
        reachable_files, traversal_warnings = discover_reachable_files_depth_first(
            scenario_dir,
            entry_file,
        )
    else:
        reachable_files, traversal_warnings = discover_reachable_files(scenario_dir, entry_file)
    output_filename = build_output_filename(args.custom_name)
    written_paths = write_outputs(
        reachable_files=reachable_files,
        scenario_dir=scenario_dir,
        entry_file=entry_file,
        warnings=traversal_warnings,
        out_dir=args.out_dir.resolve(),
        output_filename=output_filename,
    )

    print("Wrote outputs:")
    for written_path in written_paths:
        print(f"- {written_path}")


if __name__ == "__main__":
    main()
