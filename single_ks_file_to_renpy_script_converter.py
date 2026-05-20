#!/usr/bin/env python3

from __future__ import annotations

from bootstrap_src_path import ensure_src_path


def main() -> None:
    ensure_src_path()

    from tyrano_tools.scenario.single_file_converter import main as shared_main

    shared_main()


if __name__ == "__main__":
    main()
