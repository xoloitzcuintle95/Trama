# Compatibility and problem reports

Trama is an experimental Linux screen recorder with overlays. Public distribution
will use Flatpak for x86_64; no separate GSR installation is needed. There is no
public download or Flathub listing yet. The native `.deb` is a development tool.

## What to expect

- GPU H.264 encoding is required. There is no CPU fallback.
- The current target is Wayland. Pop!_OS 24.04, COSMIC and Intel Iris Xe have
  user-confirmed recording, overlays, audio and stop/recovery results with the
  earlier Flatpak build. The revised compatibility build needs a new test.
- Other desktops, distributions and GPUs are not certified. Flatpak reduces
  dependency differences; host drivers, GPU capabilities and authorization matter.
- The package currently requires system-wide installation and host `pkexec` with
  a working graphical authorization agent. Run Trama without sudo. Screen capture
  may request authorization; canceling should return control to the TUI.
- Microphone/system audio require a working PulseAudio-compatible service,
  including PipeWire's PulseAudio compatibility service.
- Files and output folders must be accessible and writable as appropriate. GIF
  preload has memory limits; oversized resources can be rejected before capture.
- Streaming, text overlays and live preview are not available in this release.

X11 is exploratory, not advertised support. A Mint/XFCE test started the TUI,
selected a monitor and loaded the plugin, but failed before recording because of
an NVENC API mismatch. A temporary test permission is:

```bash
flatpak run --socket=x11 io.github.xoloitzcuintle95.Trama
```

The revised recipe addresses that class of encoder mismatch using upstream GSR's
FFmpeg build; success on that NVIDIA machine has not yet been verified. We do not
ask users to upgrade drivers blindly or replace system libraries.

## Report a problem

If Trama does not work on your setup, please report it. Reproducible reports help
us broaden compatibility; successful reports on new setups are useful too. A fix
or response time is not guaranteed. Use the project's GitHub Issues once public;
there is no external upload or automatic diagnostic collection.

Include:

```text
Trama release / package filename:
Distribution and version:
Desktop and session (Wayland/X11):
GPU model and driver version, if known:
Physical machine or VM:
Installation type (system Flatpak or source):
Action attempted and exact error:
Steps to reproduce:
Expected versus actual behavior:
Did an empty scene / 30-second test work?
Audio enabled (system / microphone / both / neither):
```

Basic checks from a normal terminal (no sudo):

```bash
cat /etc/os-release
printf 'Session: %s\n' "$XDG_SESSION_TYPE"
printf 'Desktop: %s\n' "$XDG_CURRENT_DESKTOP"
uname -m
flatpak --version
flatpak info io.github.xoloitzcuintle95.Trama
```

For NVIDIA, if `nvidia-smi` is already available:

```bash
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
```

An incomplete recording reports paths to an adjacent `.gsr.log` and `.report.json`.
Read them locally and share only relevant excerpts. Reports can contain usernames,
absolute paths, device names and media metadata. Redact those before posting;
do not upload your personal profile, recordings, raw audio or complete logs by
default. Trama does not automatically anonymize those files.

## Known failure: NVENC API mismatch

`Driver does not support the required nvenc API version` means the encoder's API
requirement exceeds what the driver exposes. A subsequent invalid/empty MKV is a
consequence of encoder startup failing. Report both API numbers and the package
version. It is not by itself proof that X11, the plugin or the container is broken.
