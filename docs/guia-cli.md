# Trama CLI and profile reference

This guide covers the installed Flatpak's direct recording commands, TOML scene
format and classic line-based editor. For the full-screen interface, see the
[TUI guide](tui.md). First complete [Flatpak installation](flatpak.md), including
the system-wide installation and fixed KMS helper. Run the application as your
normal user in a graphical session, **not with sudo**.

The release bundles its recording engine and plugin; a separate native GSR,
Python environment or source checkout is not needed. Native development commands
are documented in [development](desarrollo.md), not used by the examples below.
Check [compatibility](compatibility.md) for verified environments and limitations.

## Installed command and quick start

The CLI script is inside the Flatpak. Invoke it with Python, not as an argument
to the default TUI launcher:

```bash
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama \
  /app/lib/trama/scripts/compositor.py --help
```

### Create a scene and record a desktop presentation

Create a writable location and open a new profile in the classic editor:

```bash
mkdir -p "$HOME/Videos/Trama"
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama \
  /app/lib/trama/scripts/compositor.py edit "$HOME/Videos/Trama/scene.toml"
```

This editor uses numbered prompts followed by Enter, not TUI arrow navigation.
Prompts and backend diagnostics are currently Spanish.

1. Enter `1` to choose a display. Select its listed number; no display identifier
   is assumed in this guide.
2. Enter `2` to select the system-default microphone, a named input, or no
   microphone, then choose whether to record game/system audio (`s` = yes,
   `n` = no). A scene without an avatar can record without a microphone.
3. Enter `3` to set output to `recording-{timestamp}.mkv` and keep 30 FPS or choose
   another value. This relative filename is resolved beside `scene.toml`.
4. Enter `5` and accept the profile path to save. Enter `0` to exit.

No layers are required for this first capture. Validate and record:

```bash
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama \
  /app/lib/trama/scripts/compositor.py check "$HOME/Videos/Trama/scene.toml"
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama \
  /app/lib/trama/scripts/compositor.py record "$HOME/Videos/Trama/scene.toml" --seconds 30
```

`record` validates again and starts without another confirmation. When it prints
`Grabando. Ctrl+C termina y cierra el archivo.`, switch to your presentation.
The **whole selected display**, including the terminal while visible, is recorded.
There is no countdown, automatic window selection or global stop shortcut.

The command prints the MKV, log and report paths on successful completion. Open
the video in a player and review picture, sound and synchronization. For an
open-ended recording, omit `--seconds`, then return to the terminal and press
Ctrl+C. Wait for file finalization before closing the terminal.

## Commands and options

In the table below, `CLI` means the entire installed invocation:

```text
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama /app/lib/trama/scripts/compositor.py
```

`CLI` is notation, not an installed executable or shell alias.

| Arguments after `CLI` | Behavior |
| --- | --- |
| `--help` / `-h` | Show top-level help |
| `devices` | List display identifiers/resolutions, microphone identifiers/descriptions and availability of `default_output` system audio |
| `edit [PROFILE]` | Open the classic editor; an absent file starts a new in-memory profile |
| No arguments | Open the classic editor with a new profile based in the current directory |
| `check PROFILE` | Validate and print a summary without starting a recording |
| `check PROFILE --assets-only` | Validate profile/build/assets/output without querying capture or audio devices |
| `record PROFILE` | Validate, print a summary and record until stopped |
| `record PROFILE --seconds N` | Stop automatically after approximately `N` seconds; floating-point values from 1 through 7200 |
| `COMMAND --help` | Show that command's help |

`PROFILE` is a TOML file path. Quote paths containing spaces in shell commands.
`check` and `record` require an existing file. No `--lang`, `--force`, streaming,
codec, quality or per-layer flags are exposed by this CLI. TUI language options
belong to the default launcher, not `compositor.py`.

Successful commands return 0; handled profile/device/recording errors return 2.
An interrupted editor or input EOF returns 130. Ctrl+C during an active recording
requests normal finalization; the completed recording can still return success.

## TOML profile format

Use `schema_version = 2` for new profiles. A profile may be at most **128 KiB**.
Unknown public keys are rejected. Tables and values are type-checked; booleans
are TOML `true`/`false`, not strings or integers. Paths expand `~`; relative asset
and output paths are resolved against the **profile's folder**, not your shell's
current directory. Environment variables in TOML paths are not expanded.

### Complete avatar example for the installed Flatpak

Save the following as a writable `scene.toml`. The avatar GIFs are bundled in
the installed app, so these `/app` asset paths are used only inside Flatpak.
**Before recording**, open it with `edit` and use option `1` to choose a real
display; the empty `screen` deliberately does not guess your monitor.

```toml
schema_version = 2

[recording]
screen = ""
output = "recording-{timestamp}.mkv"
fps = 30
game_audio = true
microphone = "default_input"

[[layers]]
name = "Presentation avatar"
kind = "avatar"
idle = "/app/share/trama/examples/assets/idle.gif"
talking = "/app/share/trama/examples/assets/talking.gif"
x = 32
y = 32
width = 300
height = 300
keep_aspect = true
visible = true
threshold = 0.04
release_ms = 250
```

For portable personal scenes, use your own assets alongside the profile and
relative paths such as `assets/idle.gif`. Saving does not copy assets. A simple
scene can omit all `[[layers]]` blocks. To add a graphic, place your own PNG at
`assets/logo.png` relative to the profile and append:

```toml
[[layers]]
name = "Presentation logo"
kind = "graphic"
path = "assets/logo.png"
x = 24
y = 24
width = 240
keep_aspect = true
visible = true
```

### Root fields

| Field | Type and behavior |
| --- | --- |
| `schema_version` | Integer 1 or 2; omitted means legacy version 1. New saves always write 2 |
| `[recording]` | Optional table; omitted fields receive the defaults below |
| `[[layers]]` | Array of layer tables; 0–16 layers, including at most one avatar. Omitted means no layers |

Legacy version 1 can import one top-level `media` path and/or an `[element]`
table instead of `[[layers]]`. Top-level `media` or `element.media` supplies the
graphic `path`; omitted kind/name become `graphic`/`Elemento`. Do not combine
this legacy single-element form with `layers`. Use the version 2 form above
when authoring a new scene.

### `[recording]`

| Field | Type | Default | Meaning and limits |
| --- | --- | --- | --- |
| `screen` | String | `""` | Exact display identifier from `devices`; must be available for recording |
| `output` | String | `"recordings/{timestamp}.mkv"` | Nonempty `.mkv` destination; only `{timestamp}` is an accepted template |
| `fps` | Integer | `30` | 1–120, constant-frame-rate recording |
| `game_audio` | Boolean | `true` | Record GSR's `default_output` system-audio source |
| `microphone` | String | `"default_input"` | System default, an exact listed microphone identifier, or `""` to disable |

These strings cannot contain NUL. No microphone is allowed only without an
avatar. `game_audio = false` and `microphone = ""` produce a silent recording.
The legacy `screen = "screen"` alias is resolved only when exactly one monitor
is available; select an explicit identifier for reliable behavior.

### Common layer fields

| Field | Type | Default | Meaning and limits |
| --- | --- | --- | --- |
| `name` | String | `"Capa N"` | Nonempty, at most 128 UTF-8 bytes |
| `kind` | String | `"graphic"` | Exactly `"graphic"` or `"avatar"` |
| `x`, `y` | Integers | `32`, `32` | −16384 through 16384; pixels from upper-left of the captured display |
| `width`, `height` | Optional integers | Omitted | 1–16384; omit a field to derive it automatically |
| `keep_aspect` | Boolean | `true` | Preserve source proportions; `false` requires both dimensions |
| `visible` | Boolean | `true` | Draw the layer; hidden assets are still loaded and validated |

Layers are composited in list order: first is behind the rest, last is on top.
Negative/off-display coordinates can intentionally clip a layer; validation does
not require every layer to fit the display. For automatic width/height, omit the
TOML field: `"-"` is an editor answer, not a valid TOML dimension.

### Kind-specific fields

| Kind | Field | Type and behavior |
| --- | --- | --- |
| `graphic` | `path` | Required nonempty path string without NUL; actual contents must be supported PNG, JPG or GIF |
| `avatar` | `idle`, `talking` | Two required nonempty path strings without NUL; both assets must actually be GIFs |
| `avatar` | `threshold` | Finite number, strictly greater than 0 and at most 1; default `0.04` RMS. Lower is more sensitive |
| `avatar` | `release_ms` | Integer 0–5000; default `250`, delay before returning to idle |

A graphic cannot contain `idle`, `talking`, `threshold` or `release_ms`. An avatar
cannot contain `path`. An avatar, even hidden, requires a microphone. The same
selected microphone is recorded and sampled separately for avatar detection;
there is no detector-only microphone setting.

### Effective size and placement

With `keep_aspect = true`:

- Both dimensions supplied: fit inside that box without changing proportions.
- Only width supplied: derive height from the source ratio.
- Only height supplied: derive width from the source ratio.
- Neither supplied: use width 320 px and derive height.

With `keep_aspect = false`, the source stretches to the explicitly supplied width
and height. Derived dimensions must also be positive and at most 16384 px.
The avatar's common box is calculated from the idle GIF; its talking GIF fits
that box when aspect preservation is enabled. Matching idle/talking canvases
make placement more predictable.

For a bottom-right layer with effective size `W × H` on a display `CW × CH` and
margin `M`, use `x = CW - ceil(W) - M`, `y = CH - ceil(H) - M`. For example, a
300×150 graphic at 1920×1080 with a 20 px margin uses `x = 1600`, `y = 910`.
The [TUI](tui.md) provides corner placement without manual calculation. Profiles
store X/Y, not corner anchors; recalculate after a resolution change.

### Asset limits

Validation uses the production Rust loader, including for hidden layers:

- Each compressed asset: at most 8 MiB; source dimensions 1–4096 px per axis.
- Each decoded still image: at most 16 MiB RGBA.
- Each GIF: at most 1024 frames and 16 MiB of full-canvas RGBA frame cache,
  plus at most 8 MiB of managed temporary buffers. These limits can reject a GIF
  even when its compressed file is small.
- Entire scene: at most 64 MiB of preloaded RGBA, counting both avatar GIFs.
- The generated internal scene description must also fit 128 KiB.

The loader detects formats from contents. Invalid/truncated data, unsupported
GIF Plain Text blocks and unsupported encodings are rejected. JPEG scan count
is bounded to 64. GIF transparency, frame delays, disposal and loop metadata are
handled by the loader; use a simple exported animation if an asset is rejected.
Reducing only the displayed width/height does **not** reduce source decoding or
frame-cache requirements: resize or simplify the source asset itself.

## Audio discovery and selection

List the current devices inside the installed app:

```bash
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama \
  /app/lib/trama/scripts/compositor.py devices
```

Use the **identifier**, not the friendly description, in TOML. Microphone choices
are inputs recognized by both GSR and PulseAudio/PipeWire; output monitor sources
are excluded. `default_input` is resolved through the audio server's current
default source before capture. If that default is a monitor or disconnected
input, select a listed microphone explicitly.

`game_audio = true` captures the default output, not one selected application.
When system audio and microphone are enabled, GSR mixes them into **one audio
track**. They are not separately editable tracks. The app does not expose audio
volume or routing controls; set levels/default devices in your desktop's audio
settings. Validation briefly captures microphone samples to confirm availability;
with an avatar, detection also captures that input while recording.

## Output and validation

`{timestamp}` expands to UTC, for example
`recording-20261110T120000.123456Z.mkv`, when each capture is prepared. Other brace
templates are rejected. Destination folders are created when recording starts.
The nearest existing parent must be a writable directory.

An existing video is never silently overwritten. Existing matching log/report
names also prevent recording; use a timestamp or another filename. A capture
produces:

| File | Contents |
| --- | --- |
| `<video>.mkv` | Recorded video and optional mixed audio |
| `<video>.mkv.gsr.log` | Engine/plugin diagnostics |
| `<video>.mkv.report.json` | Build, command, scene, timing and stream-validation information |

The sidecar suffixes are appended to the complete video filename, not substituted
for its extension.

`check` verifies matched packaged binaries, profile types, H.264 GPU/MKV support,
monitor availability, selected audio sources, microphone access, full asset
preload and the output destination. It prints effective layer sizes and RGBA
preload. It does not start capture or prove the graphics context, KMS access or
final recording will work.

`--assets-only` skips monitor/audio capability queries and microphone probing,
but still requires the matching engine/plugin/validator and validates output
paths and assets. It explicitly **does not certify capture or audio**.

Recording uses H.264 GPU encoding, constant FPS, GSR `very_high` quality and MKV;
there is no CPU encoding fallback. On stop, GSR is asked to close cleanly, then
the app checks engine/plugin completion and probes the resulting video and
expected audio streams with ffprobe. Requested durations are approximate,
include engine startup, and require additional finalization time. If completion
fails, the partial output and available diagnostics are retained rather than
deleted. A successful report still warrants playback review.

Profiles, logs and reports can contain device identifiers and absolute paths.
Review them before sharing. The scene is stored in a temporary private manifest
during recording; it is not a replacement for saving the TOML. See
[KMS security](security-kms.md) for permissions and the Flatpak's broad host access.

## Classic editor

Open it with `edit [PROFILE]`; the [TUI](tui.md) is generally easier for browsing
assets and choosing corners. The classic editor has no preview and uses
line-based input followed by Enter:

| Main choice | Action |
| --- | --- |
| `1` | Choose display |
| `2` | Choose microphone and toggle game/system audio |
| `3` | Set output path and FPS |
| `4` | Open layers/avatar menu |
| `5` | Save TOML, optionally to another path |
| `6` | Load TOML |
| `7` | Validate and summarize |
| `8` | Validate, summarize and ask whether to start recording |
| `0` | Exit |

The layers menu supports `a` add graphic, `v` add avatar, `e` edit/replace,
`o` hide/show, `q` remove, `r` reorder, and `0` return. Layer edits walk through
the fields, unlike the TUI's single-field editor. Enter keeps an existing value;
`s`/`n` answer yes/no; `-` leaves width or height automatic. Enter paths without
shell quotes in these prompts. Asset/output paths are relative to the profile
folder; save/load profile paths are relative to the command's current directory.

The editor can edit/save even when initial device discovery fails, but recording
requires full validation. Option `8` asks for confirmation (default no); direct
`record` does not. Save normalizes to schema 2 and writes relative asset/output
paths for the target profile folder; comments/formatting may change. It does not
copy assets or move video. **The classic editor does not prompt about unsaved
changes when loading or exiting**; save explicitly first. It does not restore the
TUI's last-profile state or honor the TUI's saved language preference.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| TUI appears instead of the CLI | Use `--command=python3` and the full `/app/lib/trama/scripts/compositor.py` path shown above |
| No monitors, or selected display unavailable | Run in your graphical session without sudo; run `devices` and select an exact current identifier |
| No H.264 GPU support / encoder initialization failure | Review [compatibility](compatibility.md) and the engine log. There is no CPU fallback; a detected codec alone does not guarantee working capture |
| KMS/Polkit authorization failure | Check the system-wide installation and fixed helper in [installation](flatpak.md) and [security](security-kms.md). Do not run the app as root or add persistent capabilities as a workaround |
| Missing `default_output` or microphone | Check desktop audio settings, device connection and Flatpak audio access; list devices again. Disable system audio if unwanted; no microphone requires removing the avatar |
| Avatar stays idle or talks constantly | Check the selected microphone, mute/levels, then adjust RMS threshold and release delay. Lower threshold increases sensitivity |
| Missing asset or loader/cache error | Check paths relative to the TOML folder and actual formats; resize or simplify original images/GIFs to fit the limits above |
| Output already exists / folder not writable | Use a writable destination and a fresh filename or `{timestamp}`; existing video/log/report files are not overwritten |
| Build/ABI mismatch or missing bundled component | Use matching artifacts from one installed release; do not substitute a system GSR. Repair/reinstall via [installation](flatpak.md), rather than building inside `/app` |
| Incomplete recording | Preserve the partial MKV, inspect its `.gsr.log` and `.report.json`, and review [compatibility](compatibility.md). Do not assume a partial file is finalized |

The public prerelease is for Linux x86_64. Recording, overlays, audio and orderly
stop/cancel are confirmed on Pop!_OS 24.04, COSMIC/Wayland and Intel Iris Xe;
other environments remain unverified. There is no streaming, live preview, text
overlay, HDR or measured resource-advantage claim. See
[measurements](mediciones.md) for performance scope.
