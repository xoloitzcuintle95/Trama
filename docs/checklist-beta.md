# Trama publication checklist

Distribution decision: Flatpak only for the public release. The `.deb` recipe
remains development-only. Broad compatibility is a goal, not a certified hardware
list; user reports will guide expansion.

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
- [x] Second-PC result: Mint/XFCE/X11 opens and loads the plugin; runtime NVENC 13.1 requirement rejects driver API 13.0. Capture failed; GPU model/driver version not collected.
- [x] Prepare module/Cargo source archive and dependency notices, with SDK provenance.
- [ ] Complete exact SDK glibc sources/patch and static-helper relinking review before publication.
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
- [ ] Confirm `x86_64` architecture for the Flatpak.

## 3. Clean Flatpak installation before release

A second physical capture setup is useful but is not a requirement for an
explicitly experimental release. Test the final build on the available target;
record other environments as unvalidated rather than inferring support.

- [x] User built the revised static FFmpeg/i965 recipe; ELF dependency inspection confirms no runtime FFmpeg linkage.
- [x] User confirmed the revised Flatpak works on the Intel/COSMIC/Wayland laptop; detailed final-candidate checks remain below.
- [ ] Measure final artifact size; retain corresponding sources and dependency notices.
- [ ] Copy the final `.flatpak` bundle and checksum to a clean environment when available.
- [ ] Verify the hash and install system-wide with the required runtime.
- [ ] Start outside the project directory without a separately installed GSR.
- [ ] Verify application-menu terminal launch, icon and first-run setup.
- [ ] Verify Polkit cancellation/retry, helper exit and removal preserving user data.
- [ ] Record NVIDIA retest when a machine is available; do not claim it passed now.

Installation/build commands and the system-install requirement are documented in
[the Flatpak guide](flatpak.md). The native APT recipe is retained separately in
[development-only packaging](paquete-preliminar.md).

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

Flatpak samples are in `/app/share/trama/examples/` inside the sandbox. To use them, **copy the
entire folder** to an owned, writable location first, retaining `assets/`. Do not record into `/app`. Authorization and copy commands are in the [Flatpak guide](flatpak.md).

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
- [x] Assemble a local versioned Flatpak candidate, module sources, notices and hashes.
- [ ] Close the SDK-source and metadata-URL blockers before calling it final.
- [ ] Test **that same final package**; do not replace binaries after hashing.
- [ ] Create a remote/publish only with user authorization.
- [ ] Mark release preliminary and attach the `.flatpak`, corresponding sources and hashes.
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
