from __future__ import annotations

import sys
from pathlib import Path


def ensure_src_path() -> None:
    src_root = Path(__file__).resolve().parent / "src"
    src_root_str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)
