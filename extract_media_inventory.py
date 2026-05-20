#!/usr/bin/env python3
"""Extract a migration-focused media inventory from a TyranoBuilder KS file."""

from __future__ import annotations

import argparse
from pathlib import Path

from bootstrap_src_path import ensure_src_path


def parse_args() -> argparse.Namespace:
    from tyrano_tools.version import add_version_argument

    parser = argparse.ArgumentParser(
        description="Extract a migration-focused media inventory from a TyranoBuilder KS file.",
    )
    add_version_argument(parser)
    parser.add_argument("input", type=Path, help="Path to the .ks file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("ALL_MEDIA.md"),
        help="Markdown file to write (default: ALL_MEDIA.md)",
    )
    parser.add_argument(
        "-c",
        "--include-counts",
        action="store_true",
        help="Include per-item usage counts",
    )
    parser.add_argument(
        "-l",
        "--include-line-numbers",
        action="store_true",
        help="Include per-item source line numbers",
    )
    return parser.parse_args()


def main() -> None:
    ensure_src_path()

    from tyrano_tools.inventory.media import extract_inventory, render_inventory_markdown

    args = parse_args()
    input_path: Path = args.input
    output_path: Path = args.output

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    inventory = extract_inventory(input_path)
    output_text = render_inventory_markdown(
        input_path=input_path,
        inventory=inventory,
        include_counts=args.include_counts,
        include_line_numbers=args.include_line_numbers,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")

    print(f"Wrote media inventory: {output_path}")


if __name__ == "__main__":
    main()
