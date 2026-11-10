# Development and testing

This guide is for contributors working from a source checkout. For the public
Linux x86_64 prerelease, use the [Flatpak guide](flatpak.md). Native scripts and
local packaging tools are not an alternative public installation procedure.
See [architecture](cli-escena.md) for component boundaries and resource limits,
and [measurements](mediciones.md) for benchmark methodology.

## Source layout

| Path | Purpose |
| --- | --- |
| `scripts/compositor.py`, `compositor_profile.py`, `compositor_devices.py` | Shared recorder, TOML profiles and device discovery |
| `scripts/trama_*.py` | Curses interface, model, view and translations |
| `rust/src/` | Plugin ABI, bounded media loading, animation, microphone detector and GL rendering |
| `src/` | Independent C reference for comparison tests; not the production plugin |
| `tests/` | Unit tests, Pillow oracles, offscreen GL hosts and simulated recorder adapters |
| `examples/` | Neutral profiles and geometric media |
| `packaging/` | Launchers, licenses, Flatpak recipe and rebuild tooling |
| `third_party/gpu-screen-recorder/` | Separate upstream GSR checkout |
| `build/` | Generated binaries, manifests, packages and measurement output |

## Native prerequisites

Run commands below from the repository root on Linux. Required tools are Bash,
Git, Python 3.11 or newer, current stable Rust/Cargo (edition 2024), a C compiler,
`pkg-config`, Meson and Ninja. Fetching sources/crates initially needs network
access; the plugin build itself uses Cargo's `--offline --locked` mode.

The native GSR configuration needs development libraries for FFmpeg
(`libavcodec`, `libavformat`, `libavutil`, `libswresample`, `libavfilter`), X11
(`x11`, `xcomposite`, `xrandr`, `xfixes`, `xdamage`), PulseAudio, VA-API
(`libva`, `libva-drm`), DRM, Wayland (`wayland-egl`, `wayland-client`), D-Bus
and libcap, plus the Wayland protocol generation tools. The C reference also
needs `libswscale` and OpenGL development files. Distribution package names vary;
the authoritative dependency list is the upstream `meson.build`.

Tests additionally need Python Pillow, FFmpeg/FFprobe, and Mesa EGL/OpenGL with
surfaceless software rendering (`libEGL.so.1`, `libGL.so.1`, GLES 3). Pillow is a
test/asset-generation dependency, not a Trama runtime dependency. Actual desktop
capture additionally needs compatible graphics drivers, a graphical session,
working KMS authorization and PulseAudio or PipeWire's PulseAudio compatibility
service; microphone detection uses `parec` from `pulseaudio-utils`.

## Pin and build the native engine

The plugin baseline is GSR **6.1.7**, commit
`f97d1e392816503282d20a0804c3ce3fd2943767`, plugin header API **0.1**. For a fresh
checkout without `third_party/gpu-screen-recorder/`:

```bash
git clone https://repo.dec05eba.com/gpu-screen-recorder third_party/gpu-screen-recorder
git -C third_party/gpu-screen-recorder checkout --detach f97d1e392816503282d20a0804c3ce3fd2943767
bash scripts/prepare-gsr.sh
```

With an existing upstream checkout, inspect/preserve local changes before
selecting the required commit. `prepare-gsr.sh` configures and builds locally;
it does **not** select the pinned commit or install the engine. Its configuration
uses system FFmpeg and disables portal capture, application audio, plugin
examples, systemd integration and the NVIDIA suspend fix. It is not the
production Flatpak engine recipe. For an already configured build use:

```bash
meson compile -C third_party/gpu-screen-recorder/build
```

Do not run upstream installation scripts merely to build or test the plugin.
KMS helper installation and authorization are separate privileged operations;
review the [security guide](security-kms.md) before changing a native setup.
Normal Trama execution must not run with sudo.

## Build the Rust plugin

```bash
cargo fetch --manifest-path rust/Cargo.toml --locked
bash scripts/build-rust-overlay.sh
```

The script requires the pinned upstream Git commit and unchanged plugin header,
plugin loader and recorder files. It compares C/Rust ABI sizes, alignments,
offsets and constants for the current target. It produces:

- `build/overlay-rust.so`: Rust crate **0.4.0**, plugin version **4**.
- `build/rust-target/release/scene-check` and `element-check`: validators using
  the production loaders without a recording or GL context.
- `build/overlay-rust.build.json`: GSR commit and SHA-256 hashes of the locally
  built engine, plugin, header and `rust/Cargo.lock`, with `test_hooks: false`.

Rust build paths are remapped to avoid embedding the contributor's home/checkout
path. Keep the manifest and its matching artifacts together. A version string
alone does not establish ABI or binary compatibility. Runtime checks reject a
changed engine/plugin; packaged builds also bind their helper and scene checker.
Changing engine, ABI or dependency pins requires an intentional rebuild and
review, not editing a manifest to bypass a mismatch.

For native scene CLI/TUI development, the engine is discovered through PATH
unless a packaged private engine is present. For example:

```bash
PATH="$PWD/third_party/gpu-screen-recorder/build:$PATH" \
  python3 scripts/compositor.py --help
PATH="$PWD/third_party/gpu-screen-recorder/build:$PATH" \
  python3 scripts/trama_tui.py scene.toml
```

Device queries/capture still require the appropriate runtime setup. The advanced
single-element and measurement tools below instead require the matching native
engine specifically at `/usr/local/bin/gpu-screen-recorder`; they do not select
the installed Flatpak engine or provide an engine override.

## Test entry points

```bash
bash scripts/check-rust-overlay.sh
python3 tests/test_trama.py
python3 tests/test_trama_view.py
python3 tests/test_trama_i18n.py
python3 tests/test_trama_pty.py
python3 tests/test_measure.py
```

`check-rust-overlay.sh` builds/tests the C reference, builds Rust, checks ABI,
runs Cargo release tests, offscreen GL tests, GIF oracles, element CLI and scene
CLI tests, then `scripts/check-source.py`. It builds fault-injection
`test-hooks` in `build/rust-test-target/`, never over the production plugin.
Element/scene CLI tests require the matching native GSR installation described
above, even for asset-only checks. Offscreen tests use software rendering, not
KMS or a hardware encoder. PTY tests simulate devices and recording; their timed
capture produces synthetic media, not a desktop recording. These checks do not
establish hardware compatibility or recording performance.

Run the source hygiene check from a clean development tree. It flags root-level
`*.toml` profiles and `gifs/` even when Git ignores them. Use a separate clean
checkout for publication checks rather than deleting personal files to satisfy
the checker; keep private media and working profiles outside that checkout.

Optional static analysis and asset regeneration:

```bash
CARGO_TARGET_DIR=build/rust-target cargo clippy --manifest-path rust/Cargo.toml \
  --offline --locked --all-targets --all-features -- -D warnings
python3 scripts/create-example-assets.py
```

## Advanced single-element tool

`scripts/record-element.py` exercises initial geometry/visibility without scene
profiles or microphone/avatar behavior. It supports static PNG/JPG and animated
GIF, not APNG or text. With the production plugin and matching native engine:

```bash
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --x 100 --y 80 --width 300 --height 200 --check
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --x 100 --y 80 --width 300 --height 200 --audio --seconds 30
```

`--check` validates with Rust and prints effective geometry without capture,
GL or audio-device access; it still checks the engine/plugin fingerprint.
Recording captures the full monitor via KMS at 30 FPS CFR, H.264 GPU,
`very_high`, no CPU fallback, and MKV. `--audio` adds system audio, not a
microphone. `--seconds` is total capture duration, **10..7200 seconds**, including
5 seconds of measurement warm-up. Output is created in a unique
`build/recordings-element/<UTC-id>/` directory with video, logs and metrics.
Ctrl+C requests shutdown/finalization and preserves collected output.

Geometry is measured in recorded-canvas pixels from the upper-left corner.
X/Y default to 32/32 and accept integers **−16384..16384**. Explicit dimensions
accept integers **1..16384**; derived dimensions must be positive and at most
16384 and can be fractional. Negative positions are clipped by GL.

| Dimensions | Result |
| --- | --- |
| Neither | Width 320; height follows source aspect ratio |
| Width only / height only | Other dimension follows source aspect ratio |
| Both | Largest proportional image fitting the box |
| Both plus `--stretch` | Exact dimensions, allowing distortion |

The fitted rectangle stays top-left aligned at X/Y; it is not centered, cropped
or enlarged to fill the box. `--hidden` retains and validates the source/cache
and GL resources but skips drawing, texture updates and its own damage requests.
It does not remove pipeline costs or release the asset. Use `--visible` for a
subsequent visible capture. No option changes a running capture.

### Development-only environment configuration

Direct plugin initialization can use these variables instead of a scene
manifest. They are read once during init, not watched:

| Variable | Contract |
| --- | --- |
| `GSR_RUST_IMAGE` | Required PNG/JPG/GIF path in single-element mode |
| `GSR_OVERLAY_X`, `GSR_OVERLAY_Y` | Signed canvas pixels; default 32, bounds as above |
| `GSR_OVERLAY_WIDTH`, `GSR_OVERLAY_HEIGHT` | Optional dimensions in pixels; bounds/fit as above |
| `GSR_OVERLAY_KEEP_ASPECT` | Default `true`; `false` requires both explicit dimensions |
| `GSR_OVERLAY_VISIBLE` | Default `true`; hidden assets must still be valid |

Booleans are exactly `true` or `false`; invalid values fail initialization.
Single-element CLI flags override only their corresponding inherited variables;
`--keep-aspect` and `--visible` can override exported `false`. An inherited width
plus CLI height forms a box; unset width to request height-only sizing. Reports
include inherited settings and Rust-resolved geometry.

`GSR_RUST_SCENE` selects the internal JSON manifest instead of single-element
mode. The production scene recorder clears inherited `GSR_RUST_*` and
`GSR_OVERLAY_*` variables and supplies its own private temporary manifest; these
variables are not production Flatpak configuration knobs. `GSR_RUST_TEST_PANIC`
and deterministic-clock exports exist only with `test-hooks`, not in production.
The C comparison reference does not support negative X/Y, height, stretching or
hidden state; comparison tools reject unequal layouts.

## Flatpak sources and offline rebuilding

The production application ID is `io.github.xoloitzcuintle95.Trama`, branch
`experimental`, architecture `x86_64`. Its recipe pins GSR 6.1.7 and static
FFmpeg 9.0, includes the NVENC negotiation patch, and builds the static KMS helper
and Rust plugin. Do not treat a native system-FFmpeg build as the same artifact.
The system-wide Flatpak/helper setup is described in the [Flatpak guide](flatpak.md).

For a checkout-based build, install Flatpak, flatpak-builder, the Freedesktop
26.08 SDK/runtime and its Rust extension; stage locked Cargo sources first:

```bash
python3 scripts/prepare-flatpak.py --output build/flatpak-input
flatpak-builder --arch=x86_64 --force-clean --repo=build/flatpak-repo \
  build/flatpak-app build/flatpak-input/io.github.xoloitzcuintle95.Trama.json
```

Preparation needs the locked crates already cached. The generated online recipe
can download its other pinned inputs. Use a new preparation output directory for
a subsequent staging operation. Building does not install or authorize the helper.

For the matching source archive accompanying a release, follow
[the offline rebuild instructions](../packaging/flatpak/REBUILD.md) **from the
extracted archive**, using its offline manifest, vendored crates, module sources,
notices and `BUILD-INFO.json`. The SDK/runtime must already be installed; source
offline rebuilding does not promise bit-identical binaries. Preserve SDK commits,
patches, provenance, license notices and helper relinking instructions.

Packaging-tool tests do not capture the desktop or install packages:

```bash
python3 tests/test_flatpak.py
python3 tests/test_flatpak_release.py
python3 tests/test_helper_sources.py
```

### Optional Debian development package

On an amd64 Debian-family development environment with `dpkg-deb` and
`dpkg-shlibdeps`, `python3 scripts/build-deb.py` creates a local `.deb`, matching
sources and hashes under `build/packages/`. It requires the pinned native engine
checkout, production plugin and matching manifest; it is not the public release
installation recommendation. It does not install, run setcap or copy to `/usr`.
`python3 tests/test_package.py` inspects/extracts that local package without
installing it. System drivers are not bundled.

If deliberately testing an already installed development package,
`python3 tests/test_installed.py` compares it with the matching local `.deb`.
`TRAMA_TEST_RUNTIME=/usr/lib/trama python3 tests/test_trama_pty.py` selects its
modules **only through the test adapter** with temporary HOME/XDG settings and
simulated devices. It is not a production override or a KMS/audio validation.
A package mismatch is not authorization to replace an installation.

## Media, privacy and licensing

Keep personal profiles, graphics and recordings outside the checkout. Paths in
profiles may be absolute or relative to the profile's directory; the TUI stores
a last-profile pointer in XDG state. Use synthetic geometric assets, temporary
HOME/XDG directories and neutral filenames in tests and bug reports. Do not
capture a private desktop merely to test the model or renderer.

Generated recordings, logs, measurement JSON and compiler/linker output may
contain device names, usernames, paths, audio or screen content. Review and
redact deliberately before sharing; `.gitignore` is not a privacy boundary.
Do not inspect, copy or publish another person's media or delete their caches.
Build artifacts are reproducible outputs, not source; retain matching engine,
plugin, validators and manifest when running without rebuilding.

Trama's crate is GPL-3.0-only; retain the repository license and dependency
notices, including upstream GSR and bundled/static-library obligations. Source
availability, license review, successful builds and hardware capture validation
are separate requirements.
