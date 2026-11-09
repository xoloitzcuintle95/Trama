# Trama preliminary package

Status: local evaluation for **Pop!_OS 24.04 / amd64 / Wayland-COSMIC**.
This is not a stable release or a promise of compatibility with other distributions.
Application version is `0.1.0~alpha1`; the plugin retains 0.4.0 because these
components use independent version numbers.

## Contents

- `trama` command, bilingual TUI and shared recording CLI.
- Rust plugin and scene validator from the verified build.
- GSR **6.1.7**, commit `f97d1e392816503282d20a0804c3ce3fd2943767`, and its
  `gsr-kms-server`, private to `/usr/lib/trama/engine/`.
- Icon, application entry with `Terminal=true`, neutral sample profile, TUI manual
  and dependency notices.

It does not bundle GSR's GUI, `gsr-cli`, videos, personal profiles, compilers, the C
reference, tests, development targets or copies of shared multimedia libraries.
System libraries/tools are declared as APT dependencies. The engine retains its
internal capabilities: GSR has not been reduced or rewritten. Although Wayland is
the target, upstream's binary retains X11 dependencies.

Trama selects its private engine when `engine/` exists. It does not install
`gpu-screen-recorder` globally in PATH or replace an existing native GSR.
The manifest checks engine, plugin, helper and validator hashes. Replacing just
one component with another version is not accepted.

## Local build without sudo

Requires the existing verified GSR/plugin build, Debian tools (`dpkg-deb`,
`dpkg-shlibdeps`), Cargo/Rust and cached lockfile dependencies. For engine/plugin
builds, see [development](desarrollo.md) and the
[manual](guia-cli.md#2-installation-and-requirements).

```bash
python3 scripts/build-deb.py
```

Output is written to `build/packages/`:

```text
trama_0.1.0~alpha1_amd64.deb
trama_0.1.0~alpha1_amd64-sources.tar.xz
trama_0.1.0~alpha1_amd64.sha256
```

`--output /ruta/a/carpeta` changes the output directory. Building does not install
anything, run `setcap`, configure services or change `/usr`.

The source archive is separate from the runtime: own code, an upstream snapshot
and vendored Cargo dependencies with notices. From its root,
`bash packaging/rebuild-from-source.sh` rebuilds without installing, provided the
native tools/dependencies are available. Binary identity across compilers or
environments is not promised. Snapshots do not include Git metadata.

## Inspection and installation on the laptop

First inspect the package and hashes, without sudo:

```bash
cd build/packages
sha256sum -c trama_0.1.0~alpha1_amd64.sha256
dpkg-deb --info trama_0.1.0~alpha1_amd64.deb
dpkg-deb --contents trama_0.1.0~alpha1_amd64.deb
```

The following command **requires sudo**. It installs the package and lets APT
resolve dependencies; the agent does not execute it:

```bash
sudo apt install './trama_0.1.0~alpha1_amd64.deb'
```

Then, from a terminal in your graphical session, without sudo:

```bash
trama --help
trama /ruta/a/tu/perfil.toml
```

The application entry also requests a terminal; it is not a GUI. Integration with
the COSMIC launcher must be checked after installation.

## KMS helper and permissions

Only the KMS helper needs privileges for direct capture. The package has no
installation scripts granting capabilities. Without them, GSR uses upstream
`pkexec` authentication; a working Polkit agent is required in the session.
Device queries have a timeout: if authentication takes too long, press `u` to
query again.

To use the same capability mechanism as upstream's installer, the following
command **requires sudo** and must be explicitly run after reviewing the package.
It applies neither to Python, the plugin nor the main engine:

```bash
sudo setcap cap_sys_admin+ep /usr/lib/trama/engine/gsr-kms-server
```

Check without sudo:

```bash
getcap /usr/lib/trama/engine/gsr-kms-server
```

This needs `setcap` from `libcap2-bin`. Installing it, if missing, also requires sudo:

```bash
sudo apt install libcap2-bin
```

An update can replace the helper and remove its capability; check it again.
The `.deb` contains neither setuid permissions nor persistent capabilities.
To revoke the capability manually:

```bash
sudo setcap -r /usr/lib/trama/engine/gsr-kms-server
```

## Configuration and removal

Existing TOML profiles open without migration. Language preference remains in
`$XDG_CONFIG_HOME/trama/ui.toml`; last-profile state retains its historical
location documented in the [TUI guide](tui.md). No graphics are written into
personal profiles.

Removal requires sudo and leaves user profiles/videos intact:

```bash
sudo apt remove trama
```

## Verify an extracted package without installing

```bash
python3 tests/test_package.py
```

The test extracts the `.deb` into a temporary folder and checks contents,
permissions, private-engine selection, manifest, tampered-helper rejection, help,
preloading with the Rust decoder, hashes and sources/notices. It grants no
permissions and does not capture the screen. Vendored-source Cargo resolution
was also checked offline, alongside a local APT simulation that installed nothing.
The host dependency resolver warned about usr-merge diversions; check APT on the
target system before installing. To repeat the TUI suite:

```bash
python3 -m unittest discover -s tests -p 'test_trama*.py'
```

## Validation and pending work

The [beta checklist](checklist-beta.md) covers a second PC, Mint or a VM, result
recording and publication criteria.

The user confirmed installing the `.deb` and recording on their laptop. Installed
runtime tests and the clean-state first-run flow also passed with simulated
devices/capture. Their profile was not touched. Commands are in
[development](desarrollo.md#test-the-installed-version-without-personal-profiles).

Before calling the package stable, the COSMIC launcher entry, a clean installation
and more stability/performance evidence remain to be checked. Simulated tests do
not replace KMS capture or physical audio.

Own code, icon, mascot and hero use GPL-3.0-only by the owner's decision, matching
GSR. Artwork was generated with ChatGPT and supplied for Trama; no human authorship
or exclusivity is claimed. Original GSR and dependency notices are included.

To update GSR: review upstream and ABI changes, build/test engine and plugin,
update the expected commit, then regenerate manifest and package together.
Never download or switch the engine automatically on the user's laptop.
