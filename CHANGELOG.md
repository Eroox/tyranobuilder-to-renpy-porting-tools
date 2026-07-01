# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-07-01

> Heads-up: `0.5.0` is a breaking release for anyone regenerating on top
> of a `0.4.2` output tree. The generated Ren'Py folder layout was
> tightened to align more closely with Ren'Py's own example projects and
> to be a little more opinionated about where assets live. This work also
> sets the stage for an upcoming Ren'Py-focused UI that assumes the new
> layout. See `docs/MIGRATING_FROM_0.4.2_TO_0.5.0.md` for the step-by-step
> upgrade path.

### Breaking Changes
- Generated music folder renamed from `game/audio/bgm/` to
  `game/audio/music/`.
- Generated character sprite folder renamed from `game/images/character/`
  to `game/images/characters/`.
- Character sprite subfolders now use the character name instead of
  Tyrano's numeric folder, for example
  `game/images/characters/eileen/smile.png` instead of
  `game/images/character/1/smile.png`.
- Renamed generated `game/transitions.rpy` to `game/custom_effects.rpy`.
  Story files keep their existing `with tyrano_hpunch_*` references.
- `game/options.rpy` no longer defines `config.history_length`. That
  setting now lives only in `game/gui.rpy`, which is where Ren'Py
  expects it.
- Generated `game/options.rpy` now ships a fuller build classification
  block, including active `archive` rules for images, audio, fonts,
  movies, and compiled scripts. If you had customized the previous
  minimal block, port your edits into the new one.

### Added
- Added `-m` / `--migrate-assets` to `tyranobuilder_to_renpy_project.py`.
  When the input is a real TyranoBuilder project root (with a `data/`
  folder), the builder now copies each reachable referenced asset from
  the Tyrano project into the generated Ren'Py `game/` tree. Only assets
  actually referenced by the traversed scenario files are copied,
  existing destination files are skipped instead of overwritten, and a
  new `game/ASSET_MIGRATION_REPORT.md` summarizes what was copied,
  skipped, or missing.
- Extended `--migrate-assets` to also copy fonts referenced by
  `[font face="..."]` and UI images referenced by
  `[button graphic=... enterimg=...]` / `[clickable _clickable_img=...]`.
  Fonts land in `game/fonts/` (preserving the on-disk suffix so `.otf`
  faces stay `.otf`), and UI images land in `game/images/ui/` with the
  original relative subpath preserved (for example
  `data/image/config/c_btn.png` becomes `game/images/ui/config/c_btn.png`).
- Added a `UI Images` section to `game/NEEDED_MEDIA.md` and
  `game/NEEDED_MEDIA_RAW.json` for the same references. The standalone
  `extract_media_inventory.py` output also gains a `UI Images` section.
- Sorted `game/images.rpy` into a Background Images section and a
  Character Sprites section, each in alphabetical order, so hand-editing
  and diffing are easier.
- Added `docs/MIGRATING_FROM_0.4.2_TO_0.5.0.md` with the manual steps
  users need to take when regenerating a project on top of a `0.4.2`
  output tree.
- Documented current compatibility expectations in `README.md` and
  `docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md`: the tools are
  tested against TyranoBuilder `3.0.6.c` project exports, and generated
  Ren'Py output targets Ren'Py `8.5.3` or newer.

## [0.4.2] - 2026.06.10

### Added
- Detected TyranoBuilder "Preview from here" artifacts in the converter
  entry-point path. When the resolved entry file is `_preview.ks`, or
  when `first.ks` jumps or calls into `_preview.ks`, a
  `preview_entry_detected` warning is now written into the generated
  warnings report (`conversion_warnings.md` for
  `tyranobuilder_to_renpy_project.py` and
  `tyranobuilder_scenario_to_renpy_script_converter.py`,
  `merge_warnings.md` for `tyranobuilder_scenario_to_single_ks_file.py`) so
  users can tell that the converter only walked a TyranoBuilder editor
  preview snippet instead of the real game.

### Changed
- `--entry` help text on `tyranobuilder_to_renpy_project.py`,
  `tyranobuilder_scenario_to_renpy_script_converter.py`, and
  `tyranobuilder_scenario_to_single_ks_file.py` now points users at the
  TyranoBuilder "Preview from here" scenario as a concrete reason to
  override the default entry file.

## [0.4.1] - 2026-06-10

### Fixed
- `tyranobuilder_to_renpy_project.py` no longer crashes with a
  `FileNotFoundError` when it tries to generate `options.rpy`, `gui.rpy`, or
  `screens.rpy`. The Ren'Py starter templates now ship inside the
  `tyrano_tools` package, so the project builder works from any install
  location .
- Speaker, sprite, scene, and label identifiers derived from non-ASCII names
  (Cyrillic, Japanese, Chinese, Greek, Arabic, etc.) no longer collapse to
  the bare prefix in generated Ren'Py output. Previously, every distinct
  Cyrillic speaker name was defined as `speaker` in `characters.rpy`, which
  redefined the same identifier over and over and made every such character
  speak with whichever name was defined last. 

### Changed
- Reordered and reworded the README, the
  `GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md` guide, and the converter
  `--help` text so `tyranobuilder_to_renpy_project.py` is presented as the
  recommended starting point for whole-project Ren'Py migrations. The
  scenario-only converter (`tyranobuilder_scenario_to_renpy_script_converter.py`)
  is now flagged as advanced and explicitly notes that it does not produce
  `options.rpy`, `gui.rpy`, `screens.rpy`, or `keymap.rpy`.

## [0.4.0] - 2026-06-09

### Added
- Convert TyranoBuilder `[clickable]` tags into invisible Ren'Py imagebutton
  hotspots (using a `Null(width, height)` displayable) so polygonal click
  regions over a background are preserved.
- Emit `with` transition clauses after `[bg]`, `[chara_show]`, `[chara_mod]`,
  and `[chara_hide]` so cross-fades and slide-in animations carry over from
  TyranoBuilder. Includes a mapping table that translates Tyrano `method=`
  values (such as `crossfade`, `fadeIn`, `slideInLeft`, `zoomIn`, `shake`,
  legacy `explode`/`slide`/`blind`/etc.) into the closest Ren'Py transition,
  with `Dissolve(t)` as the default fallback. When `time="0"` or
  `cross="false"` is set, no `with` clause is emitted so the visual snap
  matches TyranoBuilder runtime behavior.

### Removed
- The noisy `inline_click_wait` warning that was raised whenever a `[l]` tag
  appeared inside dialogue. Inline `[l]` already renders correctly as `{w}` in
  the generated Ren'Py text.

## [0.3.0] - 2026-05-19

Initial public release of the TyranoBuilder-to-Ren'Py toolkit.

### Added
- `single_ks_file_to_screenplay_converter.py`: convert a single `.ks` file to
  plaintext, Markdown, and Fountain screenplay formats.
- `tyranobuilder_scenario_to_single_ks_file.py`: merge a TyranoBuilder
  `scenario/` directory into a single `.ks` file.
- `single_ks_file_to_renpy_script_converter.py` and
  `tyranobuilder_scenario_to_renpy_script_converter.py`: convert `.ks` content
  into Ren'Py script form.
- `tyranobuilder_to_renpy_project.py`: scaffold a Ren'Py project from a
  TyranoBuilder source tree.
- `prepare_movies_for_renpy.py`: stage TyranoBuilder movie assets for Ren'Py.
- `extract_media_inventory.py`: report media assets referenced by a project.
- Shared `tyrano_tools` package with parsing, rendering, and IO helpers.
- `--version` / `-V` flag on every CLI, sourced from
  `src/tyrano_tools/version.py`.
