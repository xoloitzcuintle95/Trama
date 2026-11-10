> **Current checkpoint (2026-11-10):** [OMP handoff](handoff.md).
> Exact SDK/glibc sources are verified and included in a new local candidate.
> The helper rebuild has now passed locally, with matching source/SDK hashes and
> static linkage verified. Its report is included in the latest local candidate;
> older paragraphs below do not supersede the checkpoint.

# Trama status

## Implemented

- `trama` terminal application: Overview, Layers, Capture, Audio and Output;
  per-field editing, file picker, four-corner placement and contextual footer.
- Spanish and English: system detection, English fallback, `L` selector,
  separate preference and temporary `--lang` override.
- Rust plugin 0.4.0 / plugin ABI 4: PNG/JPG/GIF, layers and one microphone-reactive
  avatar. Bounded preload, existing timing/transparency/loop and placement rules.
- Compatible TOML profiles, load/save, separate output folder/name and direct
  recording without the TUI. Personal data stays outside the project.
- GSR CLI 6.1.7, commit `f97d1e392816503282d20a0804c3ce3fd2943767`, handles
  capture, audio, encoding and output. Its GUI is not used; its core has not been
  reduced or translated. Wayland/COSMIC is the support target.
- [Visual identity](../assets/brand/README.md): user-supplied icon, mascot and hero.
  Originals are retained and do not replace personal GIFs.
- [Local preliminary package](paquete-preliminar.md): amd64 `.deb` with private
  engine/helper and manifest, separate sources and dependency notices. Built
  without sudo; no automatic installation or capability grants.

The previous command name is not retained. Last-profile state keeps its historical
location to avoid moving user data; language is stored separately. Profiles,
graphics and videos are not automatically migrated.

## User-confirmed validation

The user confirmed that the **TUI works and looks good on their laptop**, and
completed **a 10-minute recording**. They later confirmed recording with the
installed `.deb` as well. Earlier checks confirmed smooth output and synchronized
sound. These are reports from their Pop!_OS/COSMIC environment, not instrumented
measurements or clean-install validation.

No 60-minute test has been performed. That duration was a proposed criterion for
finding memory growth, accumulated drift or infrequent failures. There is no
scheduled behavior change at 10/15/40/60 minutes and no such technical minimum
for using the program. A longer normal session can add evidence before declaring
a stable release.

## Automated and local validation

- 37 model/TUI/language/PTY tests: profiles, corners, editing, language, load/save,
  session recovery, unsaved changes, stopping and ECHO/ICANON restoration. Includes
  a 30-second simulated recording with a synthetic MKV.
- 5 package tests passed: allowed contents, ownership/permissions, no privileged
  installation scripts, private engine after extraction, bilingual help, real
  asset validation, tampered-helper rejection, sources/hashes/notices.
- Earlier GL hosts use llvmpipe; the detector is tested with synthetic PCM. These
  checks do not certify physical audio, GPU operation or KMS capture in this session.
- Two extended CLI checks remain pending because development artifacts are
  missing: `media-dump` and the compiled C reference/manifest. The C reference
  was neither changed nor rebuilt to prepare the minimal runtime.

The local APT simulation resolved the `.deb` without installing it or replacing
system GSR. The source snapshot resolved its 43 vendored crates with Cargo
offline; runtime files contain no personal build-directory path. The `.deb` is
about 1.5 MiB and separate sources about 5.3 MiB. This is not recording-memory
usage. The ELF resolver warned about host usr-merge diversions; clean-install
validation is still pending.

## Pending before publication

- Test the COSMIC application launcher and installation on a clean machine/user.
  Installation and recording on the laptop are already user-confirmed and do
  not need repeating solely to mark that item complete.
- Own code and visual identity are GPL-3.0-only by the owner's decision, matching
  GSR. Artwork was generated with ChatGPT. Notices and sources are retained;
  the package remains for local evaluation and has not been published.
- Equivalent measurements against GSR alone and OBS, plus longer stability testing.
  No resource advantage or achievement of the 150 MB aspiration is claimed.
- Clean installations: APT dependencies, drivers, Polkit/KMS and permissions.
  The locally built package is not a universal Linux binary.

There is no preview, live editing, text, timeline or streaming. Personal recordings,
logs and reports are not part of the sources or package.

See the [beta checklist](checklist-beta.md), [development](desarrollo.md), [TUI](tui.md),
[architecture](cli-escena.md), [package](paquete-preliminar.md) and [plan](plan-rust.md).

## Installed-runtime acceptance

**19 tests ran against the installed version**: 8 integrity/launcher/model/decoder/
error tests and 11 pseudoterminal tests. All passed, alongside the 5 package
checks. Modules and binaries under `/usr/lib/trama` and the launcher match the
local preliminary `.deb` byte for byte.

The first-run case starts without arguments in an empty temporary folder, with
fresh state/settings: display, microphone, neutral assets, corner, save and return.
Load/save, PNG/JPG/GIF, hiding/reordering/removing layers, corners, missing/invalid
GIFs and missing explicit microphones also pass. The 30-second flow creates a
synthetic MKV and checks stopping, returning and terminal restoration. User
profiles are preserved.

The installed runtime was not changed and the package was not regenerated or
reinstalled for these checks. PTY displays, audio and capture are simulated;
physical KMS/audio validation of the `.deb` remains the user's confirmation.
Commands and isolation: [development](desarrollo.md#test-the-installed-version-without-personal-profiles).

## Beta documentation preparation

README updated to separate `.deb` installation from source execution, explain
requirements/output and distinguish real from simulated testing. The
[checklist](checklist-beta.md) covers a second PC, clean installation, first
physical run, permissions, audio/video, coexistence and release preparation.
Mint and Ubuntu VM remain untested; a VM does not certify physical-GPU capture.
The version remains `0.1.0~alpha1`. No package was rebuilt or published for this
documentation update.

## Experimental Flatpak

The local x86_64 Flatpak has been built, exported and installed. The user confirmed
TUI configuration and real recording on Pop!_OS/COSMIC with the revised launcher.
Denying Polkit authorization recovers correctly; stopping with `x` finalizes the
MKV and returns to the TUI. These are user-reported hardware results.

A directed [authorization review](security-kms.md) replaced upstream's persistent
capability-bearing proxy with an unprivileged launcher that asks Polkit to run
only the fixed system-installed KMS helper. Seven local recipe tests pass. No
privileged command was executed by the agent; helper process cleanup and host
ownership/capability checks remain pending.

A private test bundle and SHA-256 file were generated for second-machine testing.
The bundle is approximately 2.4 MiB, excluding shared runtime downloads. The other
PC is being tested; no additional distribution or GPU is certified yet. Complete
release sources/notices, metadata and publication checks remain pending. See the
[Flatpak procedure](flatpak.md). No public release has been made.


## Public distribution and compatibility direction

Public packages will be Flatpak-only; the native `.deb` builder remains a
local development tool. The revised recipe uses GSR's static FFmpeg, including
its NVENC runtime API negotiation patch, plus upstream's i965 driver and VAAPI
search paths. This revision is prepared, not yet capture-validated. The earlier
Mint/XFCE/X11 test loaded the plugin but failed encoding because runtime FFmpeg
required NVENC API 13.1 and the driver exposed 13.0. The existing test bundle
predates this correction. See [build instructions](flatpak.md) and
[compatibility reporting](compatibility.md). No new hardware support is certified.

## Flatpak candidate and presentation

The user confirmed recording with the revised static-FFmpeg build on the
Intel/COSMIC laptop. The local release assembler preserves those binary hashes,
adds AppStream metadata and component notices and produces a separate module/
Cargo source archive and checksums. It does not install or publish. Exact SDK
glibc sources/patch and helper relinking review, real public URLs and host-helper
checks remain publication blockers; see [candidate assembly](flatpak.md#release-candidate-assembly).
A compatibility issue template is prepared in `.github/ISSUE_TEMPLATE/`.
Suggested presentation: retain the illustrated hero, add one short real TUI
workflow GIF, and use a separate optional recording clip to demonstrate overlays.
Review screen content, filenames and audio for personal data before publication.

## Helper-source closure follow-up

The source collector and SDK-only helper rebuild procedure are prepared. They
select the recorded SDK/glibc commits, preserve the original SDK patch and
configuration, reject different SDKs or changed archives, and can feed verified
sources/rebuild evidence into a new candidate. No installed binary was changed.
The source collector reached the pinned SDK fetch but failed DNS resolution in
the agent environment. The agent also cannot create a Flatpak build instance.
Actual source download/recompile therefore remain unverified; the existing
candidate and its explicit blockers have not been replaced. Current checks:
6 helper-source tests, 8 recipe tests and 5 release tests pass. AppStream still
has only its known missing-homepage warning; no public URL has been invented.
An idle snapshot found no running KMS helper and no file capabilities on the
installed helper. UID remapping prevents certifying host ownership here; the
snapshot does not prove process cleanup over a complete start/stop cycle.


## Verified helper-source collection

The user's source downloads completed for SDK source revision
`114ae909ec9881958bd507c8b4414aa33f758d2b` and glibc revision
`6b48c0b29c359dfa84c09c32373a48c8f663c304`. The first validation failed because
it searched the main SDK glibc element instead of its included source definition.
The verifier now checks the real include relationship and exact ref, with a
regression test against the downloaded SDK cache. It reuses existing exact Git
commits offline. Source collection subsequently passed; helper reconstruction
is still pending on the laptop. The source-only rebuild input has been prepared;
no installed artifact was changed. Seven helper-source tests now pass, alongside
the existing eight recipe and five release tests.

## Verified helper rebuild

The helper was rebuilt locally in OMP inside the recorded SDK, without network
access, privileged execution or changes to the installed application. The report
is `build/helper-rebuild-check/HELPER-REBUILD.json`; its SDK manifest and source
archive hashes match the inputs. An independent `readelf -d` check confirmed no
dynamic section. The rebuilt binary differs from the original; bit-identical
output was not promised. Candidate assembly retains the tested runtime binaries
and adds the report as rebuild evidence, not as a replacement helper.

The new local candidate is
`build/releases/0.1.0-alpha1-rebuild-verified`: 16.24 MiB Flatpak and 66.96 MiB
separate sources. All three checksum entries passed, and the rebuild report was
read back from the source archive. The assembler verified the tested binaries
were unchanged. The user installed this candidate and confirmed the requested
real capture/stop/cancel checks passed. The process observer recorded two KMS
server starts and matching exits; no KMS server/proxy remained at the final
check. Root ownership, protected parent directories, mode 0755, no file
capabilities and the original helper hash were rechecked successfully.
All 7 helper-source, 8 recipe and 5 release tests passed in this session.
Before publication, the final review found no user personal data/recordings
in the candidate or intended Git contents/history; `hermes.md` is now explicitly
ignored. All 12 nested source archives and the installed binaries/bytecode were
included in the scan; dependency test fixtures and original attribution remain.
The legacy privileged proxy was found outside these artifacts and preserved
because the official GSR Flatpak is also installed.

The reviewed source is published at https://github.com/xoloitzcuintle95/Trama,
with commit `09fa993` on `main` and the 3 original commits preserved. The final
13 staged files were privacy-checked and committed with the public alias/noreply
identity. The public README was read back successfully. `origin` uses working
SSH authentication. No Flatpak release asset has been uploaded; creating and
uploading GitHub Releases still requires an authenticated route outside this
environment. Keep binary/source/checksum assets together and mark the release
experimental/prerelease.

The latest local candidate is `build/releases/0.1.0-alpha1-github`, with the real
homepage/source/issues URLs. AppStream validation succeeds, five release tests
pass and all three artifact checksums pass. Engine/helper/plugin/checker hashes
are unchanged from the user-tested predecessor. Only three regular source-archive
members changed (AppStream XML, release assembler and build inventory); all
dependency archives remain byte-identical to those privacy-reviewed.
The user installed this exact bundle and confirmed the recording smoke test
works. OMP verified installed commit
`df30d61983d994380e3afbd9db0656b49481627dd2299811f30ee913ccb58ad2`,
the unchanged helper hash, protected root-owned deployment, mode 0755, no file
capabilities and no remaining KMS server/proxy process. The recording remains
private; neither it nor its absolute local path was added to project artifacts.
No history was reset or local data deleted. Binary release publication and
website/Reddit actions remain separate; this is not a complete security/legal audit.
