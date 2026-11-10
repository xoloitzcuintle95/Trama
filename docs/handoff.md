# Continuation checkpoint — 2026-11-10

Start here when resuming in OMP. Read AGENTS.md, inspect Git status and preserve
existing user changes. This checkpoint supersedes older chronological status
paragraphs where they describe a download or build as still pending.

## Current task

Publish the reviewed source to the user's new GitHub repository, preserving the
existing history, and prepare the experimental Flatpak release assets. Do not
install system software or change the recording pipeline. Website/Reddit
publication remain separate actions. No streaming, text, GUI or preview additions.

Public distribution will be **Flatpak only**, x86_64. The `.deb` builder remains
for development. Code/artwork are GPL-3.0-only; dependencies retain their licenses.
The newly created AppStream metadata document alone is CC0-1.0.

## What is confirmed

- User-confirmed recording on Pop!_OS 24.04, COSMIC/Wayland, Intel Iris Xe,
  including a previous 10-minute session. TUI, animated overlays and audio have
  been user-tested; cancellation of authorization and stopping with `x` return
  control to the TUI and save the recording as appropriate.
- The user built and confirmed recording with the revised static-FFmpeg Flatpak.
- GSR is pinned to 6.1.7, commit
  `f97d1e392816503282d20a0804c3ce3fd2943767`. The packaging uses GSR's static
  FFmpeg build, its original NVENC runtime API negotiation patch, pinned inputs,
  upstream's maintained i965 driver selection and VAAPI search paths.
- Earlier Mint/XFCE/X11 testing with temporary `--socket=x11` permission opened
  the TUI, enumerated the monitor and loaded/unloaded the Rust plugin, but failed
  encoding: runtime FFmpeg required NVENC 13.1; the driver exposed 13.0. That test
  predates the packaging correction. No successful NVIDIA/X11 capture is known.
  Do not ask for a blind driver upgrade. That PC belongs to the user's partner
  and is not currently available for more testing.
- No measured OBS superiority, universal Linux support or memory cap is claimed.

## Git and privacy

Publication baseline: `97924c0 Improve Flatpak GPU compatibility and prepare release candidate`.
This publication update includes:

- `scripts/prepare-helper-sources.py`, `packaging/flatpak/rebuild-helper.py`,
  `tests/test_helper_sources.py` (new).
- `scripts/release-flatpak.py`, `packaging/flatpak/REBUILD.md`,
  `docs/flatpak.md`, `docs/estado.md` and `docs/security-kms.md` (modified).
- `.gitignore`, this checkpoint and its AGENTS/status references.
- `hermes.md` was already present as an untracked user file when this handoff
  began. It is now explicitly ignored. Its contents were not reviewed or modified;
  preserve it locally and do not force-add it.

Profiles, recordings, build caches and release artifacts remain on disk, ignored
by Git. Do not delete them or include them in Git/package/source snapshots.
The final privacy review scanned 108 intended versionable files, all 3 reachable
commits and 129 distinct historical blobs. It found no user personal paths,
credentials or recordings. The only versioned media are the 3 brand PNGs and
3 neutral example assets. All historical author/committer identities and the
current Git configuration use the public alias and GitHub noreply email.

The user chose a new GitHub repository with the clean source and the existing
3 commits retained, with downloads attached to Releases. Do not reset `.git`,
rewrite history, delete local data or upload the entire working directory.
The user created https://github.com/xoloitzcuintle95/Trama, verified public with
issues enabled. `origin` now uses `git@github.com:xoloitzcuintle95/Trama.git`.
The reviewed source was committed as `09fa993` and pushed to `main` over existing
strict-host-key/batch-mode SSH authentication; the public README was read back
successfully from GitHub. The 3 original commits were retained. HTTPS push
authentication is unavailable; keep the working SSH remote. The final 13 staged
files were checked for unexpected paths, personal identifiers and credentials;
the commit uses the public alias/GitHub noreply identity.

No Flatpak release asset has been uploaded. GitHub CLI/API-token/browser-relay
access for creating/uploading Releases remains unavailable. Do not ask the user
to paste credentials into chat.

## Artifacts and sources

All paths below are local and ignored:

- `build/flatpak-app-v4`: user's built app directory; tested binaries/provenance.
- `build/flatpak-input-v4`: matching prepared source snapshot/manifest.
- `build/helper-source-cache`: downloaded Git object caches. Reuse exact commits
  offline instead of fetching or recompressing unnecessarily.
- `build/helper-sources`: **successfully verified** exact SDK/glibc archives,
  manifests, SDK OSTree evidence and patch hashes.
- `build/helper-rebuild-input`: source-only input extracted from the earlier
  candidate: GSR/libdrm archives, recipe, SDK manifest and build provenance.
- `build/helper-rebuild-check`: successful SDK-only rebuild, helper/link map and
  `HELPER-REBUILD.json`; the binary was not executed or installed.
- `build/releases/0.1.0-alpha1-github`: latest local candidate, with the verified
  GitHub homepage/source/issues URLs and conditional missing-URL checklist.
  **16.24 MiB Flatpak**, **66.96 MiB separate source archive**, release info and
  checksum; all three checksum entries passed. AppStream validation succeeds.
  OSTree commit: `df30d61983d994380e3afbd9db0656b49481627dd2299811f30ee913ccb58ad2`.
- `build/releases/0.1.0-alpha1-rebuild-verified`: installed/user-tested predecessor
  with the same engine/helper/plugin/checker hashes and verified rebuild report.
- `build/releases/0.1.0-alpha1-with-helper-sources`,
  `build/releases/0.1.0-alpha1`, other release directories and `build/packages/`
  contain older candidates/private bundles. Do not publish an older file by mistake.

The assembler preserves tested engine/helper/plugin/checker hashes, adds notices
and metadata, removes build-only libdrm files and exports to a separate local
repository. The assembler did not install or upload anything. The user installed
the `rebuild-verified` predecessor and confirmed real capture/stop/cancel checks.
The user has now installed the `github` bundle and confirmed its recording smoke
test works. OMP verified installed commit
`df30d61983d994380e3afbd9db0656b49481627dd2299811f30ee913ccb58ad2`,
the original helper hash, root-owned protected deployment directories, mode 0755,
no file capabilities and no remaining KMS server/proxy process. The user's
recording was not opened, copied or included in Git or release assets.

Source collection originally failed because the verifier searched for glibc's
ref directly in `elements/bootstrap/glibc.bst`. The real SDK includes
`elements/bootstrap/include/glibc-source.yml`. This is fixed and covered by a
regression check against the real downloaded SDK cache. Collection then passed.
Exact revisions:

- SDK OSTree: `a1b744b072d9f55d061e35382547ae80dad8d92abecc1da7dc1818de2daabfd3`.
- SDK source: `114ae909ec9881958bd507c8b4414aa33f758d2b`.
- glibc: `6b48c0b29c359dfa84c09c32373a48c8f663c304`.

## Helper rebuild verified

The helper rebuild completed locally in OMP on 2026-11-10, using the command
below. `build/helper-rebuild-check/HELPER-REBUILD.json` now exists. Its source
archive and SDK manifest hashes match the inputs; an independent `readelf -d`
check found no dynamic section.

```bash
cd "$HOME/project-gsr-compositor"
flatpak build --readonly --unshare=network --filesystem="$PWD" build/flatpak-app-v4 \
  python3 "$PWD/packaging/flatpak/rebuild-helper.py" \
  "$PWD/build/helper-rebuild-input" \
  --output "$PWD/build/helper-rebuild-check"
```

No sudo. It checks the SDK manifest, rebuilds libdrm and the helper with the
recorded flags, checks static linkage and writes a report/link map. It does not
execute the helper, grant capabilities, invoke Polkit or install anything.
OMP successfully allocated the Flatpak build instance without network access.
The rebuilt helper SHA-256 is
`b9004c4923223ebc1ca5cfa6aeaeaa8fed449b27fc168682bdad8f763fbec381`;
the original is
`4ebd02de6c9d6e9991e9d1bb53782bb5773624a86ec97cba18e562bc758eb0fa`.
Binary identity is not promised. No installed helper was changed or executed.

The new candidate was assembled successfully with:

```bash
python3 scripts/release-flatpak.py \
  --helper-sources build/helper-sources \
  --helper-rebuild build/helper-rebuild-check/HELPER-REBUILD.json \
  --output build/releases/0.1.0-alpha1-rebuild-verified
```

Retain prior candidates. The assembler checks SDK/source/binary hashes before
accepting the rebuild report. Source availability/rebuild evidence is not a
claim of a comprehensive legal audit.

## Final-candidate helper validation

The user confirmed the requested real capture/stop/cancel checks passed after
installing the final candidate. The 0.2-second process observer recorded two
root-owned KMS server processes, both followed by exit events, with no unreadable
entries in its snapshots. A final process check found no KMS server/proxy.
The installed commit, helper hash, root ownership, protected parent directories,
mode 0755 and absence of file capabilities were checked again successfully.
Evidence remains in `build/kms-lifecycle-20261110T094651Z.jsonl`; the observer
has exited and is no longer running. The process log does not distinguish a
Polkit denial from other UI actions; that outcome is user-confirmed. This is
target-machine evidence, not an exhaustive security audit or resource benchmark.

## Publication privacy/source review

The actual source archive was recursively scanned, including all 12 nested
upstream/SDK archives and the vendored Rust trees: 43,018 members, 41,319 regular
file payloads. No user local identity/path or private archive-header identity was
found. Credential-like matches were upstream CI variables and URL-test examples;
private-key markers belonged to public SDK/mbedTLS test fixtures or parser
constants, not the user's credentials. Upstream source hashes matched the
recorded inventory. Preserve those sources/notices rather than deleting fixtures.

The installed payload's 410 file paths, including 7 ELF paths and 8 Python
bytecode files, were scanned. No user identity/path or credential was found;
GSR's PEM delimiters were parser strings, not complete private keys. A temporary
local import of the actual Flatpak bundle matched the installed candidate commit;
its commit metadata had no user local identity/path or recognizable credentials.
The temporary audit repository was removed without installing anything.

Only the intended icon and geometric examples occur as own-source/runtime media;
the source copies match the versionable assets and all GIF frames were decoded.
Brand PNGs retain OpenAI C2PA provenance, not user EXIF/GPS/contact metadata.
Dependency sources contain their own public diagrams and LAME audio fixtures;
FFmpeg's small files named `.mp4`/`.mkv` under `tests/ref/` are textual references,
not the user's recordings. No personal footage was found. This is evidence for
this exact candidate, not proof against arbitrary steganography or future files.

The `github` source archive was compared with the recursively audited
`rebuild-verified` archive: no added/removed regular members, and only
`BUILD-INFO.json`, top-level `release-flatpak.py` and the AppStream XML changed.
All dependency archives and original runtime sources are byte-identical.

The notice/source review found all 10 declared upstream archives, 43 Rust crates,
SDK/glibc inputs, relink instructions and component notices. The source tree's
`packaging/copyright` describes the separate native development `.deb`; the
Flatpak's installed notice is `packaging/flatpak/NOTICE`.

Upload only the selected candidate's `.flatpak`, `-sources.tar.xz`,
`RELEASE-INFO.json` and `.sha256` as release assets. Do not upload its local
`repo/`, build caches, recordings, profiles, lifecycle log or `hermes.md`.

## Remaining release items

1. Source repository: https://github.com/xoloitzcuintle95/Trama. Real homepage,
   source-browser and issue URLs are included in the `github` candidate.
   AppStream validation succeeds and the five release tests pass. The user
   installed and confirmed the exact final bundle's recording smoke test.
   OMP rechecked the deployment/helper and found no remaining KMS process.
   The assembler's automatic host/capture reminder is satisfied by this separate
   recorded validation; no artifact/checksum was edited to erase that reminder.
2. Keep the legacy host proxy unless its owner explicitly requests cleanup:
   `$HOME/.local/share/gpu-screen-recorder/kms-server-proxy-2` is root-owned,
   mode 0755, with `CAP_SYS_ADMIN` and `CAP_SETUID`. The official GSR Flatpak is
   also installed and may use it. The known home/Flatpak-data/system/tmp paths
   were checked; no other matching copy was found. This proxy is outside the
   publication artifacts and Git, and was not executed, altered or deleted.
3. Source publication and final-bundle validation are complete. Create a GitHub
   **prerelease** and attach only the four candidate files listed
   above. The user can do this at
   https://github.com/xoloitzcuintle95/Trama/releases/new with tag
   `v0.1.0-alpha1`, targeting `main`. GitHub's automatic source ZIP/tar does not
   replace the companion `-sources.tar.xz` containing dependency/SDK sources.
   Website/Reddit remain separate actions; broad host permissions remain,
   not strong isolation.

## Tests and presentation

Latest automated checks: **7 helper-source + 8 recipe + 5 release tests passed**
in this session. These source/recipe/assembly checks are separate from the real
user capture and observed process lifecycle above. Useful commands:

```bash
python3 tests/test_helper_sources.py
python3 tests/test_flatpak.py
python3 tests/test_flatpak_release.py
git diff --check
```

The user is preparing a short TUI workflow GIF and optionally a real recording
clip (Minecraft with avatar). Keep the existing illustrated hero. The clip is a
demonstration, not a benchmark, and need not crowd the README. Review paths,
names, notifications and audio for personal information. Website work is in
Hermes; preserve the design and describe current functions honestly. Text and
streaming are future work, not implemented launch features.

References: docs/flatpak.md, docs/estado.md, docs/checklist-beta.md,
docs/compatibility.md and packaging/flatpak/REBUILD.md.
