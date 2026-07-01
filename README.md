# TyranoBuilder-to-Ren'Py Migration Toolkit

This repository contains Python tools for helping people move a TyranoBuilder or
TyranoScript project toward Ren'Py.

The tools can help you inspect `.ks` scripts, list needed media, convert story
flow into Ren'Py script files, prepare movies for Ren'Py playback, and build a
starter Ren'Py project scaffold.

If you are new to Ren'Py, start here:

- [Getting Started With Ren'Py For Tyrano Users](docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md)

That guide explains the full beginner workflow, including how to download the
toolkit, run scripts, understand generated files, copy assets, and test inside a
fresh Ren'Py project.

## Compatibility

These tools are currently tested against TyranoBuilder `3.0.6.c` project
exports. Earlier TyranoBuilder versions may work, but they are not
guaranteed because project layout, generated tags, and asset conventions
can differ between releases.

Generated Ren'Py output currently targets Ren'Py `8.5.3` or newer.

## Quick Start

You do not need Git to use this toolkit.

1. Download this repository as a ZIP from GitHub.
2. Extract the ZIP somewhere easy to find.
3. Make a copy of your TyranoBuilder project, best if copy is in this toolkit folder!
4. Install Python from `https://www.python.org/downloads/`.
5. Open a terminal in this toolkit folder.
6. Run the tool that matches your migration task.

Check Python with:

```bash
python3 --version
```

If `python3` does not work on your machine, try:

```bash
python --version
```

Most commands look like this:

```bash
python3 some_script.py [input] [options]
```

Check a tool version with either version flag:

```bash
python3 some_script.py --version
python3 some_script.py -V
```

## Which Tool Should I Use?

| Goal | Tool |
| --- | --- |
| Build the fullest current Ren'Py project scaffold (recommended starting point) | `tyranobuilder_to_renpy_project.py` |
| Read or proofread one `.ks` file | `single_ks_file_to_screenplay_converter.py` |
| List media referenced by a `.ks` file | `extract_media_inventory.py` |
| Prepare Tyrano movie files for Ren'Py | `prepare_movies_for_renpy.py` |
| Convert one `.ks` file into a Ren'Py scaffold (single-file experiment) | `single_ks_file_to_renpy_script_converter.py` |
| Merge reachable scenario flow into one `.ks` file | `tyranobuilder_scenario_to_single_ks_file.py` |
| Generate ONLY story `.rpy` files without `options.rpy` / `gui.rpy` / `screens.rpy` / `keymap.rpy` (advanced) | `tyranobuilder_scenario_to_renpy_script_converter.py` |

## Tool Summary

### `tyranobuilder_to_renpy_project.py`

**Recommended starting point for whole-project migrations.**

Builds the fullest current Ren'Py project scaffold. It calls the scenario
converter internally, reads safe TyranoBuilder project config from
`data/system/Config.tjs` and `data/system/KeyConfig.js`, creates starter Ren'Py
files, creates empty target asset directories, and writes planning reports for
remaining asset and config work.

Output includes:

- `out/game/script.rpy` (Ren'Py startup wiring)
- `out/game/story/*.rpy` (per-source-file converted scenes)
- `out/game/characters.rpy`, `out/game/images.rpy`, `out/game/custom_effects.rpy`
- `out/game/options.rpy` (Ren'Py config, build name, save directory)
- `out/game/gui.rpy` (UI styling and dimensions)
- `out/game/screens.rpy` (say, menu, quick-menu, file-picker screens)
- `out/game/keymap.rpy` (safe partial Tyrano keymap import)
- `out/game/NEEDED_MEDIA.md`, `out/game/NEEDED_MEDIA_RAW.json`
- `out/game/ASSET_MIGRATION_PLAN.md`, `out/game/PROJECT_CONFIG_MAPPING.md`
- `out/game/DIRECTORY_SCAFFOLD.md`
- empty asset directories under `out/game/images/`, `out/game/audio/`, etc.

This is the right tool for almost every whole-project migration scenario.

**Optional: copy assets automatically with `-m` / `--migrate-assets`.**

When the input is a real TyranoBuilder project root (with a `data/` folder),
you can add `-m` (or `--migrate-assets`) to have the builder copy each
reachable referenced asset from the Tyrano project into the generated
Ren'Py `game/` tree. Only assets actually referenced by the traversed
scenario files are copied. This also covers fonts referenced by
`[font face="..."]` (copied into `game/fonts/`) and UI art referenced by
`[button graphic=... enterimg=...]` or `[clickable _clickable_img=...]`
(copied into `game/images/ui/`, preserving the relative subpath).
Existing destination files are skipped rather than overwritten, and a new
`out/game/ASSET_MIGRATION_REPORT.md` summarizes what was copied, already
present, or missing.

```bash
python3 tyranobuilder_to_renpy_project.py path/to/your-project -o out --migrate-assets
```

### `single_ks_file_to_screenplay_converter.py`

Converts one TyranoBuilder `.ks` file into readable text formats:

- plaintext
- screenplay-style Markdown
- Fountain screenplay

Good for proofreading, translation prep, and reading dialogue outside
TyranoBuilder.

> Tip: use `tyranobuilder_scenario_to_single_ks_file.py` to convert you entire project into one ks file so you have a single screenplay

### `extract_media_inventory.py`

Scans a `.ks` file and writes `ALL_MEDIA.md` so you can see referenced
backgrounds, sprites, music, sound effects, movies, fonts, and `.ks` files.

### `prepare_movies_for_renpy.py`

Converts TyranoBuilder movie assets into Ren'Py-friendlier `.webm` outputs.

This helper requires `ffmpeg`. Check your install with:

```bash
ffmpeg -version
```

If that command fails, install `ffmpeg` first. The GETTING_STARTED guide includes
more beginner-friendly setup notes.

### `single_ks_file_to_renpy_script_converter.py`

Converts one `.ks` file into a starter Ren'Py `game/` scaffold. This is useful
for testing one scene, chapter, or isolated script before trying a larger
project migration.

### `tyranobuilder_scenario_to_single_ks_file.py`

Follows reachable scenario flow and writes one merged `.ks` file while keeping
source-file boundaries visible. This is useful for review, searching, or feeding
the result into another single-file workflow.

### `tyranobuilder_scenario_to_renpy_script_converter.py`

> **Most users should NOT use this tool. Use `tyranobuilder_to_renpy_project.py` instead.**
>
> This tool produces an incomplete Ren'Py game folder that will not launch
> correctly on its own. It is intended for advanced workflows where you
> already have customized `options.rpy`, `gui.rpy`, `screens.rpy`, and
> `keymap.rpy` and only want to regenerate the story flow.

**What it reads:**

- a TyranoBuilder project root, or a `data/scenario/` folder directly
- the reachable non-system `.ks` files starting from `first.ks` (or `--entry`)

**What it produces:**

- `out/game/script.rpy` (Ren'Py startup wiring)
- `out/game/story/*.rpy` (per-source-file converted scenes)
- `out/game/characters.rpy`
- `out/game/images.rpy`
- `out/game/custom_effects.rpy`
- `out/game/route_map.md`
- `out/game/conversion_warnings.md`

**What it does NOT produce (critical):**

- `options.rpy` (Ren'Py config, build name, save directory)
- `gui.rpy` (UI styling and dimensions)
- `screens.rpy` (say, menu, quick-menu, file-picker screens)
- `keymap.rpy` (Tyrano keymap import)
- `NEEDED_MEDIA.md`, `NEEDED_MEDIA_RAW.json`, `ASSET_MIGRATION_PLAN.md`,
  `PROJECT_CONFIG_MAPPING.md`, `DIRECTORY_SCAFFOLD.md`
- empty asset directories under `out/game/images/`, `out/game/audio/`, etc.

Copying only this tool's output into a Ren'Py project will typically leave
critical configuration missing and the game will not launch correctly. Prefer
`tyranobuilder_to_renpy_project.py` for beginner and standard whole-project
workflows.

## Example Commands

The `examples/...` paths below show the shape of the commands. If your download
does not include those sample files, replace them with the path to your own
TyranoBuilder `.ks` file or project folder.

### Full Project Builder (recommended)

```bash
python3 tyranobuilder_to_renpy_project.py examples/SpinaNovel -o out
```

### Screenplay Conversion

```bash
python3 single_ks_file_to_screenplay_converter.py examples/TyranoBuilder.ks -o out
```

```bash
python3 single_ks_file_to_screenplay_converter.py examples/TyranoBuilder.ks -o out -m -n -f
```

### Media Inventory

```bash
python3 extract_media_inventory.py examples/TyranoBuilder.ks
```

### Movie Preparation For Ren'Py

```bash
python3 prepare_movies_for_renpy.py path/to/your-project
```

```bash
python3 prepare_movies_for_renpy.py path/to/your-project/data/video -o game/movies
```

### Single-File Ren'Py Conversion

```bash
python3 single_ks_file_to_renpy_script_converter.py examples/TyranoBuilder.ks -o out
```

### Merge Reachable Scenario Flow Into One `.ks`

```bash
python3 tyranobuilder_scenario_to_single_ks_file.py path/to/your-project
```

```bash
python3 tyranobuilder_scenario_to_single_ks_file.py path/to/your-project -c "TheVNScript"
```

```bash
python3 tyranobuilder_scenario_to_single_ks_file.py path/to/your-project --order sorted
```

### Scenario-Only Conversion (advanced)

Only use this if you specifically want story `.rpy` files without
`options.rpy` / `gui.rpy` / `screens.rpy` / `keymap.rpy`. For a complete
scaffold use `tyranobuilder_to_renpy_project.py` above.

```bash
python3 tyranobuilder_scenario_to_renpy_script_converter.py examples/SpinaNovel -o out
```

## Output Folders

By default, tools write generated local outputs into `out/` unless you override
the destination with `-o`.

Treat `out/` as a working folder for review and testing. It is not meant to be
permanent shipped game content.

## Current Limits

This toolkit is useful now, but it is not full TyranoBuilder parity.

Expect manual work for:

- advanced UI recreation
- graphical choice buttons and clickable regions
- plugin behavior
- JavaScript-heavy logic
- some message-layer and system-scene behavior
- asset copying and final path cleanup

Generated Ren'Py output is a starting point. Review `conversion_warnings.md`,
copy required assets, test in a fresh Ren'Py project, and fix issues one at a
time.

## Common Pitfalls

### TyranoBuilder "Preview From Here" Replaces `first.ks`

When you click "Preview from here" inside the TyranoBuilder editor,
TyranoBuilder writes a `_preview.ks` file and rewrites `first.ks` so the
in-editor preview launcher can start mid-scene. If you then export, copy, or
hand off that project without restoring `first.ks`, every tool that walks the
scenario from the default entry point will only see the tiny preview snippet,
not your real game.

Affected tools (anything that starts from `first.ks`):

- `tyranobuilder_to_renpy_project.py`
- `tyranobuilder_scenario_to_renpy_script_converter.py`
- `tyranobuilder_scenario_to_single_ks_file.py`

When this happens, the converters now emit a `preview_entry_detected` warning
inside the generated warnings report (`conversion_warnings.md` for the project
builder and scenario converter, `merge_warnings.md` for the single-`.ks`
merger). Open that file first if your generated output looks unexpectedly
small or only covers a single scene.

Recovery options:

- Re-export your TyranoBuilder project so `first.ks` is restored to its
  bootstrap state, then re-run the converter.
- Or pass `--entry title_screen.ks` (or whatever your real entry file is
  named) to skip the preview artifact, for example:

```bash
python3 tyranobuilder_to_renpy_project.py path/to/your-project --entry title_screen.ks
```

Note that bypassing `first.ks` also skips its system-library bootstrap (layer
setup, character defines, plugins). The converter already filters
`system/*.ks` out of traversal, so the bootstrap was not contributing
scenario content, but if you have any non-system setup inside `first.ks` you
will need to move it into your overriding entry file.

For Ren'Py's equivalent preview workflows once your project is migrated, see
*How To Preview A Specific Scene In Ren'Py* in
[`docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md`](docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md).

## Safety Notes

- Keep a backup of your original TyranoBuilder project.
- Work on a copy of the project folder.
- Test generated Ren'Py output in a fresh Ren'Py project when possible.
- Review warning reports before assuming conversion is finished.
- Verify font filenames and asset paths manually.
- If a movie file does not play in Ren'Py, try `prepare_movies_for_renpy.py`.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for release history.

## Related Docs

- [Getting Started With Ren'Py For Tyrano Users](docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md)
- [Common Ren'Py Fixes After Conversion](docs/COMMON_RENPY_FIXES_AFTER_CONVERSION.md)
- [Supported Conversion Features](docs/CONVERT_SCRIPT_FEATURES.md)
- [TyranoScript Tag Reference](docs/TYRANOSCRIPT_TAG_REFERENCE.md)
- [TyranoBuilder Project Tree](docs/TYRANOBUILDER_TREE.md)
- [Migrating From 0.4.2 To 0.5.0](docs/MIGRATING_FROM_0.4.2_TO_0.5.0.md)
