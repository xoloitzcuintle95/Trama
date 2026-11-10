# Install and use the experimental Flatpak

Trama's public package is the [0.1.0-alpha1 prerelease](https://github.com/xoloitzcuintle95/Trama/releases/tag/v0.1.0-alpha1)
for Linux x86_64. Its application ID is `io.github.xoloitzcuintle95.Trama` and its
branch is `experimental`. This is a downloadable bundle, not a Flathub listing.
GPU Screen Recorder is included; a separate GSR installation is not required.

Recording, overlays, audio, stopping and authorization cancellation have been
confirmed on Pop!_OS 24.04 with COSMIC/Wayland and Intel Iris Xe. Other systems
remain unverified. Read [compatibility](compatibility.md) and the
[KMS security guide](security-kms.md) before installing.

## Requirements

- Linux x86_64 with Flatpak and access to the Freedesktop Platform 26.08 runtime.
- A Wayland desktop and a GPU/driver supporting hardware H.264 encoding.
  There is no CPU encoding fallback.
- A **system-wide** Flatpak installation at the standard `/var/lib/flatpak`
  location. The KMS launcher uses a fixed helper path there; a user installation,
  custom installation location or builder run is not equivalent.
- Host `/usr/bin/pkexec`, Polkit and a working graphical authorization agent.
- A PulseAudio-compatible service for audio, including PipeWire's PulseAudio
  compatibility service where applicable.
- An interactive terminal, readable media files and a writable output directory.

No SDK, compiler or native `.deb` package is needed to run the release.

## Download and verify

Download these four assets from the prerelease page into the same directory:

| File | Purpose |
| --- | --- |
| `trama-0.1.0-alpha1-x86_64.flatpak` | Installable application bundle |
| `trama-0.1.0-alpha1-x86_64-sources.tar.xz` | Matching application, dependency and SDK sources, notices and rebuild instructions |
| `RELEASE-INFO.json` | Release provenance and component inventory |
| `trama-0.1.0-alpha1-x86_64.sha256` | SHA-256 checksums for the other three files |

In that download directory, run:

```bash
sha256sum -c trama-0.1.0-alpha1-x86_64.sha256
```

All three entries must report `OK`; do not install if a file is missing or differs.
Checksums detect changed or incomplete downloads, but do not independently
establish publisher identity: obtain the checksum file from the project release
page too. GitHub's automatically generated source ZIP/tarball is **not** a
replacement for the companion source archive.

## Install or reinstall

If Flathub is not configured for the system installation, add it for runtime
availability:

```bash
sudo flatpak remote-add --system --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

From the directory containing the verified bundle:

```bash
sudo flatpak install --system ./trama-0.1.0-alpha1-x86_64.flatpak
```

To replace an existing installation with that verified bundle:

```bash
sudo flatpak install --system --reinstall ./trama-0.1.0-alpha1-x86_64.flatpak
```

Installation requires system authorization. **Run the application without sudo**:

```bash
flatpak run io.github.xoloitzcuintle95.Trama
flatpak run io.github.xoloitzcuintle95.Trama "$HOME/scene.toml"
```

Use a terminal if your desktop launcher does not open one. The TUI requires an
interactive terminal. See the [TUI guide](tui.md) for creating a scene, recording
and stopping safely.

For noninteractive profile validation or a timed recording, the bundled backend
can be invoked explicitly; these commands do not require a native checkout:

```bash
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama /app/lib/trama/scripts/compositor.py check "$HOME/scene.toml"
flatpak run --command=python3 io.github.xoloitzcuintle95.Trama /app/lib/trama/scripts/compositor.py record "$HOME/scene.toml" --seconds 30
```

See the [CLI guide](guia-cli.md) for the distinction between packaged commands and
native development commands.

## Profiles and application data

Profiles are TOML files saved at the location you choose; recordings use the
output path in the profile. To reuse a native profile, open its TOML explicitly
and check its asset and output paths. Installation does not migrate native
settings, profiles or media.

Flatpak redirects application settings and state under
`~/.var/app/io.github.xoloitzcuintle95.Trama/`. The UI language preference is
`config/trama/ui.toml` there. The last-opened profile reference is stored at
`$XDG_STATE_HOME/xolo/session.json` inside the application; the `xolo` directory
name is retained for data compatibility. Without an explicit profile, Trama
reopens the remembered profile or defaults to `./perfil.toml`.

Keep your working profiles and media in a writable personal directory. `/app`
and `/usr` inside the application are not arbitrary host-file locations; bundled
examples should be copied out before editing.

## Authorization and permissions

Starting KMS capture authorizes the fixed, system-installed helper through host
Polkit. Only the helper runs privileged, not the TUI or compositor. Trama does
not require `setcap`, a setuid executable or a persistent privileged proxy.
Polkit may cache approval according to host policy, so a new password prompt is
not guaranteed for every recording. Canceling authorization should return control
to the TUI; report failures to recover rather than launching Trama as root.

The package has broad permissions:

- `--device=all`: device access for capture/graphics.
- `--filesystem=host`: host files, media/output paths and the capture socket.
- `--socket=pulseaudio`: system audio and microphone access.
- `--socket=wayland` and `--share=ipc`: desktop integration.
- `--talk-name=org.freedesktop.Flatpak`: host execution used by the KMS launcher.

**This is not a strong sandbox.** It has no network or X11 permission in the
manifest, but host execution and broad filesystem/device access mean those
omissions are not a security containment guarantee. Read the
[security guide](security-kms.md) for the privilege boundary and inspection steps.

## Limits and troubleshooting

The release records SDR, GPU-encoded H.264 video to MKV. It does not provide
streaming, live preview, text overlays, HDR or CPU encoding fallback. Resource
usage advantages over other recorders have not been measured.

- **Missing runtime:** check that system Flathub is configured and allow Flatpak
  to install the required runtime. The SDK is only for rebuilding.
- **Authorization fails or no prompt appears:** verify a system installation,
  host `pkexec` and a running Polkit agent. Do not work around it with `sudo
  flatpak run` or capability grants.
- **No terminal window:** start the application using `flatpak run` from an
  existing interactive terminal.
- **Missing assets or unwritable output:** open the intended profile explicitly,
  review its paths and select a writable personal directory.
- **Encoder or audio failure:** follow the current diagnostic and reporting steps
  in [compatibility](compatibility.md). Hardware support depends on the host GPU
  and drivers; a completed package installation does not prove capture support.

## Updating and uninstalling

For a new Trama release, download its matching bundle, source archive, release
information and checksums, verify them together, then repeat the system
`--reinstall` command with the new bundle filename. Do not assume `flatpak update`
will retrieve a new bundle attached to GitHub. Runtime updates are separate:

```bash
sudo flatpak update --system
```

Stop recordings before replacing or removing the application. Back up profiles
and any application data you want to retain, then uninstall with:

```bash
sudo flatpak uninstall --system io.github.xoloitzcuintle95.Trama
```

Do not add `--delete-data` unless you intend to delete Flatpak application data.
Profiles and recordings saved elsewhere are separate files: uninstalling the app
is not a backup or a cleanup procedure for them. Do not delete historical GSR
caches as part of uninstalling Trama; another GSR installation may use them.

## Sources, licenses and rebuilding

Trama code and supplied artwork are GPL-3.0-only; dependencies retain their own
licenses and notices. AppStream metadata alone is CC0-1.0. Keep the companion
source archive and its notices when redistributing the release.

The package includes GSR 6.1.7 at commit
`f97d1e392816503282d20a0804c3ce3fd2943767`, static FFmpeg 9.0 with upstream NVENC
runtime negotiation, and the Rust compositor plugin 0.4.0. This does not establish
NVIDIA compatibility on untested systems.

For the published binary, extract the companion source archive and follow its
`REBUILD.md`. The [packaging rebuild instructions](../packaging/flatpak/REBUILD.md)
cover the offline recipe, exact SDK provenance and rebuilding/relinking the
static helper. For development from a checkout, use the
[developer guide](desarrollo.md). Building sources does not install the app or
authorize its helper.
