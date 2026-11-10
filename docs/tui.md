# Trama terminal interface

Trama edits a recording scene before capturing a whole display, with optional
PNG/JPG/GIF layers and one microphone-reactive avatar. It has no live preview or
editing during recording. For installation and the required system KMS helper,
see [Flatpak installation](flatpak.md); check [compatibility](compatibility.md)
before relying on another desktop or GPU.

## Open Trama

After installing the release Flatpak, open a terminal in your graphical session
and run **without sudo**:

```bash
flatpak run io.github.xoloitzcuintle95.Trama
```

Use an explicit, writable profile path to start a separate scene:

```bash
flatpak run io.github.xoloitzcuintle95.Trama "$HOME/Videos/Trama/scene.toml"
flatpak run io.github.xoloitzcuintle95.Trama --lang en "$HOME/Videos/Trama/scene.toml"
flatpak run io.github.xoloitzcuintle95.Trama --help
```

The parent folder can be created when you save. The terminal must be interactive,
with a valid `TERM` and at least **72 columns × 20 rows**. A monochrome fallback is
available when terminal colors are unavailable. Source-checkout launch commands
are separate: see [development](desarrollo.md).

Without a profile argument, Trama restores the last opened/saved profile path,
or uses `perfil.toml` in the current directory when no valid saved state exists.
A missing profile starts as a new scene at that path. An explicit argument always
takes precedence.

## First scene

For a new profile, the setup wizard opens after display discovery succeeds.
Press `w` to open it again:

1. Choose the display by identifier and resolution.
2. Choose the default microphone or a named input. The wizard creates an avatar,
   so it requires a microphone.
3. Pick an idle GIF and a talking GIF.
4. Choose the avatar's corner. The initial maximum box is 300 px with a 20 px
   margin; change size or margin before selecting the corner to apply it.
5. Choose **Save profile and record for 30 seconds**, **Save and keep editing**,
   or **Keep editing without saving**.

Esc cancels a dialog, but settings already applied remain in memory. To record
without an avatar, leave the wizard with Esc, choose a display with `p`, configure
audio with `m`/`g`, and save with `s`. No overlay layers are required.

The capture includes everything visible on the selected display, including the
terminal. After recording starts, switch to your desktop presentation or other
content. There is no countdown, automatic window selection or global stop key.

## Navigate and edit

Tab and Shift+Tab move between these sections:

| Section | Enter acts on |
| --- | --- |
| Overview | Record, 30-second test, or Save |
| Layers | The selected layer's field editor |
| Capture | Display or FPS |
| Audio | Microphone or system-audio toggle |
| Output | Recordings folder or video filename |

Use ↑/↓ or `j`/`k` to select a field, layer or action. In Overview, ←/→ also select
buttons. Space opens the focused section's actions. Enter applies a selection;
Esc returns or cancels. In a text field, Ctrl+U clears it, ←/→ move the cursor,
and Home/End move to either end. Type paths without surrounding shell quotes in
dialogs.

The header marks unsaved changes and shows READY, ERROR or SETUP INCOMPLETE.
READY is not a recording certification: device and asset validation still runs
before capture. `!` shows full diagnostics when a message is truncated.

### Main-screen shortcuts

Keys are case-sensitive and work across sections while not recording.

| Key | Action |
| --- | --- |
| `?` / F1 | Show help |
| `L` | Select and save interface language |
| `p` | Choose display |
| `f` | Set FPS, integer 1–120 |
| `m` | Choose microphone, default input, or no microphone |
| `g` | Toggle game/system audio |
| `u` | Query displays and audio devices again |
| `d` | Choose recordings folder |
| `n` | Edit video filename |
| `a` | Add PNG/JPG/GIF graphic |
| `v` | Add an avatar, if none exists |
| `e` | Edit a field of the selected layer |
| `c` | Set selected layer's corner, box size and margin, or manual X/Y |
| `h` | Hide/show selected layer |
| Delete / `D` | Confirm layer removal; does not delete its files |
| `[` / `]` | Move selected layer toward the back/front |
| `s` / `S` | Save / Save as another TOML |
| `l` | Load another TOML |
| `r` | Record until stopped |
| `t` | Record an approximately 30-second test |
| `o` | Show this session's last MKV and diagnostic-file paths |
| `w` | Open setup wizard |
| `!` | Show diagnostics |
| `q` / Esc | Quit, prompting about unsaved changes |

### Asset and folder picker

Use ↑/↓ or `j`/`k` to select entries; Enter opens a folder or selects a file.
Page Up/Down scroll. `../` goes to the parent folder. Press `p` to type or paste a
path; relative paths start at the folder displayed in the picker. Esc cancels.

The file list filters GIFs for avatars and PNG/JPG/JPEG/GIF for graphics. The
loader checks actual contents, not just extensions. In the folder picker,
**Space uses the current folder**; `p` also accepts a new folder, created when
recording starts.

### Layers, placement and avatar

The first layer is the background; the final layer is drawn on top. Up to 16
layers and one avatar are supported. Hidden layers remain in the profile and
must still have valid assets.

Press `e` to change just one field: name, asset file(s), avatar sensitivity and
release time, placement, visibility, dimensions, aspect preservation or manual
X/Y. Applying a field returns to the field list; Esc returns to the main screen.
Invalid edits preserve the previous value. Enter `-` for width or height to leave
that dimension automatic. Disabling aspect preservation requires both dimensions.
See the [CLI reference](guia-cli.md) for all field limits and sizing rules.

`c` fits a layer inside a square maximum box while preserving aspect ratio, then
places its **effective** dimensions at the chosen corner. A 2:1 graphic in a
300 px box occupies 300×150, not 300×300. Margin is 0–4096 px; box size is
1–16384 px, but the result must fit the selected display with its margins.
Manual X/Y allows intentional clipping. Positions are pixels from the upper-left
corner. The avatar uses a common box based on its idle image.

Corner placement saves calculated X/Y, not a persistent anchor. After changing
display or resolution, refresh with `u` and place layers again.

The avatar switches to its talking GIF when microphone RMS exceeds `threshold`;
a lower threshold is more sensitive. `release_ms` controls the delay before
returning to idle. It requires a microphone even when hidden. The microphone is
also recorded; this is not a silent detector-only input.

## Output, saving and loading

Output separates folder (`d`) from filename (`n`). For example, choose a writable
folder and name the video:

```text
recording-{timestamp}.mkv
```

The filename must end in `.mkv`, cannot contain folders, and supports only the
`{timestamp}` template. It expands to UTC for each capture. Folder templates are
not accepted by the folder selector. A fixed filename can be used once; existing
recordings or matching log/report files are rejected rather than overwritten.
The two controls are stored together in `[recording].output`, not as new TOML
fields.

`s` saves the current profile; `S` saves to another path, asking before replacing
a different existing TOML. Saving writes schema version 2 and rewrites asset and
output paths relative to the new profile folder. It can replace comments and
formatting. Save as does not copy assets or move recordings.

`l` loads another profile. Loading or quitting with unsaved changes offers Save,
Discard, or Keep editing; Esc keeps editing. Opening, closing or recording does
not silently save the scene. Recording uses the current in-memory settings.

## Record, stop and handle errors

Press `r` for an open-ended capture or `t` for a 30-second test. Trama first
validates the display, encoding support, audio, assets and destination. A Polkit
authorization prompt may be required for the installed KMS helper; do not run the
whole application as root. See [KMS security](security-kms.md).

During validation/capture, editing is disabled and the screen shows a static
PREPARING, RECORDING or CLOSING view, destination and requested duration. It has
no live counter or preview.

- `x` or Ctrl+C requests stopping and returns to editing after finalization.
- `q` or Esc requests stopping, then quitting; unsaved changes still prompt.
- During validation, cancellation waits for the current query to finish before
  preventing capture from starting.

Wait for the close operation before closing the terminal. On completion, `o`
shows the MKV, its folder, `<video>.gsr.log` and `<video>.report.json`; it does not
launch a player or file manager. These details concern only the current session.
A recording that fails after creating output is retained and marked partial.
A validation failure does not turn an earlier recording into a new success.
Review the resulting video and audio in a player.

If devices are unavailable, check your graphical session and connections, press
`u`, and choose the display/microphone again. For asset, encoding, helper or
output errors, press `!` and use [CLI troubleshooting](guia-cli.md). A successful
validation cannot guarantee a complete recording on every driver or desktop.

## Local preferences and privacy

Trama keeps these separate:

| Data | Location used by the application |
| --- | --- |
| Scene settings and asset/output paths | Your chosen TOML profile |
| Last profile path, not unsaved edits | `$XDG_STATE_HOME/xolo/session.json`, or `~/.local/state/xolo/session.json` when unset |
| Language preference | `$XDG_CONFIG_HOME/trama/ui.toml`, or `~/.config/trama/ui.toml` when unset |
| Video, engine log and JSON report | Your chosen output folder |

These XDG locations are evaluated **inside the running application**. Flatpak
redirects application configuration/data into its app-specific storage under
`~/.var/app/io.github.xoloitzcuintle95.Trama/`; do not assume a native checkout
shares the same preferences. If the remembered profile was deleted, Trama
prepares a new profile at that path; use `l` or `S` to choose another. A failure
to remember the session does not replace your TOML.

Press uppercase `L` to choose Automatic, Español or English. The preference file
contains `language = "auto"`, `"es"` or `"en"`. A missing/invalid file uses
automatic detection: first nonempty `LC_ALL`, `LC_MESSAGES`, then `LANG`; Spanish
locales select Spanish, all others English. `--lang auto|es|en` overrides the
saved preference for that launch, including help. Choosing `L` saves a new
preference. Language selection uses no network translation service and does not
change profiles, filenames, device names or shortcuts. Backend/system errors and
the classic CLI retain their original language.

Profiles and reports can contain device names and absolute asset/output paths;
logs may contain system diagnostics. Review them before sharing. The Flatpak's
host/device access is broad, not a strong sandbox; see
[security details](security-kms.md). Record only content and audio you intend to
capture.
