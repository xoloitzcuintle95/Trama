# KMS authorization review

Scope: directed source review of the pinned GSR KMS server/client, downloaded
upstream proxy r33 (`3b056c0`), and Trama's native/Flatpak packaging. This is not a
complete security audit, exploit validation or guarantee of safety.

## Native package

The `.deb` installs a private helper under `/usr/lib/trama/engine/`, with executable
mode 0755, no setuid and no capability-granting maintainer scripts. GSR checks for
`CAP_SYS_ADMIN` on the helper and otherwise uses `pkexec`. The user may separately
set that capability; it is not required by the package. Whether it is present on
a particular host must be checked there with `getcap`.

GSR's helper takes two arguments: Unix socket path and DRM card path. It opens
the card read-only, verifies that it is a primary DRM node, connects to the socket
and serves GSR's capture protocol. It does not load the Rust plugin or decode user
images. That narrows privileged work but leaves native DRM/protocol code as an
attack surface. System ownership and non-writable installation directories are
part of the trust boundary; this agent's mapped filesystem UIDs cannot certify
host ownership.

## Initial upstream Flatpak proxy

The reviewed source has the following confirmed behaviors:

- It can create a root-owned cached executable with `CAP_SYS_ADMIN` and
  `CAP_SETUID`, using a home path supplied as an argument.
- It copies itself through a temporary file in user-controlled directories;
  the copy routine uses `O_WRONLY | O_CREAT` without `O_EXCL`/`O_NOFOLLOW`.
- It also supports setup and global-hotkey operations unused by Trama.
- Its fallback cache may be `/usr/bin/kms-server-proxy-2`, not only the home
  directory. Our earlier home-directory isolation did not cover that fallback.

These are reasons to avoid this persistence mechanism in Trama, not a claim of a
proven privilege-escalation exploit. Root ownership of a file alone does not
establish that every directory, link and update operation around it is safe.
No exploitation or privileged execution was attempted.

## Revised Flatpak launcher

Trama now packages a small unprivileged POSIX shell script under the same proxy
filename expected by GSR. It validates argument count, absolute/socket path length
and `/dev/dri/cardN` spelling, then executes the fixed host `/usr/bin/pkexec` with
the fixed system-installed GSR helper and separately quoted arguments. The third
GSR argument (home) is deliberately unused. There is no shell evaluation of
arguments, selectable executable, cached proxy, chmod/chown/setcap operation or
hotkey/setup interface. The upstream privileged helper itself is unchanged.

This trades persistent capabilities for session authorization. Polkit may cache
approval according to host policy; the script does not promise a password prompt
every time. The fixed path requires a system Flatpak installation whose files and
parent directories are protected by the host. The broad Flatpak host-execution
permission remains; this is not a tightly isolated sandbox.

## Tests and remaining checks

Local tests substitute a harmless fake pkexec in a temporary script copy, check
literal forwarding (including shell metacharacters), a fixed executable target,
exit propagation, and rejection of malformed card/socket/count inputs before
calling it. They never run Polkit, root commands or the real helper.

The user rebuilt/updated the Flatpak and confirmed capture, recovery after
authorization denial, and stopping with `x` with a saved MKV and TUI return.
Pending on the laptop: verify system-owned deployment with no capabilities or
setuid, check that KMS exits after stop/cancel and verify no new cached privileged
copy appears. A helper crash or
protocol flaw remains possible; this review does not prove their absence.

Opening/configuring the TUI does not launch this helper. If an earlier build was
used to start capture or run upstream setup, a privileged cached copy may already
exist. Updating the app will not remove it automatically. Inspect narrowly and
plan cleanup explicitly; do not delete GSR caches or personal directories blindly.
