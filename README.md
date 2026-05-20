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

## Quick Start

You do not need Git to use this toolkit.

1. Download this repository as a ZIP from GitHub.
2. Extract the ZIP somewhere easy to find.
3. Make a copy of your TyranoBuilder project.
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
| Read or proofread one `.ks` file | `single_ks_file_to_screenplay_converter.py` |
| List media referenced by a `.ks` file | `extract_media_inventory.py` |
| Prepare Tyrano movie files for Ren'Py | `prepare_movies_for_renpy.py` |
| Convert one `.ks` file into a Ren'Py scaffold | `single_ks_file_to_renpy_script_converter.py` |
| Convert reachable story flow from a TyranoBuilder project | `tyranobuilder_scenario_to_renpy_script_converter.py` |
| Merge reachable scenario flow into one `.ks` file | `tyranobuilder_scenario_to_single_ks_file.py` |
| Build the fullest current Ren'Py project scaffold | `tyranobuilder_to_renpy_project.py` |

## Tool Summary

### `single_ks_file_to_screenplay_converter.py`

Converts one TyranoBuilder `.ks` file into readable text formats:

- plaintext
- screenplay-style Markdown
- Fountain screenplay

Good for proofreading, translation prep, and reading dialogue outside
TyranoBuilder.

### `extract_media_inventory.py`

Scans a `.ks` file and writes `ALL_MEDIA.md` so you can see referenced
backgrounds, sprites, music, sound effects, movies, fonts, and `.ks` files.

### `prepare_movies_for_renpy.py`

Converts TyranoBuilder movie assets into Ren'Py-friendlier `.webm` outputs.

This helper requires `ffmpeg`. Check your install with:

```bash
ffmpeg -version
```

If that command fails, install `ffmpeg` first. The getting-started guide includes
more beginner-friendly setup notes.

### `single_ks_file_to_renpy_script_converter.py`

Converts one `.ks` file into a starter Ren'Py `game/` scaffold. This is useful
for testing one scene, chapter, or isolated script before trying a larger
project migration.

### `tyranobuilder_scenario_to_renpy_script_converter.py`

Converts reachable scenario flow from a TyranoBuilder project root or
`data/scenario/` folder. It follows reachable non-system `.ks` files and writes a
script-focused Ren'Py scaffold.

### `tyranobuilder_scenario_to_single_ks_file.py`

Follows reachable scenario flow and writes one merged `.ks` file while keeping
source-file boundaries visible. This is useful for review, searching, or feeding
the result into another single-file workflow.

### `tyranobuilder_to_renpy_project.py`

Builds the fullest current Ren'Py project scaffold. It calls the scenario
converter, reads safe TyranoBuilder project config, creates starter Ren'Py files,
and writes planning reports for remaining asset and config work.

This is usually the best first tool to try for a whole-project migration.

## Example Commands

The `examples/...` paths below show the shape of the commands. If your download
does not include those sample files, replace them with the path to your own
TyranoBuilder `.ks` file or project folder.

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

### Single-File Ren'Py Conversion

```bash
python3 single_ks_file_to_renpy_script_converter.py examples/TyranoBuilder.ks -o out
```

### Scenario Conversion From A Project

```bash
python3 tyranobuilder_scenario_to_renpy_script_converter.py examples/SpinaNovel -o out
```

### Full Project Builder

```bash
python3 tyranobuilder_to_renpy_project.py examples/SpinaNovel -o out
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

### Movie Preparation For Ren'Py

```bash
python3 prepare_movies_for_renpy.py path/to/your-project
```

```bash
python3 prepare_movies_for_renpy.py path/to/your-project/data/video -o game/movies
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

## Safety Notes

- Keep a backup of your original TyranoBuilder project.
- Work on a copy of the project folder.
- Test generated Ren'Py output in a fresh Ren'Py project when possible.
- Review warning reports before assuming conversion is finished.
- Verify font filenames and asset paths manually.
- If a movie file does not play in Ren'Py, try `prepare_movies_for_renpy.py`.

## Related Docs

- [Getting Started With Ren'Py For Tyrano Users](docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md)
- [Common Ren'Py Fixes After Conversion](docs/COMMON_RENPY_FIXES_AFTER_CONVERSION.md)
- [Supported Conversion Features](docs/CONVERT_SCRIPT_FEATURES.md)
- [TyranoScript Tag Reference](docs/TYRANOSCRIPT_TAG_REFERENCE.md)
- [TyranoBuilder Project Tree](docs/TYRANOBUILDER_TREE.md)

## In Short

If you are brand new:

1. read [Getting Started With Ren'Py For Tyrano Users](docs/GETTING_STARTED_WITH_RENPY_FOR_TYRANO_USERS.md)
2. install Python
3. make a copy of your TyranoBuilder project
4. run `extract_media_inventory.py`
5. run `tyranobuilder_to_renpy_project.py`
6. inspect the generated `out/game/` scaffold
7. copy that into a fresh Ren'Py project and test
