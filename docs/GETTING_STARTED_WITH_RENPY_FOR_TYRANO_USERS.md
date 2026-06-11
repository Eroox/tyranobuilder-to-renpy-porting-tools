# GETTING STARTED WITH REN'PY FOR TYRANO USERS

This guide is for people coming from TyranoBuilder or TyranoScript who are not
used to code, terminals, or source-control tools.

If you have mostly worked inside the TyranoBuilder UI, that is okay. This guide
is meant to walk you through the first real steps of using this toolkit and
understanding the files it generates.

## What This Guide Helps You Do

- download this toolkit without Git
- install Python
- understand which script to run
- understand what the generated files mean
- copy the right files into a Ren'Py project
- know what still needs manual cleanup

## First, The Big Mindset Shift

TyranoBuilder is mostly UI-based.

Ren'Py is mostly file-based.

That sounds intimidating at first, but in practice your early Ren'Py work is
usually just:

- running a script
- opening text files
- reading warnings
- copying assets
- launching the project
- fixing one problem at a time

You do not need to become a full programmer before you can start migrating.

## Step 1: Download This Toolkit

You do not need Git.

Use the GitHub ZIP download instead.

### How To Download The ZIP

1. Open the GitHub page for this repository
2. Click the `Code` button
3. Click `Download ZIP`
4. Save the ZIP somewhere easy to find
5. Extract it

After extracting it, you will have a normal folder full of Python scripts and
docs.

## Step 2: Make A Safe Working Copy

Before you run any migration tool:

- keep your original TyranoBuilder project untouched
- make a copy of your TyranoBuilder project folder
- run the tools against the copy
- test the generated Ren'Py files in a fresh Ren'Py project when possible

This matters because migration work is experimental by nature. It is much less
stressful if you always have the original project to fall back on.

## Step 3: Install Python

The scripts in this repo are Python scripts.

### Where To Get Python

- `https://www.python.org/downloads/`

If you are on Windows, the installer may ask whether to add Python to PATH.
If you see that option, enable it.

### How To Check If Python Works

Open a terminal or command prompt and run:

```bash
python3 --version
```

If that does not work, try:

```bash
python --version
```

If one of those prints a version number, Python is installed and working.

## Step 4: Open A Terminal In The Toolkit Folder

You need to run the scripts from inside the extracted toolkit folder.

Examples:

- Windows: open the extracted folder in File Explorer, then either:
  1. Click the address bar at the top of the window, type `cmd`, and press
     Enter to open Command Prompt already pointed at the folder. Or type
     `powershell` instead to open PowerShell.
  2. Or hold the Shift key, right-click an empty area inside the folder, and
     choose "Open PowerShell window here" (or "Open in Terminal" on
     newer Windows versions).
- macOS: open Terminal and `cd` into the folder
- Linux: open your terminal and `cd` into the folder

If you are new to terminals, think of this as simply "opening a text-based way
to run commands in a folder."

## Step 5: Know Which Tool To Use

This repo now has several tools, and each one has a different purpose.

## If You Just Want To Read One `.ks` File More Easily

Use:

- `single_ks_file_to_screenplay_converter.py`

These are good for:

- proofreading
- translation prep
- reading dialogue and flow outside TyranoBuilder
- seeing tags in a more readable format

These are not the main Ren'Py builders.

## If You Want To Know What Assets You Need

Use:

- `extract_media_inventory.py`

This creates `ALL_MEDIA.md` so you can see which backgrounds, sprites, music,
sound effects, movies, fonts, and `.ks` references exist.

## If Your Movies Do Not Play In Ren'Py

Use:

- `prepare_movies_for_renpy.py`

This helper exists because movie playback in Ren'Py is stricter than ordinary
image, audio, or font loading.

It is especially useful when:

- a Tyrano `.mp4` intro plays fine in the original project
- but the same movie does not play in desktop Ren'Py

By default it writes converted movies into `out/`, and you can point it at a
different folder with `-o` when you want to keep movie prep separate.

Important:

- this helper needs `ffmpeg` installed first
- `ffprobe` is optional, but it helps the helper explain what codecs were in the original file

Before you run the helper, open a terminal and try:

```bash
ffmpeg -version
```

If that prints version information, you are ready.

If it says the command was not found, install `ffmpeg` first.

## Step 5.5: Install `ffmpeg` If You Need The Movie Helper

You do not need `ffmpeg` for the normal script converters.

You only need it if you want to use:

- `prepare_movies_for_renpy.py`

### Windows

Beginner-friendly path:

1. Go to `https://ffmpeg.org/download.html`
2. Follow the Windows download links to a ready-made build
3. Download a normal full build ZIP
4. Extract it somewhere easy to find
5. Open the extracted folder and find its `bin` folder
6. Make sure that folder contains `ffmpeg.exe`
7. Add that `bin` folder to your Windows PATH
8. Close Command Prompt or PowerShell if it was already open
9. Open a new Command Prompt
10. Run:

```bash
ffmpeg -version
```

If Windows users are not comfortable editing PATH manually, the simplest safe
goal is still this:

- make sure a new Command Prompt can run `ffmpeg -version`

That is the only check that really matters for this helper.

### macOS

If you use Homebrew, run:

```bash
brew install ffmpeg
```

Then verify with:

```bash
ffmpeg -version
```

### Linux

Use your package manager, then verify with:

```bash
ffmpeg -version
```

### What About `ffprobe`?

Many `ffmpeg` installs also include `ffprobe` automatically.

That is helpful, but not required.

If you want to check it too, run:

```bash
ffprobe -version
```

## If You Want To Convert One `.ks` File Into Ren'Py

Use:

- `single_ks_file_to_renpy_script_converter.py`

This is the simplest Ren'Py converter.

Its job is to:

- take one `.ks` file
- convert a safe subset of it
- produce a starter Ren'Py `game/` scaffold

This is a good choice when you want to experiment with one scene or chapter.

## If You Want The Fullest Current Project Scaffold (Recommended For Whole Projects)

Use:

- `tyranobuilder_to_renpy_project.py`

This is the highest-level tool in the repo and the recommended starting point
for almost every whole-project migration.

It:

- calls the scenario converter automatically
- reads `data/system/Config.tjs`
- generates `options.rpy`, `gui.rpy`, and `screens.rpy`
- generates `keymap.rpy` for safe partial Tyrano keymap import
- creates empty target asset directories
- writes media/config planning docs
- rewrites startup flow so the converted Tyrano title/menu can replace Ren'Py's stock main menu
- can promote a startup-only intro movie into Ren'Py `splashscreen` when that looks safe from the converted title structure

Current keymap behavior is intentionally conservative:

- `Escape` stays the Ren'Py menu key
- more unusual Tyrano input behavior such as virtual mouse, gesture, and advanced gamepad mappings is still deferred

If you want the strongest current starting point for a whole project, this is
the tool to use.

## If You Want One Merged `.ks` File From A Whole Project

Use:

- `tyranobuilder_scenario_to_single_ks_file.py`

This tool:

- starts from a TyranoBuilder project root or `data/scenario/`
- uses `first.ks` as the default starting point when present
- follows reachable non-system `.ks` files
- writes one merged `.ks` file while keeping each source file intact
- adds file-boundary comments so you can still tell where each original file came from
- uses branch-following `dfs` order by default so one route stays grouped before the next
- can use `--order sorted` if you prefer deterministic filename ordering instead

This is useful when you want a single combined Tyrano script for review,
searching, or feeding into another single-file workflow.

## If You Want Only Story Script `.rpy` Files (Advanced)

> **Most users should NOT use this tool. Use `tyranobuilder_to_renpy_project.py` instead.**
>
> This tool produces an incomplete Ren'Py game folder that will not launch
> correctly on its own. It exists for advanced workflows where you already
> have customized `options.rpy`, `gui.rpy`, `screens.rpy`, and `keymap.rpy`
> and only want to regenerate the story flow.

Use:

- `tyranobuilder_scenario_to_renpy_script_converter.py`

**What it reads:**

- a TyranoBuilder project root, or a `data/scenario/` folder directly
- the reachable non-system `.ks` files starting from `first.ks` (or `--entry`)

**What it produces:**

- `out/game/script.rpy` (Ren'Py startup wiring)
- `out/game/story/*.rpy` (per-source-file converted scenes)
- `out/game/characters.rpy`
- `out/game/images.rpy`
- `out/game/transitions.rpy`
- `out/game/route_map.md`
- `out/game/conversion_warnings.md`

**What it does NOT produce:**

- `options.rpy`, `gui.rpy`, `screens.rpy`, `keymap.rpy`
- `NEEDED_MEDIA.md`, `ASSET_MIGRATION_PLAN.md`, `PROJECT_CONFIG_MAPPING.md`,
  `DIRECTORY_SCAFFOLD.md`
- empty asset directories

If you copy only this tool's output into a Ren'Py project, critical config
files will be missing and the game will not launch correctly. Use
`tyranobuilder_to_renpy_project.py` instead unless you have a specific reason
to regenerate only the story flow.

## Step 6: Understand What The Tools Generate

## Single-file Ren'Py converter output

When you run:

```bash
python3 single_ks_file_to_renpy_script_converter.py examples/TyranoBuilder.ks -o out
```

you get a generated `game/` folder like:

- `out/game/script.rpy`
- `out/game/characters.rpy`
- `out/game/images.rpy`
- `out/game/transitions.rpy`
- `out/game/filename_map.md`
- `out/game/conversion_warnings.md`

What those mean:

### `game/script.rpy`

This is the main converted script.

It contains things like:

- labels
- dialogue
- narration
- jumps and calls
- scene changes
- music and sound

In scenario and project conversions, this file may also:

- bypass Ren'Py's built-in main menu
- jump straight into the converted Tyrano title flow
- play a startup movie once in `splashscreen` before showing the converted title menu

### `game/characters.rpy`

This defines Ren'Py speakers, for example:

```renpy
define spina = Character("Spina")
```

### `game/images.rpy`

This defines image names and file paths, for example:

```renpy
image bg_asset forest = "images/backgrounds/forest.png"
```

### `game/transitions.rpy`

This contains generated transitions used for supported effects, such as current
`quake` support.

### `game/filename_map.md`

This helps you compare source names to generated Ren'Py names.

### `game/conversion_warnings.md`

This is one of the most important output files.

It tells you:

- which tags were unsupported
- which behaviors were approximated
- which lines still need review
- which font names or external references need manual checking

Do not skip this file.

## Project-builder output (recommended)

When you run:

```bash
python3 tyranobuilder_to_renpy_project.py path/to/your-project -o out
```

you get the fullest scaffold, including:

- `out/game/script.rpy`
- `out/game/story/...`
- `out/game/options.rpy`
- `out/game/gui.rpy`
- `out/game/screens.rpy`
- `out/game/keymap.rpy`
- `out/game/characters.rpy`
- `out/game/images.rpy`
- `out/game/transitions.rpy`
- `out/game/PROJECT_CONFIG_MAPPING.md`
- `out/game/NEEDED_MEDIA.md`
- `out/game/NEEDED_MEDIA_RAW.json`
- `out/game/ASSET_MIGRATION_PLAN.md`
- `out/game/DIRECTORY_SCAFFOLD.md`

This is the best current output for a whole project.

## Scenario-converter output (advanced; partial scaffold)

When you run:

```bash
python3 tyranobuilder_scenario_to_renpy_script_converter.py path/to/your-project -o out
```

you get a generated `game/` scaffold that includes:

- `out/game/script.rpy`
- `out/game/story/...`
- `out/game/characters.rpy`
- `out/game/images.rpy`
- `out/game/transitions.rpy`
- `out/game/route_map.md`
- `out/game/conversion_warnings.md`

> **Note:** this output is missing `options.rpy`, `gui.rpy`, `screens.rpy`, and
> `keymap.rpy`. A Ren'Py game built only from this output will typically fail
> to launch correctly. Use `tyranobuilder_to_renpy_project.py` (above) to get
> the full set, unless you have a specific reason to regenerate only the story
> flow.

## Common Pitfall: TyranoBuilder "Preview From Here" Replaces `first.ks`

When you click "Preview from here" inside the TyranoBuilder editor,
TyranoBuilder writes a `_preview.ks` file and rewrites `first.ks` so the
in-editor preview launcher can start mid-scene. If you then export, copy, or
hand off that project without restoring `first.ks`, every tool in this
toolkit that walks the scenario from the default entry point will only see
the tiny preview snippet, not your real game.

This affects:

- `tyranobuilder_to_renpy_project.py`
- `tyranobuilder_scenario_to_renpy_script_converter.py`
- `tyranobuilder_scenario_to_single_ks_file.py`

When the converters detect this, they emit a `preview_entry_detected`
warning inside the generated warnings report (`conversion_warnings.md` for
the project builder and scenario converter, `merge_warnings.md` for the
single-`.ks` merger). Open that file first if your generated output looks
unexpectedly small or only covers a single scene.

Two ways to recover:

1. Re-export your TyranoBuilder project so `first.ks` is restored to its
   bootstrap state, then re-run the converter.
2. Or pass `--entry title_screen.ks` (or whatever your real entry file is
   named) to skip the preview artifact, for example:

```bash
python3 tyranobuilder_to_renpy_project.py path/to/your-project --entry title_screen.ks
```

Note that bypassing `first.ks` also skips its system-library bootstrap
(layer setup, character defines, plugins). The converter already filters
`system/*.ks` out of traversal, so the bootstrap was not contributing
scenario content, but if you have any non-system setup inside `first.ks` you
will need to move it into your overriding entry file.

Once your project is migrated, see
[How To Preview A Specific Scene In Ren'Py](#how-to-preview-a-specific-scene-in-renpy)
below for Ren'Py's equivalent workflows.

## How To Preview A Specific Scene In Ren'Py

If you came from TyranoBuilder, you may miss the right-click "Preview from
here" workflow once you are inside Ren'Py. Ren'Py does not have a single
equivalent button, but it ships three official mechanisms that together
cover the same goal. The `preview_entry_detected` warning above is about
Tyrano-side preview leakage into the conversion; this section is about how
to reach the equivalent workflow inside Ren'Py once your project is
converted.

All three workflows require developer mode (`config.developer = True`).
Ren'Py defaults `config.developer` to `"auto"`, which means it is on
automatically when you launch your project from the Ren'Py launcher during
development, and off automatically in built distributions. The generated
`options.rpy` does not override that default, so you get developer mode
for free while you are working and lose it for free when you ship.

### 1. Shift+O Console: Jump To Any Label

Press `Shift+O` while the game is running to open Ren'Py's debug console,
then type:

```
jump some_label_name
```

This is the closest match for "preview from here" when your scene boundary
lines up with a label. Our converters generate labels per source file and
per Tyrano `*labelname`, so most converted scenes are reachable this way.

The console also supports `reload`, `load <slot>`, `save <slot>`,
`watch <expression>`, and arbitrary Python expressions. The full command
list is in Ren'Py's Developer Tools documentation at
`https://www.renpy.org/doc/html/developer_tools.html`.

### 2. `--warp` From The Command Line: Line-Precise Preview

Launch Ren'Py from the command line with the `--warp` flag pointing at a
file and line number:

```bash
renpy.exe path/to/your-project --warp game/story/chapter2.rpy:140
```

On macOS or Linux, use `renpy.sh` from your Ren'Py SDK folder instead of
`renpy.exe`. The Ren'Py launcher GUI does not currently expose `--warp`,
so this workflow is command-line only.

Ren'Py finds the closest reachable statement at or before that line, walks
back through `scene`, `show`, and `hide` statements until it finds a
`scene` statement, executes that path, then transfers control to the
warped-to statement. This is the closest mechanical analogue to "Preview
from here", but it has real caveats.

Important caveats, taken from Ren'Py's own documentation:

- It only examines a single path, so it may miss bugs along other routes.
- The path does not consider game logic, so it is possible to land on a
  statement that is not actually reachable in normal play.
- Python is not executed before the warped-to statement, so all variables
  will be uninitialized and the game can crash when they are used.

To work around the variable problem, define an `after_warp` label that
initializes the variables your previewed scene needs. Ren'Py calls it
after the warp but before the warped-to statement:

```renpy
label after_warp:
    $ player_name = "Velo"
    $ chapter = 2
    return
```

### 3. Shift+R Reload: Tight Edit-Test Loop

While the game is running, `Shift+R` saves, reloads the script, and
resumes from approximately the last unchanged statement. After the first
reload, Ren'Py enters autoreload mode and reloads again on any future
script-file change. This is the workflow you want when you are editing
dialogue or fixing small mistakes and want to see the result without
manually relaunching.

One gotcha: game state (variable values, shown images, queued audio, and
so on) is preserved across the reload. If your edit changed an earlier
statement, you may need to roll back past that statement so the new
version actually runs.

`Shift+R` reloading does not work during a replay.

### Developer Menu

Pressing `Shift+D` opens the Ren'Py Developer Menu, which is a UI
front-end for several of the tools above. It is convenient if you do not
want to memorize individual shortcuts.

### Sources

- Ren'Py Developer Tools: `https://www.renpy.org/doc/html/developer_tools.html`
- Customizing the Keymap (default key bindings): `https://www.renpy.org/doc/html/keymap.html`
- Labels & Control Flow (`after_warp` special label): `https://www.renpy.org/doc/html/label.html`

## Important Note About Output Folders

All tools now default to writing generated local outputs into `out/` unless you
override the destination with `-o`.

They are for local testing, comparison, and review.

They are not meant to be permanent shipped repo content.

## Step 7: Copy The Right Files Into A Ren'Py Project

Inside a Ren'Py project, the important folder is usually `game/`.

For beginners, the easiest rule is:

- copy the generated contents of the tool's `game/` folder into your Ren'Py project's `game/` folder

Example:

- `out/game/...` -> `your_project/game/...`

### Why `script.rpy` matters

A fresh Ren'Py project already includes a very simple `game/script.rpy`.

Our generated tools also produce `game/script.rpy` on purpose.

That means:

- the generated `script.rpy` is meant to replace the starter `script.rpy`
- if you do not overwrite the starter one, Ren'Py may keep launching the default sample content instead of your converted story

For project and scenario conversions, `script.rpy` may also be doing startup work
that is easy to miss at first.

It may:

- skip Ren'Py's stock main menu on purpose
- play a startup movie once in `splashscreen`
- jump into the converted Tyrano title screen instead of ordinary story text

That is expected for ports where the original Tyrano project already had its own
title screen flow.

Example generated startup file:

```renpy
label main_menu:
    return

label splashscreen:
    $ renpy.movie_cutscene("movies/intro.mp4")
    return

label start:
    jump title_screen__post_op
```

## Step 8: Copy Your Assets

The generated `.rpy` files are only part of the work.

You still need the actual:

- backgrounds
- sprites
- music
- sound effects
- movies
- fonts

Use:

- `ALL_MEDIA.md`
- `NEEDED_MEDIA.md`
- `ASSET_MIGRATION_PLAN.md`
- `conversion_warnings.md`

to understand what you still need.

For movies specifically, also remember:

- some Tyrano `.mp4` files may need conversion before Ren'Py desktop playback will work reliably
- if that happens, run `prepare_movies_for_renpy.py` and test the converted `.webm` output
- if the helper says `ffmpeg` was not found, install it first and then open a new terminal before trying again

## A Beginner-Friendly Asset Layout

If you are not sure how to organize a Ren'Py project yet, this is a simple place
to start:

- `game/images/backgrounds/`
- `game/images/character/`
- `game/images/ui/`
- `game/audio/bgm/`
- `game/audio/sfx/`
- `game/movies/`
- `game/fonts/`

The project builder already creates these directories as empty folders.

If a movie still does not play after you copied it into `game/movies/`, the file
format may be the real problem rather than the folder path.

That is the main reason `prepare_movies_for_renpy.py` exists.

## Matching Paths To Real Files

If a generated line says:

```renpy
image bg_asset forest = "images/backgrounds/forest.png"
```

but your actual file lives at:

`game/images/backgrounds/forest.png`

then you should update it to:

```renpy
image bg_asset forest = "images/backgrounds/forest.png"
```

The same thing applies to music, sound, movies, and fonts.

## Fonts Need Special Attention

If Tyrano uses a face name like `GhoulFriAOE`, the converter may assume a file
name like:

- `fonts/GhoulFriAOE.ttf`

That assumption is useful, but it still needs to be checked by you.

So if you see a warning about a font face mapping, it means:

- the converter made a reasonable guess
- but you still need to make sure the real font file exists and is in the right place

## What The Current Converters Already Handle

Useful current support includes:

- labels
- narration and dialogue
- speaker switches
- `[l]` -> `{w}`
- `[r]` -> line break
- `[p]` -> next say block
- `cm` as a transient message/window clear boundary
- persistent `font` / `resetfont` styling across dialogue sections
- `jump`, `call`, `return`
- `if`, `elsif`, `else`, `endif`
- `bg`
- `chara_show`, `chara_mod`, `chara_hide`
- `playbgm`, `stopbgm`, `playse`
- simple horizontal or vertical `quake`
- `wait`

That is enough to produce a real starting point, but not a finished game.

## What Still Needs Manual Work

Expect manual work for things like:

- advanced UI recreation
- graphical choice buttons
- clickable regions
- speech bubble systems
- floating text systems
- backlog/message-layer details
- JavaScript-driven logic
- plugin behavior
- some system-scene behavior
- asset copying and final path cleanup

## What `TODO TYRANO` Means

If you see comments like:

```renpy
# TODO TYRANO: unsupported tag: [quake time="300" count="3"]
```

that means:

- the converter noticed something important
- it did not silently remove it
- it still needs manual review or a future conversion pass

Those comments are not failures. They are guideposts.

## How `cm` Works Right Now

The current converters treat Tyrano `cm` as a transient message/UI cleanup
boundary.

In practice that means:

- the current dialogue window is cleared or hidden
- the next scene or menu state starts fresh

If later script logic needs a temporary menu or UI to appear again, that later
logic must show it again explicitly.

So no, cleared temporary UI does not magically come back on its own.

## How To Launch The Ren'Py Project

1. Open the Ren'Py launcher
2. Create a fresh Ren'Py project if needed
3. Copy the generated `game/` contents over the project's `game/` folder
4. Copy needed assets into the right folders
5. Click `Launch Project`

If there is a problem, Ren'Py usually tells you:

- which file broke
- what line number broke
- what kind of problem it found

That is normal and helpful.

## Your First Safe Edits

If you are new to Ren'Py, start small.

### Change dialogue

Before:

```renpy
spina "Hello there."
```

After:

```renpy
spina "Hello there, Velo."
```

### Change a display name

Before:

```renpy
define spina = Character("Spina")
```

After:

```renpy
define spina = Character("Spina Aster")
```

### Change an image path

Before:

```renpy
image bg_asset forest = "images/backgrounds/forest.png"
```

After:

```renpy
image bg_asset forest = "images/backgrounds/forest.png"
```

Then save and launch the project again.

## Recommended Beginner Workflow

If you want the least confusing path:

1. download the repo ZIP
2. install Python
3. make a copy of your TyranoBuilder project
4. run `extract_media_inventory.py`
5. if your project uses movies, run `prepare_movies_for_renpy.py`
6. run `tyranobuilder_to_renpy_project.py`
7. inspect `out/game/`
8. copy that `game/` output into a fresh Ren'Py project
9. copy assets into the scaffolded folders
10. launch the Ren'Py project
11. fix warnings one by one

## Final Advice

- use the generated files as a starting point, not a final game
- trust the warning files and review markers
- keep your original Tyrano files untouched
- test often
- fix one class of problem at a time

The goal is not instant perfection.

The goal is getting from:

- "I only had a TyranoBuilder project"

to:

- "I now have a real Ren'Py project scaffold that I can open, test, and improve"

That is already a huge step forward.
