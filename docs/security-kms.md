# KMS authorization and security

Trama's Flatpak uses a privileged KMS helper for screen capture. This guide
explains its current privilege and data boundaries; it is not a complete
security audit or a guarantee that native capture code has no vulnerabilities.
For installation, see the [Flatpak guide](flatpak.md).

## What runs with privilege

The TUI, profile handling, image decoding, Rust compositor plugin, capture client
and recording output run as your normal user. Do not launch Trama with sudo.

For KMS capture, GSR calls `kms-server-proxy` through `flatpak-spawn --host`.
In Trama that name refers to an
[unprivileged shell launcher](../packaging/flatpak/launch-kms.sh), not upstream's
persistent privileged proxy. The launcher invokes host `/usr/bin/pkexec` with
this fixed helper:

```text
/var/lib/flatpak/app/io.github.xoloitzcuintle95.Trama/current/active/files/bin/gsr-kms-server
```

The helper runs privileged for the capture session. It accepts a Unix socket
path and a primary DRM card path, opens the card read-only, verifies the primary
node and serves GSR's capture protocol. It does not decode overlay images or load
the Rust plugin. Native DRM, socket and capture-protocol code still forms a
privileged attack surface; a read-only card open does not make that code risk-free.

The fixed path requires a **system-wide installation at the standard location**.
The helper and resolved installation directories must be root-owned and not
writable by ordinary users. A user-only installation or custom Flatpak location
is not an equivalent supported authorization setup. Do not copy the helper into
a user-writable directory, replace it behind its integrity manifest or change
its ownership to work around an error.

## Launcher boundary and authorization

The launcher:

- Requires the three arguments supplied by GSR, but deliberately ignores the
  third argument, the home directory.
- Requires an absolute socket path no longer than Linux's 107-character limit
  and a DRM card path spelled `/dev/dri/cardN`, where `N` contains only digits.
- Uses fixed absolute paths for `pkexec` and the helper, with the socket/card
  arguments quoted separately. It does not evaluate them as shell code.
- Does not offer a selectable executable, setup operation or global-hotkey
  interface, and does not create privileged cached copies or run
  `chmod`, `chown` or `setcap`.

These checks constrain launcher behavior, not every input accepted by the
privileged helper. Absolute socket-path validation alone does not establish
socket ownership or make the capture protocol safe against every local attack.
The helper is upstream GSR native code, not a new security isolation layer.

Polkit decides whether authentication is required. Approval can be cached under
host policy, so per-session helper execution does **not** promise a fresh password
prompt for every recording. Denying authorization should return control to Trama.
A missing authorization agent or broken policy should be diagnosed, not bypassed
by running the entire application as root.

Trama does not require persistent file capabilities or a setuid helper. Its native
development packaging also installs the helper without granting those privileges;
public runtime installation instructions apply to the Flatpak. Do not add
`CAP_SYS_ADMIN` or `CAP_SETUID` as a normal installation step.

## Files, devices and sandbox limits

The Flatpak grants broad access to host files and devices, PulseAudio-compatible
audio, Wayland and IPC. It also permits talking to
`org.freedesktop.Flatpak` for host execution. Consequently:

- The application can access much of your personal filesystem, not just the
  selected scene and output directory.
- Capture and audio access can expose sensitive on-screen content and sound.
- Host execution weakens the containment normally associated with Flatpak.
- The absence of network or X11 permission in the manifest is not a guarantee
  against access through host execution.

**Do not treat this package as a strong sandbox.** Install only a bundle you trust
and verify its published checksums. Checksums establish file consistency, not
that the application or its dependencies are free from vulnerabilities.

Profiles, assets and recordings remain user data. Output diagnostics can include
absolute paths, device names and media metadata; inspect and redact them before
sharing. The last-profile reference also contains a local path. See
[compatibility and reporting](compatibility.md) for privacy guidance.

## Read-only inspection

These commands inspect the system installation without granting privileges or
executing the helper:

```bash
flatpak info --system io.github.xoloitzcuintle95.Trama
flatpak info --system --show-permissions io.github.xoloitzcuintle95.Trama
helper=/var/lib/flatpak/app/io.github.xoloitzcuintle95.Trama/current/active/files/bin/gsr-kms-server
readlink -f "$helper"
namei -l "$helper"
stat -Lc '%A %a %U:%G %n' "$helper"
getcap "$(readlink -f "$helper")"
```

`namei` and `getcap` may need your distribution's utility packages. The expected
helper mode is `0755`, owner/group `root:root`, without setuid/setgid or file
capabilities; `getcap` normally prints nothing for it. Inspect the resolved parent
directories too: they must not allow ordinary users to replace the executable.
Symlinks are part of the deployment layout, so file ownership alone is not enough.
If the path is missing or writable by ordinary users, stop and investigate the
installation rather than authorizing capture.

To inspect named capture processes without running them:

```bash
ps -C gsr-kms-server -C kms-server-proxy -o pid,user,args
```

No Trama KMS helper is expected to remain after capture has stopped. Another GSR
application may also use these names; identify the application and process before
taking action. One idle process listing cannot prove cleanup across every capture
or rule out a process that exited between observations. Redact paths in process
arguments before sharing output.

## Existing GSR installations and historical caches

Earlier upstream proxy designs can leave root-owned cached executables with
`CAP_SYS_ADMIN` and `CAP_SETUID`, including a `kms-server-proxy-2` under
`$HOME/.local/share/gpu-screen-recorder/` or a system location such as
`/usr/bin/kms-server-proxy-2`. Trama's current launcher neither creates nor uses
that persistence mechanism.

A historical cache may belong to an official GPU Screen Recorder installation
that still needs it. Its presence is not proof that current Trama created it.
Do not execute unknown cached helpers, delete user caches or remove capabilities
as part of a generic Trama install/uninstall procedure. Inspect ownership,
capabilities and the owning application's documentation first; any cleanup needs
the owner's informed decision.

## Sources and helper modifications

The companion source archive contains GSR, libdrm and the SDK sources/provenance
needed for the static helper, together with component notices. Follow its
`REBUILD.md` and the [packaging rebuild guide](../packaging/flatpak/REBUILD.md) for
rebuilding/relinking, including deliberate SDK/library changes. Those procedures
do not execute the helper or grant privileges. A modified helper changes its
integrity hash: rebuild the application's integrity manifest rather than silently
substituting a binary in an installed deployment.

For checkout-based work, use the [developer guide](desarrollo.md). Successful
compilation or matching checksums are separate from security, legal/source review
and hardware capture validation.
