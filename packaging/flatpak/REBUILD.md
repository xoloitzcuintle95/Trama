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

## Source-completeness review still required before public distribution

The static KMS helper links SDK glibc/libgcc in addition to libdrm. The app-module
sources are included; SDK-SOURCE-MANIFEST.json records the SDK's source recipe,
and BUILD-INFO.json records its commit. This does **not** by itself supply the
exact glibc sources/SDK patch or satisfy every static-linking distribution
obligation. Obtain/retain the matching SDK sources and patch and verify a helper
rebuild/relink procedure before publishing this candidate. GCC runtime exceptions
and the SDK license notices must be reviewed as applicable. This is a local
candidate with explicit blockers, not a claim of completed legal auditing.

The original GSR helper compile command is in the manifest. Its source is
kms/server/kms_server.c in the GSR archive. Rebuild libdrm with the manifest's
configuration, then compile the helper against the intended SDK libraries; do not
replace the installed helper without rebuilding the recorded integrity hashes.
