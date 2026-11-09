# Trama publication checklist

Goal: publish an early beta with verified installation/core workflow, explicit
limits and no personal data. This does not require certifying every distribution
or adding features, and is not publication authorization.

`[x]` means existing evidence; `[ ]` means pending. Record failures/not-applicable
with a reason. A simulation is not proof of real capture.

## 1. Verified foundation

- [x] User confirms a usable, well-presented TUI in Pop!_OS/COSMIC.
- [x] Real 10-minute recording confirmed; earlier smoothness/audio checks confirmed.
- [x] User installed the `.deb` and successfully recorded with it.
- [x] Installed runtime, fresh-state startup and errors tested with temporary profiles.
- [x] PTY checks cover a simulated 30-second capture, stopping and terminal restoration.
- [x] Package reviewed: private engine/helper, no GSR GUI or personal profiles/videos.
- [x] Code/artwork GPL-3.0-only; notices and sources accompany the package.
- [x] Initial Trama commit reviewed: alias and noreply email in author/committer fields.

The earlier clean first-run test uses simulated devices; a fresh physical
installation remains to be checked. Current version is still `0.1.0~alpha1`.

## Flatpak evidence and release work

- [x] Built/exported and installed the local x86_64 Flatpak.
- [x] User confirmed configuration and real recording on Pop!_OS/COSMIC.
- [x] User confirmed recovery after denying Polkit authorization.
- [x] User confirmed `x` stops, saves the MKV and returns to the TUI.
- [x] Replaced the persistent privileged proxy with per-session Polkit authorization.
- [x] Generated a private second-machine test bundle and its SHA-256 checksum.
- [ ] Verify host deployment ownership/capabilities and helper exit after stopping.
- [ ] Finish the second-PC test; record session, distro, GPU and actual results.
- [ ] Prepare complete corresponding release sources/notices for Flatpak dependencies.
- [ ] Add final AppStream metadata and review broad permissions before public distribution.

The private test bundle is not yet a public release. Installation must be system-wide
for the current fixed helper path. See the [Flatpak guide](flatpak.md).

## 2. Choose the second environment

| Test | Physical Mint PC | Ubuntu 24.04 VM |
| --- | --- | --- |
| Dependencies/installation without development tools | Yes | Yes |
| First run, languages, profiles and legibility | Yes | Yes |
| Device discovery/errors | Yes | Partial, depending on exposed VM devices |
| Capture, GPU encoding and physical audio | Priority test | Does not certify the host's physical hardware |
| Recording workload performance | Yes, with workload recorded | Not a valid comparison of the physical host |

**Proposed order:** physical Mint first; a VM complements clean-install testing.
If Mint uses X11, record that as exploratory: Wayland remains the target. Do not
change sessions/install another desktop merely to check a box. Failure outside
the target does not require broader support before a Pop!_OS/COSMIC-limited beta.

### Machine inventory without sudo

From a graphical-session terminal:

```bash
cat /etc/os-release
printf 'Sesión: %s\n' "$XDG_SESSION_TYPE"
printf 'Escritorio: %s\n' "$XDG_CURRENT_DESKTOP"
uname -m
lspci -nn | rg -i 'vga|3d|display'
```

Without `rg`, run `lspci` and locate GPU lines. Do not paste usernames, personal
paths, serial numbers or full audio listings into public issues. Distro/version,
session and GPU model are sufficient for the report.

- [ ] Record Mint/Ubuntu version, desktop and actual session type.
- [ ] Record GPU and physical-machine versus VM environment.
- [ ] Confirm `x86_64` architecture for the `amd64` package.

## 3. Clean installation before labeling the package beta

Use a fresh user or machine/VM without compilers or GSR installed to expose
accidental dependencies on the development machine. Do not delete existing
profiles to simulate a new user.

- [ ] Copy `.deb`, source archive and `.sha256` from the same build.
- [ ] Verify hashes; retain the result and package version.
- [ ] Inspect APT simulation before installing.
- [ ] Install only the package and declared dependencies, without compiling.
- [ ] `trama --help` works outside the project directory.
- [ ] `trama` starts without sudo or another GSR in PATH.
- [ ] Application-menu entry opens a usable terminal with the icon.
- [ ] Record KMS authorization: Polkit or manually granted capability.
- [ ] If testing `setcap`, apply only to the private helper and record the result.

From the folder containing all three files:

```bash
sha256sum -c trama_0.1.0~alpha1_amd64.sha256
dpkg-deb --field trama_0.1.0~alpha1_amd64.deb Version Architecture Depends
apt-get --simulate install './trama_0.1.0~alpha1_amd64.deb'
```

Installation below **requires sudo**; these documents do not execute it:

```bash
sudo apt install './trama_0.1.0~alpha1_amd64.deb'
```

Do not force broken dependencies or replace system libraries to make the package
fit. It requires, among others, libc6 >= 2.39 and `libavcodec60`: using APT does
not establish binary compatibility. Ubuntu 24.04 provides those library families,
but compatibility remains unclaimed until tested.
[Ubuntu 24.04 libc6](https://packages.ubuntu.com/noble/libc6),
[Ubuntu 24.04 libavcodec60](https://packages.ubuntu.com/noble/libavcodec60).

Retain APT errors as packaging results. Successful installation without an
available H.264 GPU encoder is a hardware/driver/environment limitation; there
is no automatic CPU fallback. A VM's accelerated 3D desktop does not establish
GPU video encoding. This distinction follows the [actual recording command](../scripts/compositor.py),
which requires `-encoder gpu -fallback-cpu-encoding no`.

## 4. New-user workflow on a physical PC

- [ ] Without an existing profile, choose display/microphone by name; no developer data appears.
- [ ] Create/save a profile with personal assets or neutral samples.
- [ ] Reopen Trama: recover the profile and edit only the selected field.
- [ ] Test Spanish, English and automatic; help remains readable.
- [ ] Add PNG/JPG/GIF; hide, reorder and remove without deleting source files.
- [ ] Move the avatar between two corners and resize with aspect preservation.
- [ ] Record 30 seconds; open the MKV at the path shown by Trama.
- [ ] Check visible motion: no black background or frozen image.
- [ ] Check transparency, animation, position and idle/talking switching.
- [ ] Hear system sound/microphone as configured; check synchronization.
- [ ] Stop with `x` or Ctrl+C: finalized file, TUI return and usable terminal.
- [ ] Record again in the same session without overwriting previous output.

Installed samples are in `/usr/share/doc/trama/examples/`. To use them, **copy the
entire folder** to an owned, writable location first, retaining `assets/`. Do not
record into `/usr/share`. KMS permissions/diagnostic commands are in the
[package guide](paquete-preliminar.md).

## 5. Errors and coexistence

- [ ] Missing/invalid graphic: useful error, recording does not start.
- [ ] Disconnected explicit microphone: warning and replacement selection without hand-editing TOML.
- [ ] Unwritable folder: identifies the destination to fix, without running as sudo.
- [ ] Unsaved exit offers save, discard or keep editing.
- [ ] `{timestamp}` creates distinct MKV filenames.
- [ ] Package removal preserves user profiles, graphics and videos.
- [ ] Reinstall/update preserves settings; check helper capability if used.
- [ ] Existing GSR is neither replaced nor a version dependency of the package.

Do not intentionally fill disks or cut power for this first beta, or delete
personal configuration as a test step. Extreme failures can be tested later with
isolation and a concrete objective.

## 6. Stability and performance evidence to expand

- [ ] Run a normal session longer than the 10-minute reference; record actual duration.
- [ ] Review start/middle/end video and audio; include motion to detect freezes.
- [ ] Record whether memory/CPU stabilizes or grows, with resolution/FPS, audio, assets and workload.
- [ ] Compare equivalent GSR-only runs before attributing compositor cost.
- [ ] Compare OBS only if publishing resource-advantage claims.

There is no technical 60-minute minimum: longer sessions look for accumulation.
This can remain explicitly pending in an early beta; do not call it stable or
promise an OBS resource advantage without evidence. VM timings/resources are not
those of the physical laptop.

## 7. Publication cut

- [ ] Choose prerelease label/version; current artifact is `alpha1`, not `beta1`.
- [ ] Fix blockers in the primary workflow on the platform being advertised.
- [ ] Update compatibility with actual results and known failures.
- [ ] Review final documentation/code before the next commit.
- [ ] Recheck source privacy and author/committer metadata before uploading.
- [ ] Build final versioned package, corresponding sources, notices and hashes.
- [ ] Test **that same final package**; do not replace binaries after hashing.
- [ ] Create a remote/publish only with user authorization.
- [ ] Mark release preliminary and attach `.deb`, sources and hashes.
- [ ] Include installation, KMS helper, removal and bug-report instructions.

Trama's Git must not contain `build/`, GSR checkout, personal profiles, captures
or logs. Binaries/vendored sources belong in release artifacts, not source-code
history. Nothing is published as part of this checklist.

## 8. GitHub launch

- [ ] Choose repository name/description and confirm the public account.
- [ ] Review the files actually tracked by Git, including artwork and examples; exclude personal configuration and recordings.
- [ ] Confirm alias/noreply identity on every commit to be published.
- [ ] Publish the source repository and enable Issues with a short reproduction template.
- [ ] Create a GitHub prerelease using the exact tested artifacts from section 7.
- [ ] Make the README download instructions point to the actual release; remove the local-only availability note.
- [ ] Check README images, documentation links, source archive and downloads from a fresh browser/session.

## 9. User-facing website

The website is a separate task, to be built in Hermes. Keep GitHub as the source,
release and issue tracker; link both ways instead of maintaining duplicate binaries.

- [ ] Explain the product in plain language, with a real TUI screenshot or short demonstration.
- [ ] Show Linux-only scope, preliminary status and the exact tested systems.
- [ ] Link the current GitHub download, quick start, full guide and issue tracker.
- [ ] Explain installation and possible screen-capture authorization without promising universal compatibility.
- [ ] Check mobile layout, readable contrast, keyboard navigation and working links.
- [ ] Publish only after the GitHub release/download links work.

## 10. Reddit announcement

- [ ] Choose relevant communities and read each community's current posting/self-promotion rules before posting.
- [ ] Prepare a concise description, real screenshot and links to the website and source.
- [ ] Disclose that this is your project and an early release; state Linux/Wayland scope and tested hardware honestly.
- [ ] Describe existing capabilities only; make no unmeasured OBS performance or memory claims.
- [ ] Review screenshots and terminal output for personal paths, names, devices and private content.
- [ ] Post manually or with explicit authorization, then collect reproducible feedback in GitHub Issues.

## 11. Later: video

- [ ] After the initial launch, prepare a short installation-to-recording walkthrough.
- [ ] Use the published version and neutral demonstration assets; review screen/audio for private information.

The video is not a blocker for the initial publication. Suggested sequence:
finish package validation, publish GitHub prerelease, publish website, announce on
Reddit, then prepare the video. This checklist does not authorize any publication.

## Test record

Copy this template into a report without personal data. Check boxes only for
observed actions/results, not by deduction.

```text
Package and hash:
Distro / version:
Desktop / session (Wayland or X11):
Physical machine or VM / GPU:
Clean installation or development machine:
KMS authorization (Polkit or setcap):
Display / resolution / FPS (no private identifiers):
Audio (system, microphone, both or none):
Scene and formats used:
Actual duration:
Installation / first-run result:
Video / audio / avatar / stopping result:
Problem and reproduction steps:
Relevant message (no personal paths, names or email addresses):
```
