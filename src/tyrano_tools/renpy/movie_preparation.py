"""Prepare TyranoBuilder movie assets for Ren'Py-friendly playback."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from tyrano_tools.version import add_version_argument

DEFAULT_OUTPUT_DIR = Path("out")
REPORT_FILENAME = "RENPY_MOVIE_PREP_REPORT.md"
JSON_REPORT_FILENAME = "RENpy_MOVIE_PREP_REPORT.json"
MOVIE_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".ogv",
    ".ogg",
    ".mkv",
    ".avi",
    ".mpeg",
    ".mpg",
}


@dataclass
class SourceMovie:
    source_path: Path
    relative_path: Path
    action: str
    output_path: Path


@dataclass
class PreparedMovie:
    source_path: str
    output_path: str
    action: str
    source_codec_summary: Optional[str]
    ffmpeg_command: Optional[list[str]]
    note: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert TyranoBuilder movie files into Ren'Py-friendly outputs. "
            "Requires ffmpeg in PATH. Defaults to out/ unless you override it with -o."
        )
    )
    add_version_argument(parser)
    parser.add_argument(
        "input",
        type=Path,
        help=(
            "Path to a Tyrano project root, data/video directory, movie directory, "
            "or single movie file."
        ),
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for converted Ren'Py-friendly movie files (default: out).",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="VP9 quality target. Lower is higher quality. Default: 18.",
    )
    parser.add_argument(
        "--audio-bitrate",
        default="192k",
        help="Opus audio bitrate passed to ffmpeg (default: 192k).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in the output directory.",
    )
    parser.add_argument(
        "--reencode-webm",
        action="store_true",
        help="Re-encode existing .webm inputs instead of copying them unchanged.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned work and reports without running ffmpeg or copying files.",
    )
    return parser.parse_args()


def resolve_input_root(input_path: Path) -> Path:
    resolved = input_path.resolve()
    if resolved.is_file():
        return resolved.parent
    project_video_dir = resolved / "data" / "video"
    if project_video_dir.is_dir():
        return project_video_dir
    return resolved


def is_movie_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MOVIE_EXTENSIONS


def discover_movies(input_path: Path, reencode_webm: bool) -> tuple[Path, list[SourceMovie]]:
    resolved_input = input_path.resolve()
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input path does not exist: {resolved_input}")

    if resolved_input.is_file():
        if not is_movie_file(resolved_input):
            raise ValueError(f"Input file is not a supported movie file: {resolved_input}")
        root = resolved_input.parent
        return root, [build_source_movie(root, resolved_input, reencode_webm)]

    root = resolve_input_root(resolved_input)
    if not root.is_dir():
        raise NotADirectoryError(f"Movie input directory not found: {root}")

    discovered_movies = [
        build_source_movie(root, path, reencode_webm)
        for path in sorted(root.rglob("*"), key=lambda movie_path: str(movie_path).lower())
        if is_movie_file(path)
    ]
    movies = deduplicate_movies(discovered_movies)
    if not movies:
        raise FileNotFoundError(f"No supported movie files found under: {root}")
    return root, movies


def deduplicate_movies(source_movies: list[SourceMovie]) -> list[SourceMovie]:
    selected_by_output: dict[Path, SourceMovie] = {}
    for source_movie in source_movies:
        existing = selected_by_output.get(source_movie.output_path)
        if existing is None:
            selected_by_output[source_movie.output_path] = source_movie
            continue
        if existing.action == "transcode" and source_movie.action == "copy":
            selected_by_output[source_movie.output_path] = source_movie
    return sorted(selected_by_output.values(), key=lambda movie: str(movie.output_path).lower())


def build_source_movie(root: Path, source_path: Path, reencode_webm: bool) -> SourceMovie:
    relative_path = source_path.relative_to(root)
    target_relative_path = relative_path.with_suffix(".webm")
    action = "transcode"
    if source_path.suffix.lower() == ".webm" and not reencode_webm:
        target_relative_path = relative_path
        action = "copy"
    return SourceMovie(
        source_path=source_path,
        relative_path=relative_path,
        action=action,
        output_path=target_relative_path,
    )


def ensure_dependency(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        if name == "ffmpeg":
            raise RuntimeError(
                "Required dependency `ffmpeg` was not found in PATH. "
                "This helper needs ffmpeg installed before it can convert movies. "
                "After installing it, open a new terminal and run `ffmpeg -version` "
                "to verify the install, then rerun this helper. "
                "See README.md and "
                "docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md for setup guidance."
            )
        raise RuntimeError(f"Required dependency `{name}` was not found in PATH.")
    return path


def probe_movie(source_path: Path) -> Optional[str]:
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        return None
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,codec_name,pix_fmt",
        "-of",
        "json",
        str(source_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    parts: list[str] = []
    for stream in payload.get("streams", []):
        codec_type = stream.get("codec_type")
        codec_name = stream.get("codec_name")
        pix_fmt = stream.get("pix_fmt")
        description = f"{codec_type}={codec_name}" if codec_type and codec_name else None
        if description and pix_fmt and codec_type == "video":
            description = f"{description} ({pix_fmt})"
        if description:
            parts.append(description)
    return ", ".join(parts) if parts else None


def build_ffmpeg_command(
    ffmpeg_path: str,
    source_path: Path,
    output_path: Path,
    crf: int,
    audio_bitrate: str,
    overwrite: bool,
) -> list[str]:
    return [
        ffmpeg_path,
        "-y" if overwrite else "-n",
        "-i",
        str(source_path),
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        str(crf),
        "-row-mt",
        "1",
        "-c:a",
        "libopus",
        "-b:a",
        audio_bitrate,
        str(output_path),
    ]


def render_report(
    input_root: Path,
    output_root: Path,
    prepared_movies: list[PreparedMovie],
    dry_run: bool,
    crf: int,
    audio_bitrate: str,
) -> str:
    lines = [
        "# Ren'Py Movie Preparation Report",
        "",
        f"Input root: `{input_root}`",
        f"Output root: `{output_root}`",
        f"Mode: `{'dry-run' if dry_run else 'executed'}`",
        f"Video preset: `VP9 CRF {crf}`",
        f"Audio preset: `Opus {audio_bitrate}`",
        "",
        "## Why This Helper Exists",
        "",
        "- Ren'Py movie playback is stricter than ordinary image, audio, or font loading.",
        (
            "- Official Ren'Py movie docs support containers such as `WebM`, "
            "`Matroska`, and `Ogg`, with codecs such as `VP9`, `VP8`, `AV1`, "
            "`Theora`, and audio such as `Opus` or `Vorbis`."
        ),
        (
            "- The same docs note that the common `H.264 + AAC in MP4` combination "
            "is mainly a Web-platform case because Ren'Py itself does not normally "
            "decode H.264 or AAC in the standard desktop movie path."
        ),
        (
            "- That is why a Tyrano `.mp4` may look fine in the source project but "
            "fail in desktop Ren'Py until it is re-encoded to a Ren'Py-friendly "
            "format like `.webm`."
        ),
        "",
        (
            "Reference: Ren'Py movie docs `https://www.renpy.org/doc/html/movie` "
            "and splashscreen docs "
            "`https://www.renpy.org/doc/html/splashscreen_presplash.html`."
        ),
        "",
        "## Prepared Movies",
        "",
    ]

    for prepared_movie in prepared_movies:
        lines.append(f"- `{prepared_movie.source_path}` -> `{prepared_movie.output_path}`")
        lines.append(f"  - action: `{prepared_movie.action}`")
        if prepared_movie.source_codec_summary:
            lines.append(f"  - source codecs: `{prepared_movie.source_codec_summary}`")
        if prepared_movie.ffmpeg_command:
            command = " ".join(
                f'"{part}"' if " " in part else part for part in prepared_movie.ffmpeg_command
            )
            lines.append(f"  - ffmpeg: `{command}`")
        lines.append(f"  - note: {prepared_movie.note}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def prepare_movies(args: argparse.Namespace) -> list[PreparedMovie]:
    input_root, source_movies = discover_movies(args.input, args.reencode_webm)
    output_root = args.out_dir.resolve()
    ffmpeg_path = (
        ensure_dependency("ffmpeg")
        if any(movie.action == "transcode" for movie in source_movies)
        else ""
    )

    prepared_movies: list[PreparedMovie] = []
    for source_movie in source_movies:
        destination_path = output_root / source_movie.output_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_codec_summary = probe_movie(source_movie.source_path)

        if source_movie.action == "copy":
            if destination_path.exists() and not args.overwrite:
                raise FileExistsError(
                    f"Output already exists: {destination_path}. Use --overwrite to replace it."
                )
            if not args.dry_run:
                shutil.copy2(source_movie.source_path, destination_path)
            prepared_movies.append(
                PreparedMovie(
                    source_path=str(source_movie.source_path),
                    output_path=str(destination_path),
                    action="copy",
                    source_codec_summary=source_codec_summary,
                    ffmpeg_command=None,
                    note="Input was already .webm, so it was copied unchanged by default.",
                )
            )
            continue

        ffmpeg_command = build_ffmpeg_command(
            ffmpeg_path=ffmpeg_path,
            source_path=source_movie.source_path,
            output_path=destination_path,
            crf=args.crf,
            audio_bitrate=args.audio_bitrate,
            overwrite=args.overwrite,
        )
        if not args.dry_run:
            result = subprocess.run(ffmpeg_command, check=False)
            if result.returncode != 0:
                raise RuntimeError(
                    "ffmpeg failed while converting "
                    f"`{source_movie.source_path}` to `{destination_path}`"
                )
        prepared_movies.append(
            PreparedMovie(
                source_path=str(source_movie.source_path),
                output_path=str(destination_path),
                action="transcode",
                source_codec_summary=source_codec_summary,
                ffmpeg_command=ffmpeg_command,
                note=(
                    "Converted to `.webm` with `VP9 + Opus`, which aligns better "
                    "with Ren'Py's desktop movie support than typical Tyrano `.mp4` "
                    "assets."
                ),
            )
        )

    report_text = render_report(
        input_root=input_root,
        output_root=output_root,
        prepared_movies=prepared_movies,
        dry_run=args.dry_run,
        crf=args.crf,
        audio_bitrate=args.audio_bitrate,
    )
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / REPORT_FILENAME).write_text(report_text, encoding="utf-8")
    (output_root / JSON_REPORT_FILENAME).write_text(
        json.dumps([asdict(prepared_movie) for prepared_movie in prepared_movies], indent=2),
        encoding="utf-8",
    )
    return prepared_movies


def main() -> None:
    args = parse_args()
    try:
        prepared_movies = prepare_movies(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("Prepared movies:")
    for prepared_movie in prepared_movies:
        print(
            "- "
            f"{prepared_movie.source_path} -> {prepared_movie.output_path} "
            f"({prepared_movie.action})"
        )
    print(f"- Report: {(args.out_dir.resolve() / REPORT_FILENAME)}")
