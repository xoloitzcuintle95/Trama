# Trama: GSR compositor TUI

A full-screen interface for editing before recording. It reuses existing TOML
profiles, Rust plugin 0.4.0 and GSR recording. This interface adds no preview,
live editing or packaging of its own. No additional pip dependencies are needed:
it uses Python's `curses`, available in the reviewed environment.

## Open your profile

From a COSMIC terminal, without sudo:

```bash
cd "$HOME/project-gsr-compositor"
./trama perfil.toml
```

To type just `trama` in that shell without installing anything:

```bash
export PATH="$PWD:$PATH"
trama
```

That `PATH` applies to the current shell. Startup files are not modified and no
global command is installed. Other launch options:

```bash
python3 scripts/trama_tui.py perfil.toml
./trama --help
```

The terminal needs at least **72 columns × 20 rows** and a valid `TERM`. The dark
theme uses teal/cyan selection and coral for errors/recording, with a monochrome
fallback when colors are unavailable. No external TUI libraries are required.

Tab/Shift+Tab cycles through five persistent sections:

- **Overview**: summary, record, 30-second test and save.
- **Layers**: list and selected-layer properties; side by side in wide terminals,
  with properties below in compact terminals.
- **Capture**: display, known resolution and FPS.
- **Audio**: microphone and game/system audio.
- **Output**: separate folder and filename fields; last MKV.

Arrows or `j`/`k` select a field/layer/action; Enter edits or executes. Space opens
context actions, including add/remove/reorder, save as and load profile. `?` shows
all shortcuts. Direct shortcuts remain available from every section. Esc goes
back or cancels; quitting with unsaved changes asks what to do. Ctrl+U clears a
text field.

The header distinguishes READY, ERROR and SETUP INCOMPLETE using queried data and
known errors. READY does not certify every asset: full validation still runs
before GSR starts. The profile name marks unsaved changes. The footer shows a few
relevant shortcuts; `!` opens full error text when truncated.

Recording keeps a minimal static view: PREPARING, RECORDING or CLOSING, requested
duration when available and output destination. There is no periodic counter,
assumed hardware telemetry or editing during capture.

## Language: automatic, Spanish and English

On first run Trama checks `LC_ALL`, then `LC_MESSAGES`, then `LANG`, taking the
first nonempty value. An `es` language such as `es_MX.UTF-8` selects Spanish;
English, other languages and `C`/`POSIX` use English. Detection is local: no API,
network access or translation service.

Press uppercase **`L`** from any section to select:

- **Automatic (system)**: follow the environment language.
- **Español**: always use Spanish.
- **English**: always use English.

Enter saves and applies immediately; Esc cancels. The selector is also available
under Space → Overview actions. The header shows the active language beside `L`.
Help (`?`/F1) keeps one action per entry in both languages.

The preference is saved in `$XDG_CONFIG_HOME/trama/ui.toml`, or
`~/.config/trama/ui.toml` when that variable is unset:

```toml
language = "auto"
```

Accepted values: `auto`, `es`, `en`. No field is added to the recording TOML.
A missing/invalid preference file falls back to automatic. Session data and
existing profiles are neither migrated nor deleted.

To change language **for this run only**, including `--help`:

```bash
./trama --lang en
./trama --lang es /ruta/a/perfil.toml
./trama --lang auto
./trama --lang en --help
```

Precedence: `--lang` → saved preference → automatic. Choosing with `L` during a
session saves a new preference. Shortcuts do not change with language. Device,
layer and file names stay intact. Engine, loader and system diagnostics retain
their original language. TUI translation does not translate the other CLI tools;
this documentation has been translated separately.

## First run

Opening a profile name that does not exist starts this flow once a display query
succeeds. You can also open it with `w`:

1. Choose the display by name and resolution.
2. Choose a microphone by name or the system default. An avatar needs an input;
   the no-microphone option is insufficient.
3. Find idle and talking GIFs in the file picker.
4. Choose one of four corners. A new layer defaults to a 300 px box and a 20 px
   margin, both editable on that screen.
5. Select **Save profile and record for 30 seconds**. You may instead save and
   continue editing, or return without saving.

In the picker, Enter opens a folder or selects a file. `p` accepts a typed/pasted
path; relative paths start at the displayed folder. Esc cancels. Visual filters
show GIFs for avatars and PNG/JPG/GIF for graphics; the Rust decoder validates
actual content.

After recording starts, switch to the content you want to capture. The entire
display is recorded: there is no countdown or global stop shortcut. On completion
the TUI returns and shows the MKV filename. Press `o` for its full path and
auxiliary files, scrolling when needed.

Esc can cancel each wizard dialog. Already-applied settings stay in memory;
`s` saves them and quitting warns about changes.

## Daily use and last profile

Without an argument, Trama looks for:

1. The last opened/saved profile recorded in session state.
2. `perfil.toml` in the current directory if no valid state is available.

An explicit argument such as `./trama otro.toml` takes precedence. The last
profile's path is remembered in:

```text
$XDG_STATE_HOME/xolo/session.json
```

Without `XDG_STATE_HOME`, this is `~/.local/state/xolo/session.json`. The historical
location avoids moving personal data; it is not a command alias. The file stores
a profile path, not its unsaved changes. Opening a profile does not modify it.
If the last file was deleted, a new profile is prepared at that path: `l` opens
another and `S` saves under another name. Session-state write errors do not
replace the TOML profile.

For daily use press **`r` from the initial screen** or `t` for a 30-second test.
A ready scene does not require repeating the wizard. Real device/asset validation
still runs before recording.

## Main-screen keys

| Key | Action |
| --- | --- |
| Tab / Shift+Tab | Change focused section |
| ↑/↓ or `j`/`k` | Select a field or layer in this section |
| ←/→ in Overview | Select a button |
| Enter | Edit the focused field or activate its button |
| Space | Open section actions |
| L | Choose and save language preference |
| `?` or F1 | Full help |
| `e` | Edit one field of the selected layer |
| `p` | Choose display |
| `m` | Choose microphone |
| `f` | Edit FPS (1..120) |
| `g` | Toggle game/system audio |
| `d` | Choose recordings folder |
| `n` | Edit video filename, including `{timestamp}` |
| `a` | Add PNG/JPG/GIF graphic |
| `v` | Add an avatar if none exists |
| `c` | Place selected layer by corner and size |
| `h` | Hide/show without removing the layer |
| Del or `D` | Confirm layer removal; do not delete its file |
| `[` / `]` | Move layer toward the back / front of the list |
| `s` | Save current profile |
| `S` | Save as another TOML |
| `l` | Load another TOML |
| `r` | Record until stopped |
| `t` | Record a 30-second test |
| `o` | Show this session's last MKV, folder, log and report |
| `u` | Query displays and audio again |
| `w` | First-run wizard |
| `!` | Full diagnostics |
| `q` or Esc | Quit, warning about unsaved changes |

Letters are case-sensitive: `d` chooses a folder; `D` removes a layer. `o` displays
paths inside the TUI, not a player or file manager. The existing list semantics
remain: the final layer is drawn on top.

## Change just one field

Select a layer and press `e`. The field list shows current name, file(s), avatar
sensitivity, placement, visibility, width/height, aspect ratio and advanced X/Y.
Select **only** the field to change. Applying returns to the list; Esc returns
to the main screen.

There is no full-form walkthrough. Selecting Visible or Keep aspect ratio toggles
it. Enter `-` for width or height to leave that dimension unspecified and derive
it under existing rules. Disabling aspect preservation requires both dimensions.

Errors appear beside the field or in its dialog. Pre-capture validation errors
are marked beside the setting and in the bottom status. `!` shows truncated text
in full. Invalid edits preserve the previous value. New paths are checked by the
Rust loader without starting GSR or creating a graphics context.

## Corners and effective size

`c` offers:

- Top-left.
- Top-right.
- Bottom-left.
- Bottom-right.
- Maximum box size, in pixels.
- Margin, in pixels.
- Manual X/Y, an advanced option.

Change size or margin first, then select a corner to apply. Quick placement
preserves aspect ratio inside a square box of the chosen size. The plugin's
actual Rust code resolves **effective** width/height: a 2:1 image in a 300 px box
occupies 300×150, not 300×300. Position subtracts effective size from the monitor
canvas, rounding fractional dimensions upward. Sizes that do not fit with the
margin are rejected; advanced X/Y allows intentional clipping.

Existing geometry is used to recognize corner/margin when possible, so moving an
already-anchored layer need not require reentering its size. New layers default
to bottom-right, a 300 px box and a 20 px margin. The avatar uses its idle-based
box for both idle and talking, matching the plugin.

At 1920×1080, a square 300×300 avatar with margin 20 is placed at 1600/760.
To move it top-left: select it in Layers, press `c`, choose Top-left and Enter.
No manual X/Y is required.

The profile stores calculated X/Y, not a new anchor type. After changing
resolution, refresh devices with `u` and place the layer again. Manual positions
remain pixels measured from the upper-left corner.

## Recordings folder and video filename

Both settings are in Output, also available with `d` and `n`:

- `d`: browse to a folder and press **Space** to use it. `p` accepts a path,
  including a new folder that will be created when recording starts.
- `n`: type only the filename, for example `minecraft-{timestamp}.mkv`.
  Folder components are not allowed in this field.

They are combined and saved in the existing field, for example:

```toml
[recording]
output = "recordings/minecraft-{timestamp}.mkv"
```

Existing `perfil.toml` and direct recording remain compatible. No new schema or
duplicate `folder`/`filename` fields are added. `{timestamp}` is replaced with UTC
when preparing each capture. The name must end in `.mkv`; an existing fixed output
is rejected rather than overwritten. Folder selection does not allow templates;
put `{timestamp}` in the filename.

Saving retains paths relative to the TOML folder, including Save as. Graphics
are not copied and videos are not moved.

## Record, stop and return

Existing validation and recording run on a worker thread; only the main thread
uses curses. Capture shows a **minimal static view** with state, destination,
requested test duration when applicable and the stop key. There is no animated
counter or periodic panel redraw. Editing is blocked during validation/capture.

- **`x` or Ctrl+C:** request stopping, then return after GSR closes the file.
- **`q` or Esc during capture:** request stopping, then quit; unsaved profile
  changes offer save, discard or keep editing.
- **`t`:** stop automatically after approximately 30 seconds.

Stopping reuses SIGINT to GSR, waits for finalization and checks with ffprobe.
It does not kill `parec` first, allowing GSR/plugin resources to close in order.
No composition buffers, clocks or Rust code are changed. The detector remains
a second capture of the selected input.

Stopping during validation waits for the current query to finish, then cancels
before launching GSR. Device queries have their own timeouts; native calls are
not all canceled immediately.

Success shows the MKV; `o` opens full-path details. A failed capture that created
a file retains it and marks it partial. A validation failure does not present a
previous result as a new recording. No integrated playback or preview is provided.

## Saving and quitting

`s` saves the current TOML. `S` accepts another path and confirms overwriting a
different existing file. Saving preserves normalization (schema 2 and relative
paths) and can rewrite TOML comments/formatting.

Quitting or loading another profile with changes offers Save changes, Discard
changes and Keep editing. Esc keeps editing. Opening, closing or recording does
not silently save changes. First run does have an explicit Save profile and
record for 30 seconds action.

## Idle interface and resources

The screen repaints on input, resize or a worker event, not on every loop
iteration. During capture, the main thread waits for input with a one-second
timeout to check worker completion; keys still arrive immediately. Painting
performs no asset queries or decoding. When GSR closes, panels and selection return.

This suspends presentation, not the Python process or all its memory. It avoids
adding a control process or rebuilding a session to return to the TUI. There are
no new dependencies.

An indicative local sample over roughly 5-second windows measured around 22 MiB
RSS and 0.20% of one CPU core for the TUI during **simulated** capture. Capture CPU
was effectively unchanged before/after in that sample; short intervals and
counter resolution do not justify a numeric savings claim. These figures cover
only the TUI, not GSR, helper, detector or their total, and do not represent a real
COSMIC workload benchmark.

Initialization uses `curses.wrapper` to restore terminal echo/mode on exit or
error propagation. SIGTERM also follows recording shutdown and terminal
restoration. References: [Python curses](https://docs.python.org/3/library/curses.html)
and the [wrapper pattern](https://docs.python.org/3/howto/curses.html#starting-and-ending-a-curses-application).

## Direct command retained

The TUI does not replace these commands:

```bash
python3 scripts/compositor.py check perfil.toml
python3 scripts/compositor.py record perfil.toml --seconds 30
python3 scripts/compositor.py record perfil.toml
```

The classic `python3 scripts/compositor.py edit` menu remains available. Its
[reference manual](guia-cli.md) covers TOML, requirements, audio and diagnostics.
`trama` currently accepts an optional profile, `--lang {auto,es,en}` and `--help`;
it adds no streaming subcommands and has not been publicly packaged/released.

## Verification and limitations

Real capture depends on the graphical session, driver and audio server. Automated
checks do not replace a recording on the target machine.

Delivery checks:

- Model: corners with nonsquare sources and Rust effective size, avatar/sample
  TOML, single-field edits, folder/name, save/load, ordering, hidden state, missing
  assets, session recovery and unsaved changes.
- Real pseudoterminal: first run/file picker, last-profile recovery, sample
  profile, corner changes without X/Y, save, 30-second test, MKV details and return.
- Pseudoterminal: separate folder/name edits, invalid filename, one-field editing,
  unsaved warning and stopping with `x`, SIGINT and SIGTERM.
- ECHO/ICANON restoration after terminal tests.
- Sections at 72×20, 80×24, 110×30 and 160×40; focus, context actions and resize.
- No repaint while waiting; capture view has no panels or periodic terminal
  output; stop and return to panels.
- Earlier suite retained. Full execution also requires development `media-dump`
  and compiled C-reference artifacts, not part of the minimal runtime. See
  [validation status](estado.md#automated-and-local-validation).

Pseudoterminal tests use **simulated devices and capture**, with the real TOML
model, Rust decoder, shared recording process and a real synthetic MKV. The
30-second case waits that long and checks file duration. Adapters live in
`tests/`; the launcher has no fake-engine flag. These checks do not replace KMS,
physical audio or real workload capture: a graphical session with DRM/KMS and
audio-server access is required.

The user confirmed the TUI works and looks good on their laptop, plus a 10-minute
recording. This is a usage report, not instrumented benchmarking. Installed-package
recording was confirmed later; see [current status](estado.md).

To repeat tests:

```bash
python3 tests/test_trama.py
python3 tests/test_trama_view.py
python3 tests/test_trama_i18n.py
python3 tests/test_trama_pty.py
python3 tests/test_compositor.py
python3 tests/test_element_cli.py
```

To repeat target-machine acceptance:

```bash
./trama perfil.toml
```

Tab to Layers, select the avatar, press `c`, choose another corner and Enter;
`s` saves, `t` records 30 seconds and `o` shows the final file. Check video, audio,
avatar response and return to the TUI. No new resource figures or OBS advantage
are claimed.

Code: [trama entry](../trama), [TUI](../scripts/trama_tui.py),
[model/geometry](../scripts/trama_model.py), [shared recorder](../scripts/compositor.py),
[state tests](../tests/test_trama.py), [PTY tests](../tests/test_trama_pty.py).
