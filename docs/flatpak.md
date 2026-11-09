# Experimental local Flatpak

Local ID: `io.github.xoloitzcuintle95.Trama`, branch `experimental`, x86_64.
Target: Wayland, GPU H.264, SDR and MKV. No GSR GUI, X11 permission, streaming
or network permission. The native `.deb`, Rust compositor and TOML schema are
unchanged. This is a local test build, not a public release. User-confirmed recording
works on the Pop!_OS/COSMIC laptop; other systems remain unvalidated.

## Current authorization design

Read the [authorization review](security-kms.md) before installing/testing.
The initial upstream cached capability-bearing proxy has been replaced with
[an unprivileged shell launcher](../packaging/flatpak/launch-kms.sh). GSR still
uses `flatpak-spawn --host` to call `kms-server-proxy`, but that name now points
to the launcher. It executes the fixed system-installed KMS helper through the
host's `/usr/bin/pkexec`, with socket and DRM card as separate quoted arguments.
It does not create privileged copies, set capabilities or expose upstream's
setup/hotkey commands. Polkit decides whether authentication is required; do not
promise a fresh password prompt every time, since host policy may cache approval.

System installation is required: the fixed helper resides under
`/var/lib/flatpak/app/<ID>/current/active/files/bin/gsr-kms-server`. A user-only
installation or builder run does not test this host path. Trama itself never runs
as root. The helper still runs privileged for the capture session.

GSR source remains pinned to `f97d1e392816503282d20a0804c3ce3fd2943767`.
The packaging adaptation replaces its upstream Flatpak app ID and fails when
the expected identifier disappears. It never changes the original checkout or
capture/encoder code. The engine links runtime FFmpeg; compatibility with older
NVIDIA drivers needing upstream FFmpeg patches is not claimed.

## Permissions and existing profiles

- `--device=all`: broad device access retained from the upstream approach;
  narrowing it requires physical capture tests.
- `--filesystem=host`: supports existing graphics/output paths and GSR's home
  socket. This is broad access, not strong file isolation.
- `--socket=pulseaudio`: system/microphone audio and the existing avatar detector.
- `--socket=wayland`, `--share=ipc`: graphics/session integration.
- `--talk-name=org.freedesktop.Flatpak`: host execution for the launcher; this
  weakens sandbox isolation and requires review before a Flathub submission.

Flatpak redirects XDG settings/state into `~/.var/app/<ID>/`. Open an existing
TOML explicitly to reuse it; no native settings or personal files are migrated or
deleted. Host access does not make reserved `/app` or `/usr` paths arbitrary
host-file access locations. Copy samples to a writable folder before use.

## Prepare and build

Host requirements: Flatpak, flatpak-builder, Cargo and the locked crate cache.
A fresh development machine can populate that cache with
`cargo fetch --locked --manifest-path rust/Cargo.toml`.

Install user-scoped SDK dependencies manually if absent (no sudo):

```bash
flatpak install --user flathub org.freedesktop.Sdk//26.08 org.freedesktop.Platform//26.08 org.freedesktop.Sdk.Extension.rust-stable//26.08
```

Zig and the upstream proxy sources are no longer needed. Prepare from the project
root; the script refuses to overwrite an existing snapshot:

```bash
python3 scripts/prepare-flatpak.py --output build/flatpak-input-new
flatpak-builder --show-manifest build/flatpak-input-new/io.github.xoloitzcuintle95.Trama.json
flatpak-builder --arch=x86_64 --state-dir=build/flatpak-state --force-clean --repo=build/flatpak-repo build/flatpak-app build/flatpak-input-new/io.github.xoloitzcuintle95.Trama.json
```

Only allowlisted project files and locked vendored crates enter the snapshot.
Compilation uses offline Cargo; source downloads need network access. Archives
are hash-pinned and libdrm uses a fixed commit. Static helper compilation includes
upstream's `-fno-link-libatomic` option for SDK 26.08. The installer generates a
512x512 icon derivative while preserving original artwork. ELF postprocessing is
disabled to retain the engine/helper/plugin/checker hashes used for verification.
The build checks TUI help and neutral example assets, not GPU capture.

## Install/update and test

Only after a successful build, install/update the system app explicitly:

```bash
sudo flatpak install --system --reinstall ./build/flatpak-repo io.github.xoloitzcuintle95.Trama//experimental
```

The command requires authorization; it was not run by the agent. Existing profiles
are outside the app deployment and should remain intact. From a Wayland terminal,
without sudo:

```bash
flatpak run io.github.xoloitzcuintle95.Trama
flatpak run io.github.xoloitzcuintle95.Trama "$HOME/path/to/perfil.toml"
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama /app/lib/trama/scripts/compositor.py check "$HOME/path/to/perfil.toml"
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama /app/lib/trama/scripts/compositor.py record "$HOME/path/to/perfil.toml" --seconds 30
```

Use `t` for a TUI test, `x`/Ctrl+C to stop. Accepting Polkit authorizes the KMS
helper for that session, not a persistent capability-bearing proxy. Check visible
motion, transparency, idle/talking, microphone/system audio, synchronization,
finalized MKV, return to TUI and terminal restoration. Test authorization denial
as well. Desktop-menu terminal launch still needs validation on COSMIC.

## Evidence and pending work

The user built, installed and configured the revised Flatpak, then confirmed real
recording on the Pop!_OS/COSMIC laptop. Denying authorization recovers correctly;
stopping with `x` finalizes the MKV and returns to the TUI. These are user-observed
results, not agent-executed capture tests.

Seven local recipe tests pass: fixed target, literal argument forwarding, invalid
input rejection, icon dimensions, source adaptation and an offline Cargo snapshot.
Manifest parsing also passes. No privileged commands were executed by the agent.
Host ownership/capability verification and helper-process cleanup remain pending.
Testing on the other physical PC is in progress; no result is claimed yet.

Before distribution: complete authorization/capture/stop tests; review broad
permissions and desktop launch; audit transitive licenses/notices; provide
corresponding sources, build instructions and hashes; add AppStream metadata
with actual public URLs; review Flathub policy. No standalone bundle is released.

## References

- [Manifest](../packaging/flatpak/io.github.xoloitzcuintle95.Trama.json)
- [Source preparation](../scripts/prepare-flatpak.py)
- [Tests](../tests/test_flatpak.py)
- [Upstream reference](https://github.com/flathub/com.dec05eba.gpu_screen_recorder/blob/master/com.dec05eba.gpu_screen_recorder.yml)
- [Flatpak build reference](https://docs.flatpak.org/en/latest/flatpak-builder-command-reference.html)

## User-confirmed laptop capture

The user confirmed real recording with the revised per-session Polkit launcher
on Pop!_OS/COSMIC. Denying authorization recovers correctly; stopping with `x`
finalizes the MKV and returns to the TUI. These are user-observed results, not
agent-executed hardware tests. Other distributions, GPUs and helper-process
cleanup have not yet been verified. A local test bundle was generated in
`build/packages/trama-flatpak-test-x86_64.flatpak` with a companion SHA-256 file.
It is for private second-machine testing, not a published release; the complete
release sources/notices and remaining distribution checks are still pending.
