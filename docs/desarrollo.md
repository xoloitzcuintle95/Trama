# Building and testing

Native GSR installation and Pop!_OS requirements are covered in the
[manual](guia-cli.md#2-installation-and-requirements). The [preliminary package](paquete-preliminar.md)
is built locally; installed-package validation is required before publication.

## Structure

| Directory | Purpose |
| --- | --- |
| `rust/` | Plugin, decoding, animation, ABI and rendering |
| `scripts/` | CLI/TUI, builds, checks and measurements |
| `tests/` | Tests and simulated adapters |
| `examples/` | Profile and neutral geometric assets |
| `assets/brand/` | Icon, mascot and hero supplied for Trama |
| `packaging/` | Application entry, notices and source rebuild script |
| `src/` | Development C reference for independent behavior comparisons |
| `third_party/gpu-screen-recorder/` | Separate, pinned official GSR checkout |
| `build/` | Generated artifacts, not source code |

The C reference is a testing tool, not the plugin used by the TUI. Keeping its
few dozen KiB of source enables independent tests. GSR's GUI is not required.

## Build

The build requires the expected GSR commit and local binary. Cargo dependencies
are pinned in the lockfile. Initial setup may require network access:

```bash
cargo fetch --manifest-path rust/Cargo.toml --locked
bash scripts/build-rust-overlay.sh
```

The script produces the plugin, validators and manifest in `build/`. Rust source
paths are remapped so the personal build directory is not embedded. Installed
GSR must match the recorded local binary. The engine is not installed or updated
automatically.

## Verify from source

```bash
bash scripts/check-rust-overlay.sh
python3 tests/test_trama.py
python3 tests/test_trama_pty.py
python3 scripts/check-source.py
```

The first command prepares the C reference and oracles, builds Rust, compares the
ABI and runs unit, GIF oracle, offscreen GL and CLI checks. The `test-hooks`
artifact is built separately and never replaces the production plugin. The suite
no longer relies on an old C binary from a particular machine: its manifest
records the binary and source hashes for this build.

TUI tests use a real pseudoterminal with a simulated capture process. The
30-second case waits that long and produces a synthetic MKV, not a desktop
capture. Examples do not read the developer's local profiles. Large budget-test
assets are generated inside each test's temporary directory.

Pillow and FFmpeg are required by the suite. To run Clippy:

```bash
CARGO_TARGET_DIR=build/rust-target cargo clippy --manifest-path rust/Cargo.toml \
  --offline --locked --all-targets --all-features -- -D warnings
```

To regenerate the geometric examples:

```bash
python3 scripts/create-example-assets.py
```

## Private and generated files

Keep personal profiles, graphics and videos outside the project. Absolute paths
and paths relative to a profile's own folder are supported. The TUI stores only
a pointer to the last profile in the user's XDG state directory.

`.gitignore` excludes builds, recordings, local profiles, caches, logs and
environment files. This helps keep them out of Git but does not replace a
pre-publication review. Official dependency licenses and notices are not the
developer's personal data and must be retained.

Unused `rust/target/` caches, build targets and logs may be removed. Running
without rebuilding needs at least `build/overlay-rust.so`,
`build/overlay-rust.build.json` and the release `scene-check`/`element-check`
validators. The suite regenerates test artifacts. Keep the local GSR build
required by the manifest.

A local copy may retain only GSR's executables after Meson/Ninja metadata was
removed. In that case run `bash scripts/prepare-gsr.sh` to configure and build
the engine again before trying `meson compile`.

## Local evaluation package

```bash
python3 scripts/build-deb.py
```

This creates a `.deb`, separate sources and hashes in `build/packages/`. It does
not install anything or copy files to `/usr`. An explicit module/artifact list is
used rather than packaging the whole working tree. It includes a private GSR
engine/helper and Cargo dependency notices. ELF dependencies are obtained through
`dpkg-shlibdeps`; system drivers and tools are not bundled.

The runtime preserves validator paths to reuse the existing loader. `Devices`
prioritizes the private engine only when `engine/` exists; source execution keeps
PATH lookup. The package also verifies the helper and validator. Installation
and KMS permissions are covered in the [package guide](paquete-preliminar.md#kms-helper-and-permissions).

## Test the installed version without personal profiles

After installing the package separately:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_installed.py
TRAMA_TEST_RUNTIME=/usr/lib/trama PYTHONDONTWRITEBYTECODE=1 python3 tests/test_trama_pty.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_package.py
```

`test_installed.py` checks that installed modules/binaries match the local `.deb`
and runs the installed launcher/loader/model with temporary HOME, XDG directories
and profiles. It tests formats, layers and errors without capturing devices.
Pillow is needed only to generate a test JPG, not to run Trama.

Only the adapter in `tests/` interprets `TRAMA_TEST_RUNTIME`: it tests the installed
TUI in a pseudoterminal with simulated display, microphone and recorder. The
production command has no equivalent engine-override option. Tests include first
run without arguments or prior state, saving, and a 30-second synthetic MKV.
They do not validate KMS capture, physical audio or actual microphone response.
All settings are stored in temporary directories.

These tests do not install, update or grant capabilities and need no sudo.
Comparison against the local `.deb` can fail when a different build is installed;
that identifies a version mismatch and does not authorize reinstalling it.
