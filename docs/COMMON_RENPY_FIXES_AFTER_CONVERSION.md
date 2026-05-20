# COMMON REN'PY FIXES AFTER CONVERSION

This guide is for beginners using converted TyranoScript output in Ren'Py for
the first time.

It focuses on the most common problems you are likely to see after copying the
generated `.rpy` files into a Ren'Py project and clicking `Launch Project`.

The goal is not to fix every advanced issue. The goal is to help you get past
the first blockers and keep moving.

## First Rule: Do Not Panic

When Ren'Py finds a problem, it usually shows a clear error screen.

That screen often tells you:

- which file has the problem
- which line number caused it
- a short explanation of what went wrong

That is good news.

It means Ren'Py is helping you find the exact place that needs attention.

## A Good Beginner Workflow

When something breaks, use this order:

### 1. Read The Error Screen

Look for:

- file name
- line number
- missing file name
- missing label name
- invalid statement or syntax error wording

### 2. Open The File It Mentions

Use your text editor and go to that exact line.

### 3. Check `conversion_warnings.md`

If the problem is related to a converted Tyrano feature, the warning report may
already explain why it needs manual review.

### 4. Fix One Problem At A Time

Do not try to fix everything in one pass.

Fix the first error, run the project again, and then handle the next one.

## Problem: Image File Not Found

Typical meaning:

- the image file was never copied into the Ren'Py project, or
- the path in `images.rpy` does not match where the file really is

Example issue:

```renpy
image bg_asset forest = "images/backgrounds/forest.png"
```

If your actual file is here instead:

`game/images/backgrounds/forest.png`

then update it to:

```renpy
image bg_asset forest = "images/backgrounds/forest.png"
```

If the generated file already points into `images/backgrounds/`, putting the
image in the root `game/` folder will not fix the problem. The real file needs
to exist at the same relative path used by the generated declaration.

What to check:

- does the file actually exist?
- is the spelling exact?
- do uppercase/lowercase letters match?
- does the folder path match the project structure?

Helpful files:

- `game/images.rpy`
- `ALL_MEDIA.md`

## Problem: Audio File Not Found

Typical meaning:

- music or sound files were not copied over, or
- the generated path no longer matches the real location

Example:

```renpy
play music "audio/bgm/Music_Title-Artist_Name-01.ogg"
```

If the file is really stored in `game/audio/bgm/`, then change it to:

```renpy
play music "audio/bgm/Music_Title-Artist_Name-01.ogg"
```

What to check:

- was the file copied?
- is the extension correct (`.ogg`, `.mp3`, etc.)?
- does the generated path match the actual folder?

## Problem: The Movie File Exists, But It Still Does Not Play

Typical meaning:

- the path may be correct, but the movie container or codecs are not a good fit for desktop Ren'Py playback

Why this happens:

- Ren'Py movie playback is stricter than ordinary image or audio loading
- official Ren'Py movie docs recommend formats such as `WebM`, `Matroska`, or `Ogg` with codecs such as `VP9`, `VP8`, `AV1`, `Theora`, `Opus`, or `Vorbis`
- the same docs say the common `H.264 + AAC in MP4` combination is mainly a Web-platform case because Ren'Py itself does not normally decode H.264 or AAC in the standard desktop movie path

Common example:

- a Tyrano intro movie like `Op_Clean.mp4` plays in the original project
- but `renpy.movie_cutscene("movies/Op_Clean.mp4")` does nothing useful in desktop Ren'Py

Beginner-safe fix:

- run `prepare_movies_for_renpy.py`
- let it create a converted `.webm` file in a separate output folder
- copy that converted movie into `game/movies/`
- update the Ren'Py reference to the `.webm` filename if needed

Before running that helper, verify:

```bash
ffmpeg -version
```

If that command fails, install `ffmpeg` first.

Important:

- `prepare_movies_for_renpy.py` requires `ffmpeg`
- `ffprobe` is optional and only improves codec reporting
- Windows users may need to reopen Command Prompt after installing `ffmpeg` so the new PATH is picked up

Example command:

```bash
python3 prepare_movies_for_renpy.py path/to/your-project
```

Useful references:

- `https://www.renpy.org/doc/html/movie`
- `https://www.renpy.org/doc/html/splashscreen_presplash.html`

## Problem: Font File Not Found Or Styled Dialogue Looks Wrong

Typical meaning:

- a Tyrano `[font]` face name was converted into an assumed `.ttf` filename
- the expected font file does not exist in the Ren'Py project yet
- the file name or path does not match what Ren'Py is trying to load

Example generated line:

```renpy
narrator "Styled text" (what_font="fonts/GhoulFriAOE.ttf", what_size=40, what_color="#ff0a0a")
```

What to check:

- does `fonts/GhoulFriAOE.ttf` actually exist in your Ren'Py project?
- do you want to keep that file in the project root, or move it into a folder like `game/fonts/`?
- if you move it, did you update the generated `what_font=` value to match?
- did `conversion_warnings.md` mention a `font_face_mapping_needed` warning?

Beginner-safe fix:

- add the font file to your Ren'Py project
- if needed, change the generated line so it points to the actual font location, such as `fonts/GhoulFriAOE.ttf`
- test again

If the font file does not exist at all, Ren'Py cannot recreate that style until you provide it.

## Problem: Label Not Found

Typical meaning:

- another source `.ks` file was not converted yet, or
- a jump target was guessed but still needs manual cleanup, or
- a label name changed and another file still points to the old name

Example generated line:

```renpy
jump scene2__start
```

What to check:

- does `scene2__start` actually exist in one of your generated `.rpy` files?
- did you convert all related `.ks` files together?
- does `game/filename_map.md` help you locate the target file?

Helpful files:

- `game/filename_map.md`
- `game/conversion_warnings.md`

## Problem: Character Name Exists, But The Character Variable Does Not

Typical meaning:

- the script uses a speaker like `spina`, but `characters.rpy` does not define it

Example:

```renpy
spina "Hello there."
```

Ren'Py needs something like:

```renpy
define spina = Character("Spina")
```

What to check:

- is the definition present in `game/characters.rpy`?
- did the speaker name change in the script but not in the definition file?
- did you accidentally delete or rename the character definition?

## Problem: Syntax Error In A Generated File

Typical meaning:

- a generated line needs cleanup, or
- a manual edit introduced invalid Ren'Py syntax

Common examples:

- missing quote marks
- broken indentation
- deleting part of a statement by accident

Ren'Py is very sensitive to indentation.

For example, this is valid:

```renpy
label scene1__start:
    "Hello."
```

This is not:

```renpy
label scene1__start:
"Hello."
```

What to check:

- is the line indented correctly?
- are quote marks balanced?
- did you accidentally break a command like `jump`, `show`, or `play music`?

## Problem: `TODO TYRANO` Comments Are Everywhere

Typical meaning:

- the converter found Tyrano behavior it does not fully support yet

Example:

```renpy
# TODO TYRANO: unsupported tag: [quake time="300" count="3"]
```

This is not a parser crash. It is a review marker.

What to do:

- decide whether that feature matters for the scene to run
- if not, leave it for later
- if yes, replace it with a Ren'Py equivalent manually

Recommended beginner approach:

- first get dialogue and scene flow running
- then improve visual effects and UI behavior afterward

## Problem: The Scene Runs, But Something Feels Off

Typical meaning:

- the converter made an approximate translation
- a Tyrano-specific effect does not have a one-to-one Ren'Py equivalent yet

Common examples:

- pacing from `[l]` and `[p]` feels different
- sprite placement is simpler than the original
- message-window behavior is missing
- shake effects or transitions are absent

What to do:

- check `game/conversion_warnings.md`
- search the script for `TODO TYRANO`
- compare against the original `.ks` file or text export

At this stage, this is normal.

## Problem: Nothing Happens When I Launch The Project

Typical meaning:

- the game has no obvious starting label wired into the project flow, or
- another script file is taking priority for startup

What to check:

- does your project still contain Ren'Py's default sample script?
- are your generated files actually inside `game/`?
- does your project have exactly one clear `label start:`?
- did you copy the converted script into a subfolder without updating the active
  startup path?

Important:

- Ren'Py can load `.rpy` files from subfolders under `game/`
- but that does not automatically make those files your startup script
- a new project usually already has `game/script.rpy`, and that file often owns
  `label start:`

If needed, replace the default sample script or create a tiny starter script
like this:

```renpy
label start:
    jump tyranobuilder__start
```

That tells Ren'Py where to begin.

In newer scenario and project conversions, the generated `game/script.rpy` may
also intentionally skip Ren'Py's built-in main menu so the converted Tyrano title
screen becomes the real startup menu.

You may see startup code like:

```renpy
label main_menu:
    return

label start:
    jump title_screen__post_op
```

That is not broken by itself.

If a startup movie was detected safely, you may also see:

```renpy
label splashscreen:
    $ renpy.movie_cutscene("movies/intro.mp4")
    return
```

That means the converter decided the intro should play once at startup instead of
replaying every time the player returns to the title screen.

## Problem: The Project Launches, But It Jumps To The Wrong Place

Typical meaning:

- a converted cross-file reference needs manual review
- a label target was normalized differently than you expected

What to check:

- `game/filename_map.md`
- the destination label name in the target `.rpy`
- warning notes about unresolved or guessed references

For startup-specific flow, also check whether `game/script.rpy` is intentionally
jumping to a converted title label such as `title_screen__post_op` instead of a
normal story entry label.

## Problem: The Wrong Character Image Shows Up

Typical meaning:

- the image declaration points to the wrong file, or
- two variants have similar names and need cleanup, or
- the original Tyrano staging behavior used extra attributes the safe-subset converter does not fully honor yet

What to check:

- `game/images.rpy`
- `game/conversion_warnings.md`
- the actual asset filenames

## Problem: The Background Changes, But Character Placement Looks Too Simple

Typical meaning:

- Tyrano-specific layout values like position, reflection, crossfade, or timing were simplified

This is expected in the current safe subset.

What to do:

- get the right image showing first
- worry about exact staging second
- improve `show` behavior later with transforms or custom positioning if needed

## Problem: Conditional Logic Does Not Behave As Expected

Typical meaning:

- a Tyrano expression needs review
- a `cond=...` rule was flagged for manual checking
- JS-driven state logic is beyond the current safe subset

What to check:

- conditional blocks in the generated `.rpy`
- warning entries mentioning manual condition review
- the original `.ks` source around the same lines

If the logic is complex, do not guess. Mark it, isolate it, and fix it
carefully.

## Problem: The Project Compiles, But Menus Or UI Features Are Missing

Typical meaning:

- the missing feature was a Tyrano UI system, not ordinary dialogue flow

Common examples:

- graphical buttons
- clickable areas
- floating text
- speech bubbles
- backlog or message-layer behavior

These usually need:

- manual Ren'Py `screen` work, or
- a later converter feature pass

## Fast Checklist For Beginners

When something fails, check these first:

- is the file actually inside `game/`?
- does the missing asset really exist?
- do the paths in `images.rpy` or script commands match reality?
- does the missing label really exist in another `.rpy` file?
- is there a clue in `game/conversion_warnings.md`?
- is there a `TODO TYRANO` marker near the failing line?

## Which Files To Check First

If you are not sure where to look, start here:

- `game/conversion_warnings.md`
- `game/images.rpy`
- `game/characters.rpy`
- `game/filename_map.md`
- the generated file that Ren'Py says is failing
- `game/script.rpy` if startup behavior is not going where you expect

## A Good Order For Fixing Problems

For beginners, this order is usually best:

1. fix missing files
2. fix missing labels
3. fix broken startup flow
4. fix character definitions
5. fix obvious syntax problems
6. fix unsupported visual and UI behavior later

This helps you get a playable script sooner.

## Final Advice

If the converted project does not run perfectly on the first try, that does not
mean the migration failed.

A successful first conversion often looks like this:

- Ren'Py opens
- the script starts
- dialogue appears
- backgrounds show up
- labels move from one section to the next
- warnings point to the remaining manual work

That is already meaningful progress.

The fastest way forward is usually:

- make the project launch
- make one scene run
- fix the next visible problem
- repeat
