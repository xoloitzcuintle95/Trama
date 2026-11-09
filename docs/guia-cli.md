# GSR compositor CLI user guide

> Public distribution targets Flatpak: see [installation](flatpak.md).
> The [native preliminary package](paquete-preliminar.md) is development-only.
> This manual retains development/source-checkout paths and commands. The
> packaged installation includes its own GSR engine and starts with `trama`.

This page documents the **classic menu and direct commands**. The
[Trama TUI has a separate guide](tui.md), with per-field editing and corner
placement. The application is Trama; bundled graphics are neutral samples.
Personal profiles and graphics may live outside the project.

Reference manual for compositor **0.4.0**, `rust-media-overlay` plugin version 4,
on **GPU Screen Recorder (GSR) 6.1.7**. Primary environment: Pop!_OS 24.04,
COSMIC/Wayland and GPU encoding. Names/options come from the code and actual
`scripts/compositor.py` help.

The compositor prepares graphics and an avatar; GSR captures the monitor,
records audio, encodes and writes video. Editing happens before recording in a
text menu. You do not need to learn GSR's internal commands to use a profile.

The classic CLI still displays Spanish prompts and diagnostics. Literal prompts,
menu output and accepted answers are retained below so they match the program;
explanations are in English. The TUI separately supports an English interface.

## Contents

1. [Quick start: Minecraft with an avatar](#1-quick-start-minecraft-with-an-avatar)
2. [Installation and requirements](#2-installation-and-requirements)
3. [Command reference](#3-command-reference)
4. [Interactive menu reference](#4-interactive-menu-reference)
5. [Layers, geometry and avatar](#5-layers-geometry-and-avatar)
6. [TOML profile reference](#6-toml-profile-reference)
7. [Recording, output and audio](#7-recording-output-and-audio)
8. [Troubleshooting](#8-troubleshooting)
9. [Limits and test coverage](#9-limits-and-test-coverage)
10. [Reference files](#10-reference-files)

## 1. Quick start: Minecraft with an avatar

This example starts from a project checkout with native GSR installed and the
plugin built. For a first installation, complete the
[installation section](#2-installation-and-requirements) and return here.

### 1.1 Open a terminal

Open a terminal in your COSMIC session and enter the project folder. Adapt this
path to your checkout:

```bash
cd "$HOME/project-gsr-compositor"
```

Check that the sample GIFs exist:

```bash
ls -l examples/assets/idle.gif examples/assets/talking.gif
```

These are sample avatar files; other files may be used. Neither those filenames
nor that character are required.

### 1.2 Create a profile

Run without `sudo`:

```bash
python3 scripts/compositor.py edit perfil-minecraft.toml
```

If the file does not exist, a new in-memory profile opens. The editor attempts
to list displays and microphones, then shows this menu:

```text
1 pantalla | 2 micrófono/audio | 3 salida/FPS | 4 capas/avatar | 5 guardar | 6 cargar | 7 validar/resumen | 8 grabar | 0 salir:
```

Type each key and press **Enter**. Do not use arrow navigation or TUI shortcuts.

1. Type `1`. Find the display to record and enter its number. Note the resolution;
   the placement example below assumes **1920 × 1080**.
2. Type `2`. Select `1` for the default microphone or the number of an explicit
   input, such as your USB microphone if listed. At
   `Grabar juego/audio del sistema (s/n) [s]:`, press Enter to retain `s`.
3. Type `3`. At `Archivo MKV, admite {timestamp}`, enter
   `recordings/{timestamp}.mkv`. At `FPS [30]:`, press Enter.
4. Type `4` for layers, then `v` to add the avatar.

Answer the avatar form in this order:

| Prompt | What to enter |
| --- | --- |
| `GIF reposo` | `examples/assets/idle.gif` |
| `GIF habla` | `examples/assets/talking.gif` |
| `Umbral RMS 0..1 (menor = más sensible) [0.04]` | Enter |
| `Espera antes de reposo (ms) [250]` | Enter |
| `Nombre [Avatar]` | `Avatar` |
| `X [32]` | `1600` |
| `Y [32]` | `760` |
| `Ancho (- = automático) [-]` | `300` |
| `Alto (- = automático) [-]` | `300` |
| `Conservar proporción (s/n) [s]` | Enter |
| `Visible (s/n) [s]` | Enter |

At 1920 × 1080 this square avatar sits bottom-right with a 20-pixel margin.
For another resolution, use the [placement formula](#54-bottom-right-avatar).

Type `0` to return to the main menu. Type `5`, then Enter at `Guardar TOML [...]`
to save `perfil-minecraft.toml`. `Guardado:` should show the profile path.

Enter paths **without shell quotes** in menu prompts, even if they contain
spaces, for example `mis gráficos/idle.gif`. Shell commands do need quotes to
protect an argument containing spaces.

### 1.3 Validate the profile

Type `7`. The program checks assets/devices and shows the display, resolved
microphone, layers, sizes, visibility and output. If `Corregir:` appears, fix the
specified value; failed validation does not start recording.

Type `0` to exit the editor. Validation is also available from the terminal:

```bash
python3 scripts/compositor.py check perfil-minecraft.toml
```

### 1.4 Record 30 seconds

Open Minecraft and the world you want to record. Return to the terminal and run:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml --seconds 30
```

The command validates, prints the summary and starts without another confirmation.
When `Grabando. Ctrl+C termina y cierra el archivo.` appears, switch to Minecraft.
Move and speak to test video, audio and avatar response. Include silence to check
returning to idle.

Capture covers **the entire selected monitor**, including the terminal while
visible. There is no countdown, automatic game-window selection or global start
shortcut. Duration is approximate: startup is included and file-finalization time
is added.

### 1.5 Find and review the video

On completion, the terminal shows:

```text
Guardado: /ruta/del/proyecto/recordings/FECHA.mkv
Log: /ruta/del/proyecto/recordings/FECHA.mkv.gsr.log
Informe: /ruta/del/proyecto/recordings/FECHA.mkv.report.json
```

With this profile created at the project root, locate the output using:

```bash
ls -lt recordings/
```

Open the `.mkv` in a player. Check the captured content, avatar placement/animation,
system sound, voice and synchronization. CLI success does not replace visual and
auditory review.

Next time, edit the same profile or record directly:

```bash
python3 scripts/compositor.py edit perfil-minecraft.toml
python3 scripts/compositor.py record perfil-minecraft.toml
```

The second command records until you return to the terminal and press **Ctrl+C**.

## 2. Installation and requirements

### 2.1 Components and environment

| Component | Purpose |
| --- | --- |
| Project checkout | Includes `scripts/`, `rust/`, `rust/Cargo.lock`, tests and required assets |
| Python 3.11 or later | CLI and `tomllib`; Python 3.12.3 was checked here |
| Recent Rust and Cargo | Build plugin/validators; Rust 1.99.1 was checked here. No verified minimum Rust version is declared |
| C compiler, Git and build tools | Build GSR and check the C/Rust ABI |
| Compatible native GSR | Capture, audio, encoding and output; must be in `PATH` |
| Working EGL/OpenGL and graphics driver | Plugin reuses GSR's context; needs GLES 3, or GLX with GL 3.3 / GL 3 plus `ARB_sampler_objects` |
| GPU with GSR-supported H.264 | Recording requires GPU encoding without CPU fallback |
| Graphical session and DRM/KMS access | Monitor capture in COSMIC/Wayland |
| PulseAudio or compatible PipeWire service | System audio and microphone input |
| `pactl` and `parec` | Query inputs and probe/capture the microphone |
| `ffprobe` | Validate output streams on completion |
| Pillow and FFmpeg | Full test suite, not per-frame plugin drawing |

The plugin uses Rust edition 2024 and recent standard-library APIs. Do not assume
your distribution's Rust package is sufficient. Older versions than the one
used here need an actual build check.

GSR is pinned to:

```text
f97d1e392816503282d20a0804c3ce3fd2943767
```

The numeric version `6.1.7` alone is insufficient: the CLI compares installed-GSR
and plugin hashes against the build manifest. Another build may be rejected even
if it reports the same version.

This installation keeps GSR source in `third_party/gpu-screen-recorder`, separate
from compositor code. The source workflow does not install a Python package or
register a global `compositor` command; run `python3 scripts/compositor.py` from
the checkout. Packaged Trama installation is covered separately above.

### 2.2 Pop!_OS 24.04 packages

If the environment is already prepared, check components before reinstalling.
For a fresh setup, these commands are for the user to execute; they **modify the
system and require `sudo`**:

```bash
sudo apt-get update
sudo apt-get install build-essential git curl pkg-config meson ninja-build \
  python3 ffmpeg pulseaudio-utils libcap2-bin \
  libx11-dev libxcomposite-dev libxrandr-dev libxfixes-dev libxdamage-dev \
  libwayland-dev libva-dev libpulse-dev libdrm-dev libcap-dev libdbus-1-dev \
  libvulkan-dev linux-libc-dev libavcodec-dev libavformat-dev libavutil-dev \
  libswresample-dev libavfilter-dev libswscale-dev libglvnd-dev
```

For Pillow-based tests:

```bash
sudo apt-get install python3-pil
```

The list reflects inspected GSR dependencies and packages from Pop!_OS's Ubuntu
24.04 base. Exact versions/availability depend on configured repositories.
`pulseaudio-utils` provides client tools; it does not require replacing PipeWire
with a PulseAudio server. See the [official package page](https://packages.ubuntu.com/noble/pulseaudio-utils).

The encoding driver depends on the GPU. The reference Intel machine had
`intel-media-va-driver`; that does not establish compatibility elsewhere. Check
`gpu-screen-recorder --info` first. The compositor does not select/install drivers
automatically.

### 2.3 Prepare Rust

Check:

```bash
rustc --version
cargo --version
```

If Rust is missing, the [official rustup installer](https://rust-lang.org/tools/install/)
provides this Linux command, run as a normal user:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Then open another terminal or load the environment:

```bash
. "$HOME/.cargo/env"
rustc --version
cargo --version
```

Follow installer instructions. Installing the toolchain into your account needs
no `sudo`. This guide does not install or update anything automatically.

### 2.4 Obtain and build GSR

Work from the compositor checkout root. If GSR sources **already exist**, start
by checking the commit:

```bash
git -C third_party/gpu-screen-recorder rev-parse HEAD
```

For a new copy without that folder:

```bash
mkdir -p third_party
git clone https://repo.dec05eba.com/gpu-screen-recorder third_party/gpu-screen-recorder
git -C third_party/gpu-screen-recorder checkout --detach f97d1e392816503282d20a0804c3ce3fd2943767
```

Do not switch a tree containing your own work without review. The Rust build
script rejects a different baseline or changes to the header/loader/recorder used
for ABI verification.

To configure and build GSR initially, without privileges:

```bash
bash scripts/prepare-gsr.sh
```

This configures release mode with `/usr/local` prefix and system FFmpeg; portal,
per-application audio, plugin examples, systemd service and NVIDIA suspend tweak
are disabled. If GSR's folder is absent, the script clones it itself; to retain
the expected commit, first prepare the pinned copy as shown above.

For an already-configured build, rebuild without repeating initial setup:

```bash
meson compile -C third_party/gpu-screen-recorder/build
```

### 2.5 Install native GSR

After building, installation needs privileges:

```bash
sudo meson install -C third_party/gpu-screen-recorder/build
```

With that prefix, GSR and its helper install under `/usr/local/bin`. Upstream's
post-install script assigns `cap_sys_admin+ep` to `gsr-kms-server` for KMS. This
privilege belongs to the GSR helper, not the compositor. Do not run the Python
CLI with `sudo` or grant capabilities to our plugin.

GSR's old `install.sh` is deprecated and recreates the build with different
options; this guide uses Meson directly. Flatpak is not needed: this source CLI
looks for a native executable in `PATH` and loads the local `.so`.

Check:

```bash
command -v gpu-screen-recorder
gpu-screen-recorder --version
command -v gsr-kms-server
getcap "$(command -v gsr-kms-server)"
```

Expected helper capability is `cap_sys_admin=ep`. If missing, or KMS access fails,
review GSR installation output.

### 2.6 Build the compositor

From the project root, first fetch Cargo dependencies if the account lacks a
cache. Network access is required, but not `sudo`:

```bash
cargo fetch --manifest-path rust/Cargo.toml --locked
```

Then:

```bash
bash scripts/build-rust-overlay.sh
```

The script builds with `--offline --locked`, compares ABI against the C header
and generates, among other files:

```text
build/overlay-rust.so
build/overlay-rust.build.json
build/rust-target/release/scene-check
build/rust-target/release/element-check
```

It also needs `third_party/gpu-screen-recorder/build/gpu-screen-recorder`: its
hash is recorded in the manifest. Installed GSR found by the CLI must match it.
After rebuilding GSR, normally install that build and regenerate the plugin
manifest to keep them aligned.

The plugin need not be installed into `/usr/lib`: the CLI loads the known
`build/overlay-rust.so` path. Retain the checkout/artifacts; copying just
`compositor.py` elsewhere does not prepare a working application.

### 2.7 Checks before first use

```bash
python3 --version
command -v pactl
command -v parec
command -v ffprobe
ls -l build/overlay-rust.so build/overlay-rust.build.json \
  build/rust-target/release/scene-check
python3 scripts/compositor.py --help
python3 scripts/compositor.py check examples/perfil.toml --assets-only
```

The last command validates sample GIFs/configuration without a selected display.
It still requires native GSR and the correct build artifacts.

From your COSMIC-session terminal, also check:

```bash
ls -l /dev/dri
gpu-screen-recorder --info
gpu-screen-recorder --list-capture-options
gpu-screen-recorder --list-audio-devices
pactl info
python3 scripts/compositor.py devices
```

Actual availability depends on driver, DRM/KMS access, Wayland session, audio
server and connected devices. An SSH session, container or terminal without
access to the graphical session may build successfully and still be unable to
capture.

## 3. Command reference

All syntax below runs from the project root. Elsewhere, use the full script path.
A relative profile argument is resolved from the terminal's current directory.

### 3.1 Help

```text
python3 scripts/compositor.py [-h] {devices,edit,check,record} ...
```

`-h` and `--help` print help and exit. Both work for the main program and each
subcommand:

```bash
python3 scripts/compositor.py --help
python3 scripts/compositor.py devices --help
python3 scripts/compositor.py edit --help
python3 scripts/compositor.py check --help
python3 scripts/compositor.py record --help
```

This CLI has no `--version`. Query GSR using `gpu-screen-recorder --version`;
the compositor version is in [`rust/Cargo.toml`](../rust/Cargo.toml).

### 3.2 Without a subcommand

```bash
python3 scripts/compositor.py
```

Opens the editor with a **new** profile based on the current directory. It does
not automatically load `perfil.toml`, even if that file exists. Saving proposes
`perfil.toml` in the current directory. There is no automatic saving.

### 3.3 `devices`

```text
python3 scripts/compositor.py devices [-h]
```

Lists GSR-advertised monitors, microphone identifiers/descriptions and
`default_output` availability. No arguments or capture options.

```bash
python3 scripts/compositor.py devices
```

Names/order depend on the machine. The `default_input` option does not prove the
current default is valid; it is resolved and checked before recording. No profile
is needed and this command does not validate the plugin as `check` does.

### 3.4 `edit`

```text
python3 scripts/compositor.py edit [-h] [profile]
```

| Argument | Required | Behavior |
| --- | --- | --- |
| `profile` | No | Load an existing TOML; otherwise prepare a new profile at that path. Without an argument, create a new profile based on the current directory |

```bash
python3 scripts/compositor.py edit perfil-minecraft.toml
python3 scripts/compositor.py edit "perfiles/desarrollo diario.toml"
python3 scripts/compositor.py edit
```

Invalid existing TOML produces an error, not a silently substituted new profile.
The editor can save even if device discovery failed, but recording still requires
validation.

### 3.5 `check`

```text
python3 scripts/compositor.py check [-h] [--assets-only] profile
```

| Argument or option | Default | Effect |
| --- | --- | --- |
| `profile` | No value; required | Existing TOML to validate |
| `--assets-only` | Off | Skip display/audio queries; check configuration, assets, build and output path |

```bash
python3 scripts/compositor.py check perfil-minecraft.toml
python3 scripts/compositor.py check examples/perfil.toml --assets-only
```

Normal mode verifies build compatibility, GSR-advertised GPU H.264/MKV, selected
monitor, configured audio, microphone samples, real asset decoding, geometry,
pixel budget and output destination. Microphone probing briefly captures data to
confirm the source produces samples; it does not save that audio to a file.

`--assets-only` checks neither hardware, effective capture permissions nor audio.
It prints `SOLO RECURSOS: pantallas, audio y captura no comprobados.`. It is not
a full recording test or preview.

`check` creates neither video nor output folder. Its displayed timestamp belongs
to that validation; a later `record` generates another filename.

### 3.6 `record`

```text
python3 scripts/compositor.py record [-h] [--seconds SECONDS] profile
```

| Argument or option | Default | Effect |
| --- | --- | --- |
| `profile` | No value; required | Load and validate this TOML before recording |
| `--seconds SECONDS` | No fixed duration | Approximate seconds from GSR launch; accepts 1..7200, including decimals |

30-second test:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml --seconds 30
```

Ten minutes:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml --seconds 600
```

Without automatic stopping:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml
```

Recording starts directly after the summary, without a menu/confirmation. To stop
early or without a time limit, return to that terminal and press **Ctrl+C**.
Wait for `Guardado:` or an error diagnostic. Normal shutdown sends SIGINT to GSR
and waits up to 15 seconds, then forces termination and marks incomplete output
if needed. Closing the terminal or SIGKILL should not be the normal stop method.

Duration belongs to this subcommand. The classic menu has no duration field.
There is no pause/resume or global shortcut to stop from another application.

### 3.7 Exit codes and option scope

| Code | Usual meaning |
| --- | --- |
| `0` | Command completed or normal menu exit |
| `2` | CLI-detected argument, profile, device, build or recording error |
| `130` | Interrupt/EOF caught at the top level, such as Ctrl+C in the menu |

Ctrl+C during `record` requests finalization and may return `0` if the file closes
correctly. In the menu, action errors are shown and editing continues; a later
`0` does not certify that all earlier actions succeeded.

Those four subcommands are the complete current scene CLI. `compositor.py` has
no `--screen`, `--mic`, `--output`, `--fps`, `--preview`, `--scene` or `--avatar`
options: edit those settings through the menu or TOML. Earlier single-element
scripts have separate options; see [element configuration](configuracion-elemento.md).

## 4. Interactive menu reference

### 4.1 Input rules

The menu is a sequence of text prompts, not an arrow-navigable screen. Press
Enter after each response.

| Prompt type | Meaning of Enter |
| --- | --- |
| Form with a value in `[...]` | Keep that value |
| `(s/n)` question | Keep the bracketed `s` or `n` |
| Numbered display/microphone/layer selection | Type a number; empty Enter does not select the first option |
| Main/layer menu action | Empty Enter does not go back or confirm; it reports an unknown option or asks again |
| `TOML a cargar:` or `Nueva posición 1..N:` | A path or number is required; no default |

For `(s/n)`, only `s` and `n` are accepted, including uppercase. `sí`, `yes` and
`y` are not valid answers. Layer action letters must be lowercase. There is no
general mid-form cancel key: Ctrl+C exits the entire editor without saving.
Ctrl+D at an input prompt also exits without saving.

Numbers are integers except RMS threshold, which accepts decimals. Use a decimal
point (`0.04`), not comma (`0,04`). Do not enter units, quotes or `%`.

### 4.2 Startup and main menu

Startup attempts device discovery. Failure is reported but editing/saving can
continue. The header shows profile, display, microphone and layer count, followed
by the main menu.

| Key | Action |
| --- | --- |
| `1` | Display |
| `2` | Microphone and system audio |
| `3` | Output file and FPS |
| `4` | Layers and avatar |
| `5` | Save profile |
| `6` | Load another profile |
| `7` | Validate and show summary |
| `8` | Validate, show summary and record if confirmed |
| `0` | Exit program |

Exiting or loading another profile neither saves changes automatically nor asks
about them. Save with `5` beforehand to retain them. The menu does not change
scenes during an active recording.

### 4.3 `1`: display

GSR's list is queried again. Each option shows monitor name/resolution, such as
`MONITOR-1: 1920×1080`.

At `Pantalla (número):`, type a number from the current list, not the monitor
name. The profile stores its name rather than selection index.

Choosing returns to the main menu. There is no cancel `0` inside this selection;
it is an out-of-range number. Only monitors are offered, even though GSR has
other capture modes such as windows, regions or portal.

### 4.4 `2`: microphone and audio

The list begins with:

```text
1. Predeterminado del sistema
2. Sin micrófono (requiere no tener avatar)
```

Specific currently queried inputs follow. At `Micrófono (número):`, enter the
desired number. Here `2` means no microphone, not the main-menu audio action.

Next prompt:

```text
Grabar juego/audio del sistema (s/n) [s]:
```

The displayed value can be `[n]` when disabled in the profile. Answer `s`, `n`,
or Enter to retain it, then return to the main menu.

An avatar needs a microphone even while hidden. To record without a microphone,
remove the avatar layer; hiding it is insufficient. Recording a microphone
without an avatar is supported.

### 4.5 `3`: output and FPS

Prompts appear in this order:

1. `Archivo MKV, admite {timestamp} [...]`: a file path, not just a folder.
2. `FPS [...]`: integer `1`..`120`, default `30`.

Example filename response:

```text
recordings/minecraft-{timestamp}.mkv
```

The extension must be lowercase `.mkv`. Container selection is not exposed.
Relative paths start at the profile's base directory. Missing folders are
created at recording time. This changes neither monitor resolution nor the
captured application's FPS limit.

### 4.6 `4`: layers and avatar

First shown:

```text
Capas (primera = fondo):
```

Each row has number, name, type (`graphic` or `avatar`) and visibility. Then:

```text
a agregar gráfico | v agregar avatar | e editar/reemplazar | o ocultar/mostrar | q quitar | r reordenar | 0 volver:
```

| Key | Action |
| --- | --- |
| `a` | Append a PNG/JPG/GIF graphic above previous layers |
| `v` | Append an avatar; at most one |
| `e` | Ask for layer number, then edit its form or replace files |
| `o` | Ask for a layer, then immediately toggle in-memory visibility |
| `q` | Remove a chosen layer from configuration without deleting its file |
| `r` | Ask for a layer, then `Nueva posición 1..N:`, moving it within the list |
| `0` | Return to main menu |

`q` means **remove**, not leave the submenu. Layer numbering starts at `1`.
List order defines drawing order; no independent depth or `z-index` field exists.

#### Graphic form: `a` or `e` on `graphic`

Prompt order:

1. `Ruta PNG/JPG/GIF [...]`.
2. `Nombre [...]`.
3. `X [...]`.
4. `Y [...]`.
5. `Ancho (- = automático) [...]`.
6. `Alto (- = automático) [...]`.
7. `Conservar proporción (s/n) [...]`.
8. `Visible (s/n) [...]`.

A new graphic defaults to menu name `Gráfico`, X/Y `32`, unspecified dimensions
(`-`), and `s` for aspect ratio and visibility. Enter a real path: Enter on an
empty path does not select a file.

For an existing layer, Enter retains its file. Enter a new path to replace it,
including another supported format. The type remains `graphic`; this form cannot
convert it to an avatar.

#### Avatar form: `v` or `e` on `avatar`

Prompt order:

1. `GIF reposo [...]`.
2. `GIF habla [...]`.
3. `Umbral RMS 0..1 (menor = más sensible) [...]`.
4. `Espera antes de reposo (ms) [...]`.
5. `Nombre [...]`.
6. `X [...]`.
7. `Y [...]`.
8. `Ancho (- = automático) [...]`.
9. `Alto (- = automático) [...]`.
10. `Conservar proporción (s/n) [...]`.
11. `Visible (s/n) [...]`.

Menu defaults are name `Avatar`, threshold `0.04`, release `250`, X/Y `32`,
automatic dimensions, aspect preservation and visibility enabled. Enter both
paths when adding. Idle/talking are GIF files, not separate layers.

Completing a form returns to the layer submenu. Configuration is structurally
validated, but files decode when validating/recording. A listed path does not
mean the resource has already loaded successfully.

### 4.7 `5`: save

Prompt:

```text
Guardar TOML [ruta/propuesta/perfil.toml]:
```

Enter retains the proposed path. Without an associated path, `perfil.toml` in the
current directory is proposed. Another filename/folder can be typed. Relative
paths for the **TOML being saved** start at the terminal's current directory.

Required folders are created and TOML is replaced through a temporary file.
Existing profiles are overwritten without another confirmation. Content is
normalized to schema 2; rewriting does not preserve comments or original layout.
Saving does not copy graphic resources.

### 4.8 `6`: load

Prompt:

```text
TOML a cargar:
```

Enter the path to an existing TOML. Empty Enter has no default file. Relative
paths start at the terminal's current directory. Successful loading replaces
in-memory configuration and returns to the main menu. Previous unsaved changes
are discarded without confirmation.

### 4.9 `7`: validate and show summary

No more values are requested. Success shows display/resolution/FPS, resolved
technical microphone ID, system audio, ordered layers, files, coordinates,
effective dimensions, visibility, avatar sensitivity, RGBA budget and output,
then returns to the main menu.

This neither previews nor records. Timestamped output paths may differ on the
next validation. Errors are shown as `Corregir:` and allow returning to editing.

### 4.10 `8`: record and `0`: exit

`8` repeats full validation and displays the summary, then asks:

```text
Iniciar grabación (s/n) [n]:
```

Enter or `n` does not start; `s` starts capture. Menu recording has no fixed
duration: return to the terminal and press Ctrl+C. Finalization returns to the
main menu. Edit settings before another capture. In-memory settings used to
record are not automatically saved to TOML.

`0` in the main menu exits. `0` under layers only goes back one level.

## 5. Layers, geometry and avatar

### 5.1 Add, replace and order

The profile's layers form the current scene. Graphics and one avatar are
supported. There is no multi-scene library, transitions or live scene switching.

To add, use `4`, then `a` or `v`. To replace a graphic, use `e`, select its number
and change `Ruta PNG/JPG/GIF`; retain other values with Enter. Replace avatar
GIFs by editing paths inside that same layer.

Moving/scaling means editing X/Y/width/height with `e`. Hide using `o` or
`Visible = n`; remove with `q`; reorder with `r`. Position `1` is beneath others
and the final layer is on top. A large opaque top layer can cover other content.

There is no duplicate-layer or change-type option. Add another layer with the
same file, or remove/recreate it with the desired type. Repeated sources are
not deduplicated in memory.

### 5.2 Coordinates and size

Origin `(0, 0)` is the **video's upper-left corner**. X increases rightward and Y
downward. These are recorded-canvas pixels, not source-image or terminal pixels.

The CLI records the chosen monitor at its capture resolution; it exposes no
independent output resolution. Changing monitor, resolution or orientation may
require repositioning layers. Width `300` means graphic width, not 300-pixel video.

| Configured dimensions | Result with aspect preservation |
| --- | --- |
| Neither | Width 320; height derived from the file |
| Only `width` | Derive height |
| Only `height` | Derive width |
| Both | Uniform scale to fit that box |

The box aligns at X/Y by its upper-left corner, without automatic centering or
crop-to-fill. A square GIF with width `300` and height `200` draws at
**200 × 200**, potentially leaving right/bottom space inside the requested box.

In the menu, `-` removes an explicit dimension. Do not enter `0`; it is invalid.
To stretch, answer `n` for aspect preservation and specify width and height.
Allowed coordinates are integers `-16384`..`16384`; explicit dimensions are
integers `1`..`16384`. Derived dimensions must also be positive and at most
16384, but may be fractional.

Negative X/Y can put part of a graphic outside the frame. OpenGL clips it without
automatically moving the layer into view. A completely offscreen layer may pass
validation and remain invisible.

### 5.3 Formats, transparency and animation

| Format | Behavior |
| --- | --- |
| PNG | Static image with transparency and partial alpha |
| JPG/JPEG | Opaque static image, no transparency |
| GIF | Animation with transparency, frame timings, disposal and repetition |

Content determines the format, not just extension. APNG, video, SVG and text are
unsupported. There is no opacity selector, chroma key, filter, rotation or
in-program resource editor.

Source alpha is blended over capture; it does not make the MKV background
transparent. GIF transparency is defined by its palette; use PNG for edges with
partial alpha.

GIFs are preloaded and composed with partial-frame/disposal handling. Infinite
loops continue; finite repetition holds the final frame when finished. Without
a loop extension, a GIF plays once. A missing/zero frame delay uses the current
**100 ms** policy; other delays are converted from GIF's 10 ms units. The menu
has no speed/loop controls: these come from the file.

Hidden layers are still validated and retain caches/textures. Hiding permits
neither nonexistent/malformed files nor bypassing memory budgets. Remove a layer
from the profile to stop loading it.

### 5.4 Bottom-right avatar

For canvas `W × H`, effective element size `w × h` and margin `m`:

```text
X = W - w - m
Y = H - h - m
```

At **1920 × 1080**, with a **300 × 300** square avatar and margin **20**:

```toml
x = 1600
y = 760
width = 300
height = 300
keep_aspect = true
```

These are explicit coordinates, not an anchor. This classic CLI has no
`bottom-right`, percentage position or automatic adjustment after resolution
changes. Use summary effective dimensions for calculations. Transparent margins
inside the GIF can make visible content appear farther from the edge than its
canvas.

### 5.5 Idle, talking, threshold and release

An avatar occupies one list position and shares X/Y, size and visibility between
`idle` and `talking`. Both must be GIFs, but their canvases may differ. Idle
geometry defines the common box; each source fits it with its aspect ratio
preserved. Different aspect ratios can leave empty space. Without aspect
preservation they stretch to the explicit box.

The detector measures RMS amplitude, not words:

- `threshold` is the minimum talking level, greater than `0` and at most `1`.
- Default is `0.04`. Lower values increase sensitivity; higher values reduce it.
- `release_ms` is time since the last above-threshold block before returning idle:
  `0`..`5000` ms, default `250`.
- Detector audio is mono float32 at 16 kHz, evaluated in 20 ms blocks. This rate
  does not set GSR's recorded-audio rate.
- Switching idle/talking restarts the incoming GIF's clock. While selected, it
  follows its own timing and loop.

Tune with a short recording containing silence, normal speech and keyboard
noise. Gradually lower threshold if speech does not activate; raise it for noise
activation. Increase release if it switches too quickly between phrases. There
is no level meter, automatic calibration, speech recognition or shake in the
current version. Keyboard, fan, music reaching the microphone and other noise
can activate talking.

## 6. TOML profile reference

### 6.1 Complete example

This profile is syntactically/structurally valid. Recording requires a real display
name and the listed files. Save it as `perfil.toml` at the project root, for
example, using neutral graphics included in `examples/assets/`:

```toml
schema_version = 2

[recording]
screen = "NOMBRE_DE_TU_MONITOR"
output = "recordings/minecraft-{timestamp}.mkv"
fps = 30
game_audio = true
microphone = "default_input"

# First layer: geometric sample below the avatar.
[[layers]]
name = "Marco"
kind = "graphic"
path = "examples/assets/overlay.png"
x = 20
y = 20
width = 400
height = 120
keep_aspect = true
visible = true

# Last layer: above the frame.
[[layers]]
name = "Avatar"
kind = "avatar"
idle = "examples/assets/idle.gif"
talking = "examples/assets/talking.gif"
x = 1600
y = 760
width = 300
height = 300
keep_aspect = true
visible = true
threshold = 0.04
release_ms = 250
```

`NOMBRE_DE_TU_MONITOR` is a placeholder, not a valid device. Choose through the
menu or replace it with an identifier from `devices`. To use only the avatar,
remove the entire first `[[layers]]` block; do not keep a hidden layer pointing
to a nonexistent sample file.

An [included avatar profile](../examples/perfil.toml) is also available. Its display
is deliberately empty for selection on your own machine; device validation fails
until configured.

### 6.2 Top-level fields

| Field | Required | Default and rules |
| --- | --- | --- |
| `schema_version` | No, but recommended | Omitted means version 1 import; saving writes `2`. Integers `1` and `2` are accepted |
| `[recording]` | No | Omission uses the next table's defaults; select a display before recording |
| `[[layers]]` | No | Zero or more ordered tables; up to 16 layers and one avatar |

Unknown keys are rejected; do not invent fields. `_base` is internal program
data and must not appear in a user profile.

### 6.3 `[recording]` fields

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `screen` | String | `""` | GSR-advertised monitor name; empty requires selection before recording |
| `output` | String | `"recordings/{timestamp}.mkv"` | `.mkv` filename; absolute or relative to TOML |
| `fps` | Integer | `30` | 1..120 |
| `game_audio` | Boolean | `true` | Capture the default system audio output |
| `microphone` | String | `"default_input"` | Default input, explicit input identifier or `""` to disable |

Legacy `screen = "screen"` resolves to the concrete monitor only when exactly one
is available. With several, it is ambiguous and requires selection. It does not
mean the display where the terminal was launched.

### 6.4 Common layer fields

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `name` | String | `"Capa N"`, N starting at 1 | 1..128 UTF-8 bytes; label, not path |
| `kind` | String | `"graphic"` | `"graphic"` or `"avatar"` |
| `x` | Integer | `32` | -16384..16384 |
| `y` | Integer | `32` | -16384..16384 |
| `width` | Optional integer | No explicit dimension | 1..16384; follows aspect-ratio rules |
| `height` | Optional integer | No explicit dimension | 1..16384 |
| `keep_aspect` | Boolean | `true` | `false` requires explicit width and height |
| `visible` | Boolean | `true` | `false` keeps the layer loaded without drawing |

TOML booleans are `true`/`false`, not `s`/`n`. For an automatic dimension omit its
line: `width = "-"`, `width = 0` and `width = null` are invalid. Omitting both
means effective default width 320. Initial menu names (`Gráfico`, `Avatar`) can
differ from names generated when omitted in TOML.

### 6.5 Graphic and avatar fields

For `kind = "graphic"`:

| Field | Required | Purpose |
| --- | --- | --- |
| `path` | Yes | Path to a loadable PNG, JPG or GIF |

Do not include `idle`, `talking`, `threshold` or `release_ms` in a graphic.

For `kind = "avatar"`:

| Field | Required | Default and purpose |
| --- | --- | --- |
| `idle` | Yes | Idle GIF path |
| `talking` | Yes | Talking GIF path |
| `threshold` | No | `0.04`; finite number greater than zero and at most one |
| `release_ms` | No | `250`; integer 0..5000 ms |

Do not include `path` in an avatar. `recording.microphone` cannot be empty if an
avatar exists, even with `visible = false`. `[[layers]]` block order determines
drawing order; no `order` field exists.

### 6.6 Paths and output names

There are two different bases:

| Where a path is entered | Relative-path base |
| --- | --- |
| Command `profile` argument | Terminal's current directory |
| Menu `Guardar TOML` and `TOML a cargar` | Terminal's current directory |
| Profile `path`, `idle`, `talking`, `recording.output` | TOML folder |
| Asset/output paths entered in the editor | Profile base folder; initially current directory if unnamed |

Absolute paths and `~` expansion are accepted. Variables such as `$HOME` inside
TOML/menu input are not expanded: use `~` or a real path. The shell does expand
`$HOME` when appropriate in a shell command.

For example, `perfiles/minecraft.toml` containing `idle = "assets/idle.gif"` looks
for `perfiles/assets/idle.gif`, not project-root `examples/assets/idle.gif`.
Launching from another folder does not change that interpretation.

Saving writes paths relative to the TOML's new location while preserving actual
targets. Save as in another folder may introduce `../`: it neither moves images
nor automatically changes the effective video folder. New relative paths entered
after saving use the new profile directory as base.

`{timestamp}` becomes UTC date/time with microseconds when preparing capture,
such as `20261109T041847.260757Z`. It is not a shell variable. It is the only
supported template: no `{scene}`, `{game}` or `{counter}`. A fixed name works,
but the next capture is rejected if video or log/report already exists. Videos
are not automatically overwritten.

### 6.7 Reuse and sharing

To share a profile and graphics, retain a relative structure:

```text
mi-perfil/
  perfil.toml
  assets/
    marco.png
    idle.gif
    talking.gif
  recordings/
```

In that TOML use `assets/marco.png`, `assets/idle.gif`, `assets/talking.gif` and
`recordings/{timestamp}.mkv`. Copy the entire folder. Sources are not embedded
in TOML or a compositor package.

On the other machine, open the editor, select its display/microphone, save and
validate. Hardware identifiers are not portable. Profiles/images do not include
the program, native GSR or drivers.

To reuse without changing files:

```bash
python3 scripts/compositor.py edit mi-perfil/perfil.toml
python3 scripts/compositor.py record mi-perfil/perfil.toml --seconds 30
```

### 6.8 Backward compatibility

No earlier TOML profiles were found in the tree when this CLI was implemented.
The available importer supports schema 1 with a single element:

```toml
schema_version = 1

[recording]
screen = "NOMBRE_DE_TU_MONITOR"
microphone = ""

[element]
media = "assets/idle.gif"
x = 32
y = 32
width = 300
visible = true
```

`[element]` accepts `path` instead of `media`; root-level `media` is also accepted.
Do not mix the old element and `layers`. Current `recording`/`layers` structure
with version 1 also normalizes to 2. Saving writes the current format. Other
unknown older formats are not guaranteed importable.

Single-element scripts and environment variables remain a separate path.
`compositor.py record` uses the profile and clears `GSR_RUST_*` and
`GSR_OVERLAY_*` from the child environment so they do not alter the saved scene.

## 7. Recording, output and audio

### 7.1 Display and effective settings

The stored monitor name selects capture, not the display where the terminal
opened or where focus currently is. This monitor path uses GSR/KMS and does not
request capture through the COSMIC portal.

Exposed settings:

- Capture monitor.
- MKV output path/name.
- FPS, 1..120.
- System-audio on/off and microphone selection.
- Profile layers and avatar.

Fixed implementation settings:

| Setting | Value sent to GSR |
| --- | --- |
| Video | `-k h264` |
| Quality | `-q very_high` |
| Encoder | `-encoder gpu` |
| CPU fallback | `-fallback-cpu-encoding no` |
| Frame mode | `-fm cfr` |
| Profile container | MKV |

This CLI exposes no bitrate, audio-codec/rate, independent resolution, HDR,
window capture, application-audio selection, replay, streaming or pause options.
Unexposed GSR options cannot be passed as extra `compositor.py` arguments.

### 7.2 Microphone and system audio

The list intersects GSR-known inputs with `pactl` sources, excluding output
monitors. Choose:

- `default_input`: resolved to a concrete identifier at validation/start.
- An explicit input: retains its identifier even if list order changes.
- No input: `microphone = ""`, incompatible with an avatar.

The same resolved input records voice and drives the avatar; separate microphones
cannot be selected for these functions. If an explicit input disappears, it is
reported before recording and another must be chosen, without silently falling
back to the default.

`game_audio = true` captures default system output, which may include any
application, music and notifications. It does not isolate a game. With microphone
and system audio enabled, GSR receives one combined source:

```text
default_output|device:IDENTIFICADOR_DEL_MICROFONO
```

This creates one mixed track; the menu exposes neither separate tracks nor
individual volume controls. Avatar threshold **is not a volume control** and
does not modify recorded sound.

The detector opens a second capture of the same input through `parec`. GSR keeps
its own audio/video clocks. Detector mono 16 kHz does not set file-audio rate;
the CLI does not configure it through `-ac`, `-ab` or a sample-rate argument.

Do not switch devices during capture: there is no automatic reconnection. A
closed detector pipe disables the overlay, logs a diagnostic and causes the CLI
to mark the result incomplete at the end. There is no watchdog if the server
stops delivering samples without closing the pipe.

### 7.3 Starting and stopping

| Start method | Stop method |
| --- | --- |
| Menu `8`, then `s` | Ctrl+C in the terminal; return to menu |
| `record perfil.toml --seconds 30` | Automatic stop or earlier Ctrl+C |
| `record perfil.toml` | Ctrl+C; return to shell |

Without `--seconds`, no 7200-second deadline is imposed. That limit applies to
the fixed-duration argument. Disk space, devices and the system still limit
session length.

There is no countdown or scheduled start. Keep the terminal accessible for
stopping. Wait for finalization before opening/moving the output.

### 7.4 Files and final checks

For output `grabacion.mkv`, these are created:

| File | Contents |
| --- | --- |
| `grabacion.mkv` | Video and configured audio |
| `grabacion.mkv.gsr.log` | GSR/plugin output and diagnostics |
| `grabacion.mkv.report.json` | Command, build hashes, effective scene, exit code, timing, ffprobe metadata and `completed` state |

The report is written after process completion and checks; it is neither live
progress nor a scene CPU/RAM measurement.

The CLI checks nonempty output, process exit, plugin load/unload and expected
video/audio streams. Failure retains partial output and identifies the log/report
to inspect. Very early interruption or GSR-launch failure may leave an empty file
or no report.

Inspect a file manually with:

```bash
ffprobe -v error -show_streams -show_format -of json "recordings/grabacion.mkv"
```

Replace the path with the one printed by `Guardado:`. An audio stream does not
prove audible voice; duration/FPS do not prove freedom from freezes, duplicates
or drift. Play the result.

## 8. Troubleshooting

Configuration errors usually begin with `Corregir:`. In the editor, fix the value
and repeat `7`. A direct command exits on failure; use `edit`, correct and save
before recording again.

### 8.1 GSR or plugin unavailable

**Symptom:** `Falta gpu-screen-recorder en PATH`, `build: ejecuta bash
scripts/build-rust-overlay.sh`, or a hash/ABI error.

**Check:**

```bash
command -v gpu-screen-recorder
gpu-screen-recorder --version
ls -l build/overlay-rust.so build/overlay-rust.build.json \
  build/rust-target/release/scene-check
git -C third_party/gpu-screen-recorder rev-parse HEAD
```

Build missing artifacts with `bash scripts/build-rust-overlay.sh`. For missing
Cargo cache, run `cargo fetch --manifest-path rust/Cargo.toml --locked` with
network access, then repeat. If GSR/manifest differ, check the binary returned
by `command -v`, commit and installed local build. Do not edit hashes to bypass
verification; align builds and regenerate the manifest.

### 8.2 Missing display or inaccessible graphical session

**Symptom:** `recording.screen: '...' no disponible`, no advertised monitors or
Wayland-server connection errors.

**Check from a COSMIC terminal as a normal user:**

```bash
printf 'Tipo de sesión: %s\nWayland: %s\n' "$XDG_SESSION_TYPE" "$WAYLAND_DISPLAY"
ls -l /dev/dri
gpu-screen-recorder --list-capture-options
python3 scripts/compositor.py devices
```

If a monitor was renamed/disconnected, select it again with `1`. If a legacy
profile uses `screen` with multiple monitors, choose a concrete one. Graphic
connection/DRM failures are not fixed by changing X/Y or using `--assets-only`.
Check session, driver and KMS helper; do not try to compensate with sudo on the
compositor.

### 8.3 Missing or disconnected microphone

**Symptom:** `recording.microphone: '...' no está disponible como entrada`, or
failure to capture samples from the source.

**Check:**

```bash
gpu-screen-recorder --list-audio-devices
pactl --format=json list sources
pactl get-default-source
python3 scripts/compositor.py devices
```

Connect the device and query again. In `edit`, option `2`, choose the current
input/default and save. The displayed commercial name is not the technical
identifier used in TOML. A default output monitor is not accepted as microphone
input.

If `pactl`/`parec` is missing, check `pulseaudio-utils`. If `pactl info` fails,
check the audio service and user session before changing the profile.

### 8.4 Missing, invalid or oversized GIF

**Symptom:** `layers[N].path`, `idle` or `talking` reports a nonregular file, or
the validator reports header, truncated-GIF, disposal or budget errors.

**Check:**

```bash
python3 scripts/compositor.py check perfil-minecraft.toml --assets-only
ls -l examples/assets/idle.gif examples/assets/talking.gif
```

Check path bases: sources resolve from the TOML folder. For graphics use `4`,
`e`; for avatars edit both paths in that form. Renaming an extension does not
convert a file. Hiding does not bypass validation: replace the resource or
remove its layer.

If over budget, reduce dimensions/frame count **in the source file** using an
external tool, or use fewer layers. Profile `width`/`height` only changes drawing,
not source-image preload cost.

### 8.5 Avatar never changes, always talks or returns too quickly

**Symptom:** only one state appears, or keyboard/noise activates it.

Check in order:

1. Layer must be `kind = "avatar"`, not a graphic pointing only to idle.
2. It must be visible, on canvas and not covered by another opaque layer.
3. Check the concrete microphone shown by `check`, plus mute/gain in system audio.
4. Use visually distinct idle/talking GIFs; pointing both to one file hides state changes.
5. Edit threshold/release, save and make another short recording.
6. Inspect `.gsr.log` for `gsr-rust:` or `parec` diagnostics.

Lower threshold for missed speech, raise it for noise activation. Increase
`release_ms` if idle returns too soon. The menu has no level meter or interactive
level test. Long GIF frames can look static even when clock/state are working.

### 8.6 Offscreen, distorted or unexpectedly sized layer

**Symptom:** missing, clipped, too small or not filling its box.

Run `check` for effective dimensions and compare X/Y against selected monitor
resolution. Use `4`, `e` to correct; `4`, `o` for hidden state and `r` if behind
another layer. A simple test is X/Y `32`/`32`, width `300` and automatic height
(`-`).

Aspect preservation need not fill both dimensions. Remove an inherited limiting
dimension with `-`. Idle defines the avatar's shared box. This CLI has no corner
anchoring and does not validate that the element is visible within the canvas.

### 8.7 Missing or wrong audio

**Symptom:** missing voice, system sound, both, or another application's sound.

Review the summary and fields:

- `game_audio = true` for default-output sound.
- Nonempty `microphone` for voice; the avatar does not enable another source itself.
- Correct system default, unmuted device and useful volume.

Check sources and output:

```bash
pactl info
gpu-screen-recorder --list-audio-devices
ffprobe -v error -show_streams -of json "recordings/grabacion.mkv"
```

An audio track containing silence can still pass ffprobe; selection, mute or gain
may be wrong. Change input with `2` and review default system output. System audio
is not isolated to one application. This CLI has no mixer, gain or separate tracks.

### 8.8 Missing/empty output or incomplete recording

**Symptom:** no `Guardado:`, a command ends with `Corregir:`, or output is not in
the expected folder.

Read `Salida:` and remember output paths are TOML-relative. A profile in
`perfiles/` with `recordings/...` writes below `perfiles/recordings/`, unless Save
as preserved a different original target. A previous `check` filename may differ
because of `{timestamp}`.

Check the actual folder, permissions, free space and auxiliary files:

```bash
ls -lt recordings/
df -h .
cat "recordings/grabacion.mkv.gsr.log"
cat "recordings/grabacion.mkv.report.json"
```

Adapt the paths. Failure before GSR launch may create neither video nor log.
Launch failure can leave a zero-byte file. If GSR captured anything, partial video
is retained and a report is written when result handling completes. Existing
fixed names, including existing log/report names, are rejected; choose another
or use `{timestamp}`.

For encoder issues:

```bash
gpu-screen-recorder --info
```

H.264 GPU encoding is required; there is no automatic CPU fallback. If it is not
advertised, resolve driver/compatibility/environment: the profile offers no
alternative codec. A black screen with visible graphics does not prove capture
works. Retain the log and check GSR in the target session before blaming the GIF.

## 9. Limits and test coverage

### 9.1 Current limits

| Resource or feature | Limit |
| --- | --- |
| Layers per profile | 16, including the avatar |
| Avatars | One; two GIF sources in one layer |
| TOML and internal manifest | Up to 128 KiB each |
| Compressed graphic file | Up to 8 MiB per source |
| Source dimensions | 1..4096 per axis, also subject to byte budgets |
| RGBA image / one GIF cache | Up to 16 MiB |
| GIF frames | Up to 1024 |
| Managed GIF temporaries | Up to 8 MiB per decoder |
| Total preloaded scene RGBA | Up to 64 MiB, including hidden layers and both avatar GIFs |
| JPEG | Up to 64 scans; no promise of ICC management or automatic EXIF orientation |
| Composition | 8-bit SDR; HDR rejected |

RGBA budget is not total RAM: textures, GSR buffers, driver memory, allocator and
temporaries add costs. A layer rejected for exceeding the total may already have
been temporarily decoded. Repeated resources load separately. Neither 150 MB nor
lower consumption than OBS is guaranteed for an unmeasured scene.

Loading/decoding precedes drawing. `draw` neither reads files nor decodes again;
GIF textures update only on frame changes. Configuration is fixed during capture.
This classic menu is not a full-screen TUI; use [Trama's interface](tui.md) for
that. There is no GUI, preview, live editing, text, streaming, shake or multi-scene
management. Temporary scene JSON is internal, not another user-managed file.

### 9.2 What was checked and what remains

| Evidence | Coverage |
| --- | --- |
| Actual CLI help | Four subcommands and their syntax/options |
| Profile/CLI tests | Save/load, relative/Unicode paths, layer menu, order/visibility, v1 import, assets and budgets |
| Simulated device errors | Missing explicit microphone without fallback, GSR/PulseAudio response parsing; not physical unplugging |
| Invalid resources | Missing GIF and malformed JPEG, including hidden state |
| EGL/OpenGL hosts with llvmpipe | Pixels, transparency, order, clipping, animation, GL state, shutdown and panic barriers; not Iris Xe |
| Avatar with synthetic PCM | Threshold, release and GIF switching, including differently sized sources |
| Simulated process runner | Save/load TOML, produce real MKV with FFmpeg synthetic color/audio, signal stop and inspect; not real GSR capture |

Automated tests use simulated devices/software GL, not KMS access or physical
audio certification. Validate in the target COSMIC session: monitor/input
selection, video, system/microphone audio, avatar response, stability and resources
during an extended session. A 30-second test is a first step, not a performance
certification.

To run checks from the project root:

```bash
bash scripts/check-rust-overlay.sh
CARGO_TARGET_DIR=build/rust-target cargo clippy --manifest-path rust/Cargo.toml \
  --offline --locked --all-targets --all-features -- -D warnings
```

The full suite builds separate test artifacts and uses Pillow, FFmpeg and
software GL. `clippy` needs that toolchain component. It does not record your
screen to replace manual COSMIC acceptance.

The suite builds the C reference from source and generates its manifest; no
historical binary recovery is required. New tests use neutral samples, not the
developer's local profiles. The application uses Rust; the C reference is a
development tool.

## 10. Reference files

When documentation differs, implementation and help define the current interface.
One machine/build's results are not promises of universal behavior.

- [Main CLI and menu](../scripts/compositor.py).
- [Schema, defaults, paths and TOML saving](../scripts/compositor_profile.py).
- [Device enumeration and microphone probing](../scripts/compositor_devices.py).
- [Sample profile](../examples/perfil.toml).
- [Technical CLI/scene overview](cli-escena.md).
- [GSR preparation script](../scripts/prepare-gsr.sh).
- [Plugin build script](../scripts/build-rust-overlay.sh).
- [Rust plugin suite](../scripts/check-rust-overlay.sh).
- [Profile and CLI tests](../tests/test_compositor.py).
- [Earlier CLI tests](../tests/test_element_cli.py).
- [GL and avatar tests](../tests/rust_gl_host.py).
- [GIF oracle](../tests/check_rust_gif.py).
- [Scene loading and limits](../rust/src/scene.rs).
- [Amplitude detector](../rust/src/microphone.rs).
- [FFI/OpenGL contract](../rust/SAFETY.md).
- [GSR pinned-source documentation](../third_party/gpu-screen-recorder/README.md).
- [GSR build options](../third_party/gpu-screen-recorder/meson_options.txt).
- [GSR argument manual](../third_party/gpu-screen-recorder/gpu-screen-recorder.1).
- [Status and validation scope](estado.md).
