# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
