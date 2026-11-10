# Rebuild this local candidate

This archive contains the exact Trama snapshot used by the tested binaries,
vendored Cargo dependencies, hash-verified module source archives, original
notices/patches, recipe and build provenance. It excludes profiles and recordings.
AppStream metadata/notices were added after capture testing without changing the
engine, helper, plugin or scene-checker binaries. The original and offline recipes
are both retained. The release assembler is included for inspection; its local
cache defaults refer to the development checkout, not this archive's structure.

Install Flatpak, flatpak-builder and the Freedesktop 26.08 SDK/runtime and its
rust-stable extension through your distribution/Flatpak. From this directory:

```bash
flatpak-builder --arch=x86_64 --force-clean --repo=repo app io.github.xoloitzcuintle95.Trama.offline.json
flatpak build-bundle --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo repo trama-rebuilt.flatpak io.github.xoloitzcuintle95.Trama experimental
```

The module inputs and Rust crates are local. The SDK/runtime must already be
installed; this archive does not replace them or promise bit-identical output.
Keep the original build's SDK/runtime commits from BUILD-INFO.json when comparing.
Building does not install the application or grant helper privileges.

## Static helper and SDK sources

The static KMS helper links SDK glibc/libgcc in addition to libdrm. The original
GSR source and helper compile flags are in the included archives/manifest.
SDK-SOURCE-MANIFEST.json records the SDK source recipe; BUILD-INFO.json records
its exact OSTree commit. SDK/GCC runtime notices/exceptions are retained.

When `helper-sources/` is present, it contains glibc and Freedesktop SDK Git
archives collected from the installed SDK's recorded revisions. Its inventory
records their hashes, the SDK source manifest hash and the exact glibc patch.
The full SDK tree retains the original BuildStream configuration and patch,
rather than inventing a replacement glibc configuration. Instructions for building
or modifying the SDK are in that tree. If the folder is absent, exact SDK glibc
source collection is still pending; a source URL list alone is not its substitute.
Check `publication_blockers` in BUILD-INFO.json before distributing the candidate.

### Rebuild/relink the helper without installing it

After the offline application build above, run this from the source archive root:

```bash
flatpak build --readonly --unshare=network --filesystem="$PWD" app \
  python3 "$PWD/rebuild-helper.py" "$PWD" \
  --output "$PWD/helper-rebuild"
```

This rebuilds libdrm and the helper using the manifest's flags, requires the SDK
source manifest to match the original and checks that the helper has no dynamic
library dependencies. It writes `helper-rebuild/gsr-kms-server`, a linker map and
`HELPER-REBUILD.json`. It does not execute that binary, call Polkit/setcap or change
the installed app. Choose a new output directory for another attempt. Compiler
messages/link maps can contain local paths; review before sharing them.

For a modified glibc, use the included SDK sources/build configuration to prepare
an SDK containing that modification, then perform the same libdrm/helper build
inside it. The verification script intentionally rejects a changed SDK source
manifest: for an intentional modification, adapt that comparison in your copy
and document the changed library rather than claiming an original-SDK rebuild.
The C source and linker flags remain available; there is no application-imposed
restriction on modifying/relinking them. The resulting helper will have different
integrity hashes: rebuild the application's hash manifest before installing a
modified application, rather than replacing the helper behind its existing hash.

The procedure is not claimed as exercised until a matching rebuild report is
included. Legal/source review and capture validation are separate checks; neither
a successful compiler invocation nor a checksum proves all license obligations.
