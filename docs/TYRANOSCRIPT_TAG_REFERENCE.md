# TYRANOSCRIPT TAG REFERENCE

This document is a compact project reference for this repository.

It is not a full replacement for the official TyranoScript tag manual at
`https://tyrano.jp/tag`. Instead, it summarizes the tags and syntax that matter
most for script extraction, text conversion, and future Ren'Py migration work.

## Purpose

Use this file when deciding how `single_ks_file_to_screenplay_converter.py` and future converter
scripts should interpret TyranoBuilder or TyranoScript input.

This reference is meant to answer:

- which tags affect readable script output
- which tags should become action lines or scene markers
- which tags change branching or story structure
- which tags can be ignored for early text-only conversion

## Core script structures

These are not all standard tags, but they are important to the current parsing
model used in this repo.

### Standard Tyrano project layout

The official tutorial uses a project root with these top-level entries:

- `index.html`
- `data/`
- `tyrano/`

The main game content normally lives under `data/`.

Important standard subfolders mentioned in the official tutorial:

- `data/scenario/` for `.ks` scenario files
- `data/bgimage/` for backgrounds
- `data/fgimage/` for foreground and character images
- `data/image/` for other images such as buttons or inline graphics
- `data/bgm/` for music
- `data/sound/` for sound effects
- `data/video/` for movie files
- `data/system/` for config such as `Config.tjs`
- `data/others/` for miscellaneous files

Important migration note:

- the official beginner tutorial opens `data/scenario/first.ks` as the starter
  scenario file
- this strongly suggests `first.ks` is the standard beginner entry script for a
  typical Tyrano project
- a project-level TyranoBuilder-to-Ren'Py converter should treat
  `data/scenario/` as the default scenario root and should prefer `first.ks` as
  the default entry file when present

### Labels and chapter-like markers

- `*label_name`
- Used for labels and jump targets in TyranoScript
- The current converter treats top-level `*...` lines as chapter markers

### Speaker lines

- `#CharacterName`
- Usually changes the active speaker for following dialogue lines
- The current converter maps this to the `speaker` field of a dialogue block

### Text block wrappers seen in TyranoBuilder exports

- `[tb_start_text ...]`
- `[_tb_end_text]`
- These surround dialogue or narration blocks in the current sample script
- The current converter only emits dialogue while inside these wrappers

### Inline text control tokens

- `[l]` = click wait
- `[p]` = click wait plus page break
- `[r]` = line break
- These are currently the only inline tokens the converter handles inside text
- Current single-file Ren'Py converter mapping:
  - `[l]` -> Ren'Py `{w}`
  - `[r]` -> newline inside the same say string
  - `[p]` -> split into a new say block rather than Ren'Py `{p}`

Conversion note:

- for this project, Ren'Py `{p}` is not treated as a direct match for Tyrano
  `[p]`
- the current converter treats Tyrano `[p]` more like a dialogue-block split,
  while Ren'Py `{p}` is closer to a paragraph break plus wait behavior

### Tag syntax variants

- `[tag attr="value"]`
- `@tag attr="value"`
- The official docs note that lines starting with `@` are also tags
- `@tag` lines can contain only one tag per line
- The current screenplay converter handles both bracketed tags and `@tag` lines

### Comments

- `; comment`
- Block comments use `/*` and `*/` on their own lines
- The converter should ignore these safely

### Parsing rules from the official docs

- all tags can use a `cond` attribute for conditional execution
- leading spaces at the start of a text line are not preserved by default
- use a leading `_` when the source intentionally wants visible leading space
- these rules matter for both literal text extraction and branch-aware parsing

## Priority categories for conversion

The official TyranoScript reference covers many tag families. For this project,
they do not all have the same importance.

### Tier 1: structural and narrative-critical

These affect story flow and should be modeled early.

- labels and jumps
- choices and clickable branching
- conditionals
- subroutine and macro flow
- variable-driven text or embedded expressions
- text block boundaries
- speaker changes

### Tier 2: readable action cues

These do not usually change branching, but they matter for understanding scenes
in extracted script output.

- background changes
- character show, hide, move, and expression changes
- audio playback and stops
- waits, shakes, transitions, video cues
- message window visibility and basic text styling changes
- visible text emitted outside the normal message window

### Tier 3: inline text semantics

These appear inside dialogue or narration and may need a text-safe fallback.

- inline images
- ruby text
- highlighted or marked text
- embedded expressions

### Tier 4: lower priority for text conversion

These may matter later for full migration work, but are lower priority for the
current script-to-text pipeline.

- system UI customization
- save or load screens
- HTML injection
- plugin loading
- 3D features
- AR features

## High-level official categories

The V6 docs group tags into these broad areas:

- message and text
- message settings
- labels, jumps, and choices
- character control
- images, backgrounds, and layers
- effects, filters, and video
- animation
- camera
- system control
- system design and UI
- menu and HTML display
- macros, branching, and subroutines
- variables, JavaScript, and file loading
- audio
- voice and speech
- input forms
- 3D
- AR

## Current converter support

`single_ks_file_to_screenplay_converter.py` supports separate action, flow, and
message-control flags plus better handling for links and inline semantic tags.

### Explicitly supported now

- `[tb_start_text]` starts a text block
- `[_tb_end_text]` ends a text block
- `*label` becomes a chapter-like marker
- `#speaker` changes the active speaker
- `[bg ...]` creates a new scene heading using the `storage` value
- `[l]`, `[p]`, and `[r]` are parsed as inline text tokens

### Supported as optional action lines

When `--include-non-dialogue` is enabled, the current converter can emit action
lines for a much broader staging set, including tags such as:

- `playbgm`
- `stopbgm`
- `fadeinbgm`
- `fadeoutbgm`
- `xchgbgm`
- `playse`
- `stopse`
- `bg`
- `bg2`
- `image`
- `freeimage`
- `wait`
- `quake`
- `trans`
- `wt`
- `chara_show`
- `chara_hide`
- `chara_mod`
- `chara_move`
- `chara_face`
- `chara_part`
- `chara_new`
- `chara_config`
- `chara_hide_all`
- `movie`
- `bgmovie`
- `font`
- `deffont`
- `resetfont`
- `position`
- `layopt`
- `locate`
- `camera`
- `wait_camera`
- `tb_show_message_window`
- `tb_hide_message_window`
- `hidemessage`
- `ptext`
- `mtext`
- `fuki_start`
- `fuki_chara`
- `fuki_stop`
- `jump`

See [Supported Conversion Features](CONVERT_SCRIPT_FEATURES.md) for the fuller
flag-family matrix and current coverage notes.

### Current limitations

- many engine and plugin tags are still treated as unsupported or low-priority detail
- inline semantics are preserved with placeholders, but the converter does not fully model final engine behavior
- common choices are grouped, but the converter does not yet reconstruct visual UI layout or execute branching logic

## Recommended handling rules

These rules are meant to keep conversion behavior deterministic and readable.

### Structural tags

Represent these explicitly in parsed output.

Important tags:

- `jump`
- `link` / `endlink`
- `glink`
- `glink_config`
- `button`
- `clickable`
- `if` / `elsif` / `else` / `endif`
- `call` / `return`
- `macro` / `endmacro`
- `clearstack`
- `erasemacro`
- `ignore` / `endignore`
- `sleepgame` / `awakegame` / `breakgame`

Recommended behavior:

- preserve target labels and conditions verbatim
- emit explicit action or branch markers in text output
- do not silently flatten branching logic

### Scene and presentation tags

Convert these into concise action lines where possible.

Important tags:

- `bg`, `bg2`, `image`, `freeimage`, `trans`, `wt`
- `layopt`, `backlay`, `free`, `locate`
- `chara_show`, `chara_hide`, `chara_mod`, `chara_move`
- `chara_face`, `chara_part`, `chara_ptext`
- `chara_new`, `chara_config`
- `tb_show_message_window`, `tb_hide_message_window`
- `position`, `font`, `resetfont`, `hidemessage`
- `camera`, `wait_camera`, `wa`

Recommended behavior:

- summarize with stable labels such as `BACKGROUND`, `CHARACTER SHOW`, or
  `WINDOW HIDE`
- preserve key identifiers like `name`, `storage`, and obvious timing values
- prefer readable summaries over raw attribute dumps when the meaning is clear

### Audio and effect tags

These should usually become action lines.

Important tags:

- `playbgm`, `stopbgm`, `fadeinbgm`, `fadeoutbgm`, `xchgbgm`
- `playse`, `stopse`, `fadeinse`, `fadeoutse`
- `bgmopt`, `seopt`, `changevol`, `pausebgm`, `resumebgm`
- `pausese`, `resumese`, `wbgm`, `wse`, `popopo`
- `wait`, `quake`, `movie`, `bgmovie`, `wait_bgmovie`, `stop_bgmovie`
- `filter`, `mask`

Recommended behavior:

- preserve filenames, buffer ids, and timing values when available
- treat them as non-dialogue action cues, not scene headings
- current Ren'Py converter direction for `quake`:
  - horizontal-only `quake` -> generated horizontal punch-style ATL transition
  - vertical-only `quake` -> generated vertical punch-style ATL transition
  - mixed-axis `quake` -> warning/TODO for now
  - `wait=false` -> warning/TODO for now

### Message flow and backlog integrity tags

These tags strongly affect how text is displayed, logged, layered, or skipped.

Important tags:

- `current`
- `cm`, `ct`, `er`
- `s`
- `deffont`, `font`, `resetfont`
- `delay`, `resetdelay`, `configdelay`
- `nowait`, `endnowait`
- `skipstart`, `skipstop`, `cancelskip`
- `autostart`, `autostop`, `autoconfig`
- `nolog`, `endnolog`, `pushlog`

Recommended behavior:

- preserve them as action markers when they change visible reading flow
- treat `current` as a possible message-layer routing change, not cosmetic noise
- treat backlog-related tags as important when reconstructing what the player can
  review later
- treat `cm` as a message-layer clear, not a flow stop
- treat `s` as a hard scenario stop that usually needs context-sensitive
  conversion rather than a plain timed pause
- current Ren'Py converter direction for `font` / `resetfont`:
  - `[font]` is treated as persistent text-style state, not a one-line inline effect
  - supported fields are currently `size`, `color`, `face`, `bold`, and `italic`
  - active style is reapplied to each emitted Ren'Py say line using say arguments such as `what_font`, `what_size`, and `what_color`
  - `[resetfont]`, `[cm]`, `[ct]`, and `[er]` reset the active font state
  - `face=` names are currently assumed to map to `.ttf` filenames and should be verified by the user

### Inline text-semantic tags

These need special handling because they can appear within prose.

Important tags:

- `graph`
- `ruby`
- `mark` / `endmark`
- `emb`
- `ptext`
- `mtext`
- `fuki_start` / `fuki_stop` / `fuki_chara`

Recommended behavior:

- do not drop them silently
- convert to readable placeholders when full fidelity is not possible
- example placeholders:
  - `[INLINE_IMAGE: heart.png]`
  - `漢{ruby:かん}`
  - `[MARK_START color=...]... [MARK_END]`
  - `[EMBED: f.score]`
  - `[PTEXT text=... layer=...]`
  - `[MTEXT text=... effect=...]`
  - `[FUKI_START]`, `[FUKI_CHARA name=...]`
- current status: `graph`, `ruby`, `mark`, and `emb` are preserved now; `ptext`,
  `mtext`, and `fuki_*` should be surfaced as readable non-dialogue cues rather
  than dropped

### State and scripting tags

These often affect what text is reachable and should be tracked even when not
fully executed by the converter.

Important tags:

- `eval`
- `iscript` / `endscript`
- `clearvar`
- `clearsysvar`
- `loadjs`
- `plugin`

Recommended behavior:

- preserve them as action lines or metadata markers
- avoid attempting JavaScript execution inside the converter
- keep conditions and expressions as source text for later review

### Tag notes for migration-critical state and UI tags

These tags deserve explicit notes because they are easy to forget during text
extraction, but they can matter a lot during a later Ren'Py migration pass.

#### `eval`

- Runs JavaScript from the `exp` attribute
- Often used for variable assignment, but can execute arbitrary JS or call
  helper functions
- Migration importance: high
- Text-converter recommendation: preserve the expression verbatim; do not try to
  execute it
- Ren'Py migration note: this usually requires manual review or translation into
  Python statements or expressions

#### `clearvar`

- Clears variables
- With an `exp`, it can clear a specific variable such as `f.flag`; without one,
  it can clear a broader set of variables
- Migration importance: high when branching depends on variable state
- Text-converter recommendation: preserve as an explicit state marker
- Ren'Py migration note: map to variable resets carefully so route logic stays
  intact

#### `clearsysvar`

- Clears system variables
- Usually affects engine-level or meta-state values rather than visible prose
- Migration importance: medium
- Text-converter recommendation: surface under a low-priority engine-detail view
  rather than normal script-reading output
- Ren'Py migration note: check whether the original project uses system vars for
  persistent progression, settings, or unlocks

#### `sleepgame`

- Saves the current game state, then moves to another scenario or label
- Later `awakegame` can restore the saved state
- Migration importance: high
- Text-converter recommendation: preserve as a structural state-transition
  marker, not a simple action cue
- Ren'Py migration note: this behaves like temporary flow suspension plus resume
  and may need custom stack-aware conversion logic

#### `awakegame`

- Restores the game state previously saved by `sleepgame`
- The restored state may include runtime context such as variables and, in some
  cases, media state depending on original behavior
- Migration importance: high
- Text-converter recommendation: preserve as a structural state-transition
  marker
- Ren'Py migration note: treat this as paired resume behavior, not a plain jump

#### `breakgame`

- Discards the suspended state created by `sleepgame`
- After this, the paused state cannot be resumed
- Migration importance: medium
- Text-converter recommendation: preserve as a state-control marker
- Ren'Py migration note: important when reconstructing temporary menus,
  overlays, or detours that are allowed to cancel their return path

#### `erasemacro`

- Deletes a previously registered macro by name
- Migration importance: low for plain text export, medium for faithful Tyrano
  behavior emulation
- Text-converter recommendation: preserve under engine-detail output unless macro
  behavior is being modeled more fully
- Ren'Py migration note: mostly relevant if macro behavior is being modeled
  systematically

#### `glink_config`

- Configures layout and presentation rules for `glink` graphical choices
- Covers placement, spacing, wrapping, and animation-related behavior for button
  display
- Migration importance: low for text extraction, medium for UI polish in final
  migration
- Text-converter recommendation: do not treat it as narrative structure; keep as
  optional UI metadata or an action/config marker
- Ren'Py migration note: usually affects screen-language styling rather than core
  branching logic

#### `cm`

- Clears all message layers
- Also clears UI or display elements emitted by tags such as `button`, `glink`,
  and `html`
- Resets font style to default settings
- Does not reset the current message layer target the same way `ct` does
- Migration importance: high for message presentation and UI cleanup
- Text-converter recommendation: preserve as an explicit message-clear control
  marker, not a generic action cue
- Ren'Py migration note: this is usually closer to clearing dialogue/UI state,
  hiding transient screens, or forcing a fresh page than to any control-flow
  statement

#### `s`

- Stops scenario execution at that point
- Often used after choices, buttons, clickable regions, title screens, or other
  interactive UI where the script should not continue automatically
- Unlike `wait`, this is not a timed pause that resumes on its own
- Migration importance: high for route flow and interactive state handoff
- Text-converter recommendation: preserve as an explicit stop marker whenever
  structural flow is being audited
- Ren'Py migration note: convert based on context:
  - after ordinary choices, it may be absorbed by `menu` behavior
  - after UI-driven interactions, it may need a `screen`, a label loop, or an
    explicit handoff rather than a plain `pause`
  - a bare `s` with no interactive escape path should be treated as a manual
    review case

## Flag-family guidance

The screenplay converter now has four optional non-dialogue buckets plus inline marker
flags.

- `-n`, `--include-non-dialogue`: readable staging and action cues
- `-f`, `--include-flow-control`: branch structure, calls, jumps, and choices
- `-c`, `--include-message-control`: message-layer and stateful reading-flow
  behavior that can affect what the player sees
- `-g`, `--include-game-engine-details`: engine, UI, plugin, and runtime details
  that are usually not useful for normal script reading

Recommended tag-family placement for debated tags:

- `-c`: `eval`, `clearvar`, `sleepgame`, `awakegame`, `breakgame`
- `-g`: `clearsysvar`, `plugin`, `loadjs`, `iscript`, `endscript`,
  `erasemacro`, `glink_config`

Implementation notes for the current converter:

- `-c` should surface state-changing tags that can alter reachable story flow
- `-g` should preserve low-value engine detail without mixing it into normal
  script-reading output
- `iscript` and `endscript` should preserve enclosed script lines under the
  engine-detail rendering style so migration audits can inspect them later

Recommended rendering style for `-g` output:

- plaintext: `// ENGINE: ...`
- Markdown: `> ENGINE: ...`
- Fountain: `[[ENGINE: ...]]`

## Priority tag shortlist

This is the most practical backlog for improving the current converter.

| Tag or pattern | Why it matters | Suggested next handling |
| --- | --- | --- |
| `@tag` syntax | Official syntax variant; currently unsupported | Parse same as bracket tags |
| universal `cond` attribute | Any tag may execute conditionally | Preserve condition text on every parsed tag |
| leading `_` on text lines | Preserves intentional indentation | Normalize carefully without dropping visible spacing |
| `link`, `glink`, `button` | Choice structure | Emit explicit `CHOICE` blocks |
| `clickable` | Choice or interactive region structure | Represent as explicit interactive marker |
| `if`, `elsif`, `else`, `endif` | Branching and conditional text | Emit conditional markers |
| `call`, `return` | Subroutine flow | Preserve as action markers |
| `macro`, `endmacro` | Script reuse and indirection | Track as macro boundaries |
| `current` | Routes text to a specific message layer | Preserve as a message-layer action marker |
| `ptext`, `mtext`, `fuki_*` | Player-visible text outside normal dialogue flow | Preserve as visible-text markers |
| `graph`, `ruby`, `mark` | Inline semantics inside text | Convert to placeholders |
| `cm`, `ct`, `er` | Message flow and resets | Emit action lines when enabled |
| `s` | Hard scenario stop, often after UI interactions | Preserve as a stop marker and review contextually for Ren'Py conversion |
| `delay`, `nowait`, `skipstart`, `autostart`, `nolog` | Affect pacing and backlog semantics | Preserve as message-flow markers |
| `chara_ptext`, `chara_face`, `chara_move`, `chara_part` | Character context and expression changes | Add readable character action lines |
| `fadeinbgm`, `fadeoutbgm`, `stopse`, `bgmovie` | Common audio and media cues | Expand action-tag coverage |
| `wbgm`, `wse`, `wait_bgmovie`, `stop_bgmovie` | Pacing and media ordering | Preserve wait or stop markers explicitly |
| `sleepgame`, `awakegame`, `breakgame` | Story-state suspension and resume flow | Preserve as state-transition markers |
| `emb`, `eval` | Dynamic text and state | Preserve expressions verbatim |
| `clearvar`, `clearsysvar` | Reset route or system state | Preserve as explicit state-reset markers |
| `erasemacro` | Changes available macro behavior | Preserve as macro-control marker |
| `glink_config` | Affects graphical choice layout | Preserve as optional UI metadata, not narrative flow |

## Suggested normalization rules

These rules should keep future converter behavior consistent.

- preserve source order unless a feature explicitly requires restructuring
- preserve jump targets, conditions, and expression text exactly when possible
- prefer concise, deterministic action labels over freeform summaries
- keep scene detection rules centralized
- treat unsupported but important tags as explicit markers, not invisible drops
- use placeholders for inline tags when full rendering is not yet implemented

## Example mapping ideas

These are not strict output requirements yet. They are working conventions.

### Choice example

Input:

```text
[link target=*accept]Yes[endlink]
[link target=*decline]No[endlink]
```

Possible text-friendly output:

```text
CHOICE:
- Yes -> *accept
- No -> *decline
```

### Conditional example

Input:

```text
[if exp="f.flag == true"]
Secret line[p]
[else]
Normal line[p]
[endif]
```

Possible text-friendly output:

```text
[IF exp="f.flag == true"]
NARRATION
Secret line

[ELSE]
NARRATION
Normal line

[ENDIF]
```

### Inline ruby example

Input:

```text
[ruby text="かん"]漢字[p]
```

Possible text-friendly output:

```text
NARRATION
漢{ruby:かん}字
```

## Future parser roadmap

Recommended order for expanding parser support:

1. add `@tag` parsing
2. expand action-tag coverage for common scene, audio, and character tags
3. add explicit choice and jump structure support
4. add conditional and subroutine markers
5. add inline semantic tag placeholders
6. decide how much macro and variable behavior should be modeled vs preserved

## Ren'Py conversion map

This section cross-checks the TyranoScript tag families above against official
Ren'Py documentation so future conversion work is grounded in real destination
features, not assumptions.

### Core story flow

TyranoScript concepts in this area map cleanly to standard Ren'Py script.

- dialogue and narration -> Ren'Py `say` statements
- labels and jumps -> `label`, `jump`
- subroutines -> `call`, `return`
- branching -> `if`, `elif`, `else`
- choices -> `menu`
- variables and expressions -> `$` statements, `default`, and `python:` blocks
- embedded dynamic text -> string interpolation like `[variable]`

### Text and inline formatting

Ren'Py has direct support for several text features we are likely to need.

- ruby text -> Ren'Py `{rb}` and `{rt}` text tags
- inline formatting -> Ren'Py text tags
- expression interpolation -> Ren'Py text interpolation inside strings

Conversion note:

- Tyrano inline tags should not be flattened too early if Ren'Py has a direct or
  near-direct text representation

### Scene, image, and presentation control

Ren'Py provides script-level constructs for most common staging operations.

- background swaps -> `scene`
- character or image display -> `show`
- removals -> `hide`
- transitions -> `with`
- layer-aware display -> `scene`, `show`, and `hide` can target layers
- repeated motion or positioning -> transforms and ATL
- camera-like presentation -> transforms, layer transforms, and modern Ren'Py
  `camera` support in 3D-stage-oriented workflows

Conversion note:

- many Tyrano presentation tags will not map one-to-one, but most can still be
  preserved as Ren'Py staging code or intermediate action markers

### Audio, voice, timing, and media

Ren'Py has native support for the main playback concepts used by visual novels.

- BGM and SFX -> `play`, `stop`, `queue`, channel-based audio control
- fades and volume -> `play ... fadein`, `play ... fadeout`, channel volume
- voice -> `voice` statement and voice-capable channels
- waits and pacing -> `pause` statement and timing logic around transitions
- movies -> movie playback support and `Movie` displayables

Conversion note:

- audio wait tags such as `wbgm`, `wse`, and video wait tags should be preserved
  carefully because pacing order matters even when playback APIs differ

### UI, clickable elements, and backlog-adjacent behavior

Ren'Py has equivalents for some UI systems, but these often live in screen
language rather than plain script statements.

- clickable choices -> usually `menu`, `screen`, `textbutton`, `imagebutton`
- custom overlays or interface elements -> `screen` language
- history or backlog behavior -> Ren'Py has built-in dialogue history, but not
  every Tyrano backlog-control tag has a direct script equivalent

Conversion note:

- `link`, `glink`, `button`, and `clickable` may convert either to plain `menu`
  blocks or to custom `screen` definitions, depending on how visual the original
  interaction is
- `nolog`, `endnolog`, and `pushlog` may require custom handling because they
  affect dialogue history semantics, not just presentation
- if a reachable Tyrano project boots into its own title screen, a Ren'Py port may
  intentionally bypass Ren'Py's built-in main menu and route startup through the
  converted Tyrano title flow instead
- if the title flow begins with a non-interactive intro movie that should only play
  once, that movie may be a good candidate for Ren'Py `splashscreen` rather than
  remaining inside the normal title label flow

### Scripting and engine-level features

Ren'Py supports Python integration directly, but this does not mean TyranoScript
JavaScript should be converted automatically.

- Tyrano `eval`, `emb`, `iscript`, and related state tags have conceptual room
  in Ren'Py through Python expressions and `python:` blocks
- plugin, HTML, and browser-oriented engine hooks may have no direct equivalent
  in stock Ren'Py

Conversion note:

- preserve original expressions and script blocks as explicit markers first
- only translate them into Ren'Py Python after their runtime assumptions are
  understood

### Known mismatch areas

These categories are the most likely to require custom design rather than direct
statement-for-statement conversion.

- message-layer routing and window internals
- backlog control semantics
- graphical buttons and clickable regions with custom layout rules
- macro behavior and script metaprogramming
- plugin-driven behavior
- 3D and AR systems

For these areas, the safest path is:

1. preserve intent in intermediate output
2. map common cases to native Ren'Py constructs
3. flag complex cases for manual conversion or custom framework support

## Official source

Primary reference:

- `https://tyrano.jp/tag`

Ren'Py reference used for compatibility checks:

- `https://www.renpy.org/doc/html/`

When behavior in this document and the official docs disagree, use the official
docs as the source of truth and then update this file to reflect the repo's
conversion strategy.
