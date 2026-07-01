# Migrating From 0.4.2 To 0.5.0

This guide is for users who already ran the porting tools at version `0.4.2`
and want to upgrade to `0.5.0` without regenerating everything from scratch.

If you are running the tools for the first time, you can skip this whole
document. Nothing here applies to a clean run.

## What Changed In 0.5.0

The generated Ren'Py project layout uses new folder names and a slightly
different `options.rpy`. The story files themselves keep working, but a few
paths and files were renamed.

Summary of the changes that affect an existing `0.4.2` output tree:

- Music folder renamed from `game/audio/bgm/` to `game/audio/music/`.
- Character sprite folder renamed from `game/images/character/` to
  `game/images/characters/`.
- Character sprite subfolders now use the character name instead of the
  original Tyrano number, for example `characters/eileen/smile.png`
  instead of `character/1/smile.png`.
- `game/transitions.rpy` was renamed to `game/custom_effects.rpy`
  (this rename was introduced during the `0.5.0` cycle).
- `game/options.rpy` no longer defines `config.history_length`. That
  setting now lives only in `game/gui.rpy`, which is where Ren'Py
  expects it.
- `game/options.rpy` now ships a fuller build classification block with
  active `archive` rules for images, audio, fonts, movies, and compiled
  scripts.

## Recommended Path: Regenerate

The safest way to move to `0.5.0` is to re-run the project builder on
your Tyrano project. This will produce a fresh Ren'Py project with the
new folder names, the new `options.rpy`, and the reorganized
`images.rpy` for free.

If you have hand-edited any of the generated files, copy those edits into
the freshly generated versions afterward.

### Even Easier: Let `0.5.0` Copy The Assets For You

`0.5.0` adds a new `-m` (or `--migrate-assets`) flag to
`tyranobuilder_to_renpy_project.py`. When you point it at a real
TyranoBuilder project root, it will copy each referenced asset from your
Tyrano `data/` folders into the correct spot in the generated Ren'Py
`game/` tree, using the new folder names automatically.

```bash
python3 tyranobuilder_to_renpy_project.py path/to/your-project -o out --migrate-assets
```

This also handles fonts referenced by `[font face="..."]` (copied into
`game/fonts/` using the on-disk file suffix) and UI art referenced by
`[button graphic=... enterimg=...]` or `[clickable _clickable_img=...]`
(copied into `game/images/ui/` while preserving the relative subpath).

Existing destination files are always skipped, so you can safely re-run
the command. A summary lands in `out/game/ASSET_MIGRATION_REPORT.md`.

## Manual Migration Path

If you would rather patch your existing `0.4.2` output in place, follow
these steps inside your Ren'Py `game/` folder.

### 1. Rename The Music Folder

Rename `game/audio/bgm/` to `game/audio/music/`.

Then update any `play music "audio/bgm/..."` lines in your story `.rpy`
files to use `audio/music/...` instead. A project-wide find and replace
for `audio/bgm/` to `audio/music/` is usually enough.

### 2. Rename The Character Sprite Folder

Rename `game/images/character/` to `game/images/characters/`.

If you kept the numbered subfolders like `character/1/`, you can rename
them to the matching character name, for example `characters/eileen/`.
If you do that, also update the paths inside `game/images.rpy` so the
`image ... = "images/characters/<name>/..."` lines point at the new
folders.

If you are not ready to switch to character-named subfolders, just
keeping the numeric ones under `game/images/characters/` still works.

### 3. Rename `transitions.rpy` To `custom_effects.rpy`

If you have a generated `game/transitions.rpy` from an older run, rename
it to `game/custom_effects.rpy`. The story files reference the same
`with tyrano_hpunch_*` names, so nothing else needs to change.

### 4. Update `options.rpy`

You have two easy options:

- The clean option: replace your existing `game/options.rpy` with a
  freshly generated one from `0.5.0`. If you had customized anything,
  copy those edits back in afterward.
- The minimal option: remove the `define config.history_length = ...`
  line from `game/options.rpy`. The value already lives in
  `game/gui.rpy` and Ren'Py will pick it up from there.

If you want the new build classification block (with `archive` rules for
images, audio, fonts, movies, and compiled scripts), the clean option is
easier than editing it in by hand.

### 5. Re-Check Your `images.rpy`

`0.5.0` sorts `game/images.rpy` into a Background Images section and a
Character Sprites section, each in alphabetical order. If you generate a
fresh `images.rpy` from `0.5.0`, the file will look different, but the
actual image definitions still match the same asset filenames.

If you kept your old `images.rpy` and only renamed folders on disk,
double-check that the paths inside it still match where the files
actually live.
