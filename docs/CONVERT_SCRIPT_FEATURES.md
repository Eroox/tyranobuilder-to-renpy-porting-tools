# Supported Conversion Features

This document summarizes what the current tools can read, preserve, or convert
from TyranoBuilder and TyranoScript projects.

The tools are meant to produce useful migration outputs, not a finished Ren'Py
game. Expect to review generated warnings and make manual edits for advanced UI,
plugins, JavaScript-heavy logic, and exact visual polish.

## Output Layers In The Screenplay Converter

`single_ks_file_to_screenplay_converter.py` always emits readable dialogue,
narration, chapters, and scene headings. Optional flags add more migration detail:

- `-p`: include inline pause markers for `[l]`.
- `-m`: include panel/page markers for `[p]`.
- `-n`: include readable staging and non-dialogue action cues.
- `-f`: include structural flow, branching, calls, jumps, and choices.
- `-c`: include message-flow and state-control markers.
- `-g`: include lower-level engine, UI, plugin, and runtime details.

Use the default output when you want a clean script for reading or proofreading.
Add flags when you want a migration audit with more technical context.

## Status Key

- `Supported`: implemented and intentionally surfaced.
- `Partial`: represented, but with known limitations or approximations.
- `Placeholder`: preserved in a readable fallback form, not fully modeled.

## Feature Matrix

| Feature family | Example tags | Status | Output flag | Current behavior | User note |
| --- | --- | --- | --- | --- | --- |
| Labels and chapter markers | `*label` | Supported | default | Top-level labels become chapter markers. | Useful for navigation and proofreading. |
| Speaker attribution | `#speaker`, `#` | Supported | default | Speaker lines become dialogue block speakers. | Blank `#` falls back to narration. |
| Text block wrappers | `tb_start_text`, `_tb_end_text` | Supported | default | Dialogue and narration are extracted from TyranoBuilder text blocks. | Core path for TyranoBuilder exports. |
| Inline flow tokens | `l`, `p`, `r` | Supported | default / `-p` / `-m` | Pause, panel, and line-break tokens are preserved or split into readable output. | Important for pacing review. |
| `@tag` syntax | `@bg`, `@jump` | Supported | relevant flags | `@tag` lines are parsed like bracket tags. | Useful for broader TyranoScript compatibility. |
| Scene headings | `bg` | Supported | default / `-n` | Background changes can become scene headings and action cues. | `cond` text is preserved where available. |
| Action cues | `playbgm`, `quake`, `chara_show`, `movie` | Supported | `-n` | Common staging tags become readable action lines. | Helps identify music, sprites, effects, and movies. |
| Flow control | `jump`, `call`, `return`, `if`, `else` | Supported | `-f` | Flow tags become explicit markers. | Helps audit routes and cross-file movement. |
| Choices | `link`, `glink`, `button`, `clickable` | Supported | `-f` | Choices are grouped into `CHOICE:` blocks where possible. | Visual layout still needs manual Ren'Py work. |
| Macro and ignore flow | `macro`, `endmacro`, `ignore`, `endignore`, `clearstack` | Supported | `-f` | Macro and ignored sections are surfaced as flow markers. | Useful for migration review. |
| Message flow | `current`, `cm`, `ct`, `er`, `delay`, `nowait`, `nolog` | Supported | `-c` | Message-layer and reading-flow tags become control-like action lines. | Review these when timing or backlog behavior matters. |
| Stateful control | `eval`, `clearvar`, `sleepgame`, `awakegame`, `breakgame` | Supported | `-c` | State-changing tags are preserved as markers. | JavaScript expressions are not executed. Review manually. |
| Engine detail | `clearsysvar`, `plugin`, `loadjs`, `iscript`, `endscript`, `glink_config`, `erasemacro` | Supported | `-g` | Lower-level details are de-emphasized as engine notes. | Useful for audits, usually noisy for casual reading. |
| Inline ruby | `ruby` | Partial | default | Ruby text attaches to a likely target character or token. | Heuristic output may need review. |
| Inline image placeholder | `graph` | Placeholder | default | Rendered as `[INLINE_IMAGE: ...]`. | Preserves intent without layout fidelity. |
| Inline highlight placeholder | `mark`, `endmark` | Partial | default | Rendered as a readable marked span. | Styling is not final Ren'Py behavior. |
| Inline expression placeholder | `emb` | Placeholder | default | Rendered as `[EMBED: ...]`. | Dynamic expression needs manual review. |
| Visible text systems | `ptext`, `mtext`, `fuki_start`, `fuki_chara`, `fuki_stop` | Supported | `-n` | Visible text and speech-bubble cues are surfaced as action lines. | UI recreation is still manual. |
| Cross-file target linking | `jump storage=...`, `call storage=...` | Partial | `-f` | Targets are normalized into readable links or labels. | Good for review; exact project routing may still need cleanup. |
| Universal `cond` preservation | `cond` on tags | Partial | varies | Conditions are preserved on many surfaced outputs. | Review conditional logic before assuming route parity. |
| Script blocks | `iscript`, `endscript` | Partial | `-g` | Block contents are preserved, not executed. | Translate JavaScript manually if needed. |
| UI/system customization | `glyph`, `body`, `title`, `sysview`, `dialog_config`, `showmenubutton` | Supported | `-g` | Preserved as lower-level engine or UI notes. | Usually requires custom Ren'Py screens or manual styling. |
| Browser/HTML behavior | `showsave`, `showload`, `showmenu`, `showlog`, `web`, `html`, `endhtml`, `loadcss` | Supported | `-g` | Preserved as engine/browser notes; HTML blocks keep enclosed lines. | Stock Ren'Py may not have direct equivalents. |
| 3D and AR families | `3d_*`, `bgcamera`, `qr_config`, `qr_define` | Supported | `-g` | Preserved as lower-level audit notes. | Manual design work is expected if the project depends on these. |

## Current Strengths

- Dialogue, narration, speaker changes, labels, and background changes are readable.
- Branching, choices, calls, jumps, and target hints can be surfaced for review.
- State-risk tags such as `eval`, `clearvar`, and `sleepgame` are not silently dropped.
- Engine and plugin details can be inspected without cluttering normal script exports.
- Common staging cues such as music, sound, sprites, movies, waits, and shakes are visible.

## Known Limits

- `ruby` handling is heuristic rather than a full text-span model.
- `graph`, `emb`, and some marked text are placeholders, not final layout behavior.
- `ptext`, `mtext`, and `fuki_*` are surfaced as cues, not rebuilt as Ren'Py UI.
- Cross-file links are readable but may still need manual cleanup in complex projects.
- Conditional logic is preserved for review, but JavaScript expressions are not executed.
- Plugin behavior, HTML/browser hooks, 3D, AR, and advanced UI systems need manual work.

## Ren'Py Converter Expectations

The Ren'Py converters are safe-subset migration helpers. They aim to produce a
starter `game/` scaffold that can be opened, inspected, and improved.

Currently useful Ren'Py conversion support includes:

- labels, narration, dialogue, and speaker definitions
- scene and image declarations for common background and sprite references
- jumps, calls, returns, and basic conditional structure
- basic choice reconstruction where the source structure is clear
- music and sound playback markers
- simple horizontal or vertical `quake` effects
- persistent font styling for supported fields such as size, color, face, bold, and italic
- generated warning reports for unsupported or approximate behavior

Generated Ren'Py output should be treated as a starting point. Always review
`conversion_warnings.md`, copy needed assets, and test in a fresh Ren'Py project.

## When To Use Extra Screenplay Flags

For a clean reading copy:

```bash
python3 single_ks_file_to_screenplay_converter.py path/to/script.ks -o out
```

For a migration audit with pauses, page breaks, action cues, and flow markers:

```bash
python3 single_ks_file_to_screenplay_converter.py path/to/script.ks -o out -p -m -n -f
```

For deeper engine and message-layer review:

```bash
python3 single_ks_file_to_screenplay_converter.py path/to/script.ks -o out -p -m -n -f -c -g
```

The more flags you enable, the noisier the output becomes. That is useful for
audits, but less useful for casual reading.
