"""Version helpers shared by the command line tools."""

from __future__ import annotations

import argparse

__version__ = "0.3.0"


def add_version_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )
