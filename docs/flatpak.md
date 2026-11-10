# Experimental Flatpak

App ID: `io.github.xoloitzcuintle95.Trama`, branch `experimental`, x86_64.
Target: Wayland, GPU H.264, SDR and MKV. No GSR GUI, X11 permission, streaming
or network permission. Public distribution is Flatpak-only; the native `.deb`
recipe remains for development. The Rust compositor and TOML schema are unchanged.
The public [0.1.0-alpha1 prerelease](https://github.com/xoloitzcuintle95/Trama/releases/tag/v0.1.0-alpha1)
has user-confirmed recording on Pop!_OS/COSMIC; other systems remain unvalidated.

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
capture/encoder code. The revised recipe builds upstream static FFmpeg with its NVENC runtime API
negotiation patch. That revision has not yet been built or capture-tested; the
previous user-tested bundle still links runtime FFmpeg. No NVIDIA compatibility
claim is made from recipe checks alone.

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
The second physical PC runs Linux Mint/XFCE on X11. With a temporary
`--socket=x11` launch permission, the user confirmed that the TUI opens. GSR
enumerated the selected monitor and loaded/unloaded the Rust plugin, but capture
failed during encoder initialization: runtime FFmpeg required NVENC API 13.1,
while the NVIDIA driver exposed 13.0. No successful X11 capture is claimed.

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

## NVIDIA compatibility investigation (2026-11-09)

The Mint log reports `Driver does not support the required nvenc API version.
Required: 13.1 Found: 13.0`, followed by failure to open the video codec. The
invalid MKV/ffprobe error is a consequence of encoder initialization failing,
not evidence of a separate container bug. The test had no layers or microphone.
The GPU model and exact driver version were not collected.

The previously tested recipe used `-Dffmpeg_static=false`, linking the runtime's FFmpeg. The
[upstream Flatpak recipe](https://github.com/flathub/com.dec05eba.gpu_screen_recorder/blob/master/com.dec05eba.gpu_screen_recorder.yml)
instead uses `-Dffmpeg_static=true` and supplies pinned FFmpeg 9.0 sources and
`nv-codec-headers` n13.0.19.0. The pinned GSR source's
`subprojects/nv-codec-headers.wrap`, `subprojects/packagefiles/ffmpeg/meson.build`
and `extra/build_ffmpeg.sh` confirm that it builds those headers before FFmpeg.
The FFmpeg wrap also applies `ffmpeg-nvenc-runtime-api-version.patch`: inspection
confirms runtime API negotiation tables. Earlier investigation missed that patch;
headers alone do not describe the complete upstream compatibility mechanism.

Implemented in the recipe, pending a real build: use GSR's existing static FFmpeg build with
the upstream-pinned source inputs, preserving our authorization launcher and
disabled portal/app-audio options. Audit the resulting dependency notices,
corresponding sources, binary size and encoder linkage. Compiling only GSR
against older headers would not change runtime libavcodec's NVENC requirement;
lowering a reported version without a compatible build is not a solution.

This should address the observed API-version mismatch, but requires a rebuilt
package and real NVIDIA retest before claiming compatibility. Intel/Wayland
recording must also be checked for regression. X11 remains unvalidated and is
not enabled by default. No driver update is requested, and the existing
test bundle remains unchanged; rebuild from a fresh snapshot to use this recipe.


## Broader compatibility recipe (not yet capture-validated)

The next snapshot uses the pinned GSR static FFmpeg build and its original
patches, with all seven source archives explicitly hash-pinned in the manifest.
The installer rejects a GSR binary that still depends on runtime libavcodec,
libavformat, libavfilter, libavutil or libswresample. The build manifest records
the FFmpeg/header choice. Runtime ffprobe remains the file-inspection tool.

The recipe also includes the upstream-selected maintained i965 VAAPI driver for
older Intel hardware and the x86_64 VAAPI search paths from upstream. Modern
Intel/AMD/NVIDIA graphics integration still depends on the Flatpak runtime and
host drivers. Bundling i965 does not add hardware encoder capabilities to a GPU.
No X11 permission or new capture mode is enabled by this change.

Prepare a new snapshot (do not rebuild v3 expecting these changes):

```bash
python3 scripts/prepare-flatpak.py --output build/flatpak-input-v4
flatpak-builder --arch=x86_64 --state-dir=build/flatpak-state --force-clean --repo=build/flatpak-repo build/flatpak-app build/flatpak-input-v4/io.github.xoloitzcuintle95.Trama.json
```

If v4 already exists, choose a fresh output suffix and use it in both commands.
The static build may increase build time and package size; neither the final
size nor NVIDIA success is known before building/testing. Keep corresponding
sources for all dependencies and review their licenses before public release.
See [compatibility and issue reporting](compatibility.md).


Local validation of this revision: eight recipe tests pass, including source
hash/URL agreement with the pinned upstream wraps and the v4 snapshot matching
the current manifest. Manifest parsing and `git diff --check` pass. The attempted
build stopped during source download because this environment could not resolve
`gitlab.freedesktop.org`; compilation and the linkage guard have not run yet.

## Release-candidate assembly

The revised static-FFmpeg Flatpak was built by the user and the user confirmed
recording on the Intel/COSMIC/Wayland laptop. NVIDIA/X11 recording remains
unverified. The local release assembler adds metadata and dependency notices
without rebuilding the tested engine/helper/plugin/checker, and checks their
hashes before and after staging. It removes libdrm build-only headers/archives.

```bash
python3 scripts/release-flatpak.py
```

The default input is `build/flatpak-app-v4` with its matching v4 source snapshot.
Output is `build/releases/0.1.0-alpha1/`; an existing output is never overwritten.
Use `--build`, `--snapshot` and `--output` for other explicit locations. No sudo,
installation, capability grants or publication are performed. Icon export
validation runs without a sandbox because this environment cannot run bwrap;
the locally generated icon and metadata have separate validation checks.

Files to retain together:

- `trama-0.1.0-alpha1-x86_64.flatpak`: local binary candidate.
- `trama-0.1.0-alpha1-x86_64-sources.tar.xz`: matching Trama/Cargo snapshot,
  verified module archives, offline source recipe, patches and rebuild instructions.
- `RELEASE-INFO.json`: source inventory, build hashes/commits and publication blockers.
- `trama-0.1.0-alpha1-x86_64.sha256`: checksums for all three files.

```bash
cd build/releases/0.1.0-alpha1
sha256sum -c trama-0.1.0-alpha1-x86_64.sha256
```

The metadata describes `0.1.0-alpha1` as a development release. Code and art remain
GPL-3.0-only; the new AppStream metadata document alone uses CC0-1.0. The real
homepage/source browser is https://github.com/xoloitzcuintle95/Trama and issues
use that repository's issue tracker. The assembler records the public-URL blocker
only when one of the homepage/source-browser/bugtracker URL types is missing.
This is not a Flathub submission. Rust notices, FFmpeg and its codec/network
dependencies, libdrm, i965 and applicable SDK notices remain in the inventory.

The exact SDK/glibc collection and helper rebuild evidence have now been
verified; pass both options documented below to include them. Independent host
helper checks and user capture/stop/cancel validation are recorded in
[the current checkpoint](handoff.md), not certified automatically by the
assembler. Its remaining host-validation checklist must be reconciled with that
evidence before publication. No source archive/checksum proves legal compliance.
The assembler does not change the installed application or earlier bundles;
never upload an older candidate by mistake.

The current URL-complete candidate is
`build/releases/0.1.0-alpha1-github/`. It preserves all four tested runtime binary
hashes, includes the verified helper sources/rebuild report, passes artifact
checksums and has valid AppStream metadata. The user installed this exact bundle
and confirmed its recording smoke test works; OMP rechecked the deployed commit,
helper hash/permissions/capabilities and absence of remaining KMS processes.
The assembler's host/capture reminder is reconciled with that separate evidence
in the checkpoint, not removed by editing checksummed artifacts.
Source publication to the GitHub repository does not upload any Flatpak release
asset; the four release files must be attached separately.
The user has published those four files in the prerelease linked above. Their
GitHub API SHA-256 digests match the reviewed local candidate, and the public
checksum manifest was downloaded and matched. GitHub's automatically generated
source ZIP/tar is not a substitute for the companion dependency/SDK source archive.

## Collect the static helper's SDK sources

The SDK source manifest identifies glibc by a Git-describe ref ending in an exact
40-character commit. The SDK's signed OSTree commit subject identifies its
BuildStream source revision. The collector checks the actual build SDK commit,
fetches those source revisions (not `master`), and verifies that the SDK tree's
glibc recipe/ref and patch agree with the installed manifest.

From the project root, without sudo:

```bash
python3 scripts/prepare-helper-sources.py
```

This downloads source repositories into `build/helper-source-cache/` and writes
verified archives/records to `build/helper-sources/`. It installs nothing and
never runs the KMS helper. It refuses an existing output or a different SDK.
If the server does not permit fetching the recorded commit, preserve the error;
do not substitute the latest branch or silently use a different libc version.

The user downloaded both exact source revisions. The initial verifier incorrectly
looked for the glibc ref in the main element; the real SDK includes it from
`elements/bootstrap/include/glibc-source.yml`. This was corrected against the
actual downloaded tree. Cached exact commits are now reused without fetching,
and lower-cost source compression avoids repeating unnecessary work. Seven tests
cover matching, rejection and a real-cache/include regression check. The source
collection is now verified; helper recompilation remains pending. The original
candidate stays unchanged; a separate candidate includes the helper sources.

After collection, create a new candidate including those sources:

```bash
python3 scripts/release-flatpak.py \
  --helper-sources build/helper-sources \
  --output build/releases/0.1.0-alpha1-with-helper-sources
```

The assembler revalidates the collection against the recorded SDK before adding
it. It will still report a helper-rebuild check pending. Extract that candidate's
source archive to a new owned directory and follow its REBUILD.md; the script
runs inside `flatpak build --readonly`, builds libdrm/helper and writes a static
linkage/rebuild report, without installing or executing the helper.

For a final assembly after that check, pass the matching report as
`--helper-rebuild /path/to/helper-rebuild/HELPER-REBUILD.json`, alongside
`--helper-sources` and a new `--output`. The assembler checks the report, binary
hash, SDK manifest and source archive hashes. The real public URLs and host/helper
lifecycle checks are independent release items. Inside this agent environment,
even `flatpak build ... true` fails to allocate an instance; this is not evidence
of a failure on the user's installed runtime.


The prepared source-only input for the laptop rebuild is `build/helper-rebuild-input`.
It contains the original candidate's GSR/libdrm archives, manifest and provenance.
From the checkout, the next check (no sudo, no install) is:

```bash
flatpak build --readonly --unshare=network --filesystem="$PWD" build/flatpak-app-v4 \
  python3 "$PWD/packaging/flatpak/rebuild-helper.py" \
  "$PWD/build/helper-rebuild-input" --output "$PWD/build/helper-rebuild-check"
```

Run from the project root. This writes only a new build output, never executes
the rebuilt helper, and should finish with both helper hashes and a no-install
message. Its report can be passed to the release assembler as described above.
