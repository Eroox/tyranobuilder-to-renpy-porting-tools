#!/usr/bin/env python3
"""Convert TyranoBuilder scenario flow into Ren'Py script outputs."""

from __future__ import annotations

from bootstrap_src_path import ensure_src_path


def main() -> None:
    ensure_src_path()

    from tyrano_tools.scenario.converter import main as scenario_converter_main

    scenario_converter_main()


if __name__ == "__main__":
    main()
