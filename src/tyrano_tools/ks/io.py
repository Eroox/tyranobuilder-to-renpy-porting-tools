from __future__ import annotations

from pathlib import Path

KS_FILE_ENCODINGS = ("utf-8", "cp932")


def read_ks_lines(path: Path) -> list[str]:
    last_decode_error: Exception | None = None

    for encoding in KS_FILE_ENCODINGS:
        try:
            return path.read_text(encoding=encoding).splitlines()
        except UnicodeDecodeError as exc:
            last_decode_error = exc
        except OSError as exc:
            raise RuntimeError(f"Failed to read KS file: {path}") from exc

    raise RuntimeError(f"Failed to decode KS file: {path}") from last_decode_error
