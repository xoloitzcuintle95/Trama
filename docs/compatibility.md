# Compatibility and problem reports

Trama is an experimental Linux screen recorder with overlays. The public
[0.1.0-alpha1 prerelease](https://github.com/xoloitzcuintle95/Trama/releases/tag/v0.1.0-alpha1)
is distributed as an x86_64 Flatpak bundle with its capture engine included.
Follow the [Flatpak guide](flatpak.md) for download verification and installation;
a separate GSR installation is not required.

## Current compatibility

| Area | Current status |
| --- | --- |
| Confirmed environment | Pop!_OS 24.04, COSMIC/Wayland, Intel Iris Xe |
| Confirmed behavior | Recording, overlays, audio, stopping/finalizing MKV and recovery after authorization cancellation |
| Package target | Linux x86_64, Wayland, SDR, hardware H.264 encoding to MKV |
| Other distributions, desktops and GPUs | Unverified; not certified by the confirmed environment above |
| X11 | Unverified and not enabled by the package's default permissions |

Flatpak reduces dependency differences, but it does not replace the host graphics
driver, add encoder capabilities to a GPU or guarantee authorization works on
every desktop. The package uses GSR's static FFmpeg 9.0 build and upstream NVENC
runtime API negotiation patch; that is not a claim of successful NVIDIA capture.

Requirements and limits:

- Hardware H.264 encoding is required; there is no CPU fallback.
- Install the Flatpak system-wide at the standard location. Capture uses host
  `pkexec` and requires Polkit with a working graphical authorization agent.
  Run Trama without sudo. See [KMS security](security-kms.md).
- Microphone and system audio need a working PulseAudio-compatible service,
  including PipeWire's PulseAudio compatibility service where applicable.
- Assets must be readable and the output directory writable. Oversized GIF
  resources may be rejected by preload limits before capture begins.
- The TUI needs an interactive terminal. There is no live preview, streaming,
  text overlay or HDR support.
- No resource-usage advantage over other recorders has been measured.

## Troubleshooting

### Authorization or startup

Start Trama from a terminal to retain the error message:

```bash
flatpak run io.github.xoloitzcuintle95.Trama
```

If no authorization dialog appears, check that the app is installed system-wide,
that host `/usr/bin/pkexec` is available, and that your desktop has a running
Polkit agent. Denying authorization should return control to the TUI. A repeated
prompt is not guaranteed: Polkit may cache approval according to host policy.
Do not run the whole application as root or grant persistent capabilities as a
workaround. The [security guide](security-kms.md) documents read-only helper
inspection commands.

### Encoder initialization

`Driver does not support the required nvenc API version` means the encoder's API
requirement exceeds what the driver exposes. Include both reported API numbers,
the Trama release and driver version in a report. An invalid or empty MKV after
that error can be a consequence of encoder startup failing, rather than an
independent container or plugin fault.

For any encoder failure, retain the first relevant error, not just the final
file-inspection failure. Do not replace system libraries or update drivers
blindly. Other encoder/driver errors need their own diagnosis.

### Files, overlays and audio

Open the intended `scene.toml` explicitly and check its asset/output paths.
Validate the profile before recording; see the [CLI guide](guia-cli.md). A profile
or assets-only check does not prove that capture and audio devices will work.
Use a short recording without layers or audio to isolate capture, then add the
required layers and audio sources separately. Check system/microphone device
selection and the desktop audio service if audio alone fails.

Use a new output filename for each attempt. A recording such as
`recording-{timestamp}.mkv` has adjacent diagnostic files ending in `.gsr.log` and
`.report.json`; existing output/diagnostic files are not silently overwritten.
A failed recording is not evidence that a later attempt with different settings
will succeed.

## Report a problem or a working setup

Use [GitHub Issues](https://github.com/xoloitzcuintle95/Trama/issues). Reports from
new environments are useful whether capture succeeds or fails. Trama does not
automatically upload diagnostics; review anything you choose to share.

Include this inventory, marking unknown details as unknown:

```text
Trama release / package filename:
Distribution and version:
Desktop and session (Wayland/X11):
GPU model and driver version:
Physical machine or VM:
Installation type (system Flatpak or source):
Monitor setup and selected capture target:
Action attempted and exact error:
Steps to reproduce:
Expected versus actual behavior:
Did a short scene without layers or audio work?
Audio enabled (system / microphone / both / neither):
Did stopping or authorization cancellation return control normally?
```

Read-only environment information from a normal terminal, without sudo:

```bash
cat /etc/os-release
printf 'Session: %s\n' "$XDG_SESSION_TYPE"
printf 'Desktop: %s\n' "$XDG_CURRENT_DESKTOP"
uname -m
flatpak --version
flatpak info --system io.github.xoloitzcuintle95.Trama
flatpak info --system --show-permissions io.github.xoloitzcuintle95.Trama
```

If `nvidia-smi` is already installed, its GPU and driver inventory is useful:

```bash
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
```

Before posting, read the adjacent recording log/report locally and share only
relevant excerpts. Redact usernames, home directories and other absolute paths,
device names, window titles and media metadata as appropriate. Profiles can also
contain personal paths and device selections. Do not upload personal recordings,
raw audio, complete profiles or complete logs by default. Trama does not
automatically anonymize these files. Reproduce with neutral assets where possible
and preserve the exact error text after redaction.
