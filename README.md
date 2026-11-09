# Trama

Record your screen from the terminal, with overlays and a microphone-reactive
avatar. Trama uses **GPU Screen Recorder** for screen capture, audio recording
and GPU video encoding.

![Trama: screen capture, audio and overlays in one recording](assets/brand/hero.png)

**Early release.** Tested on Pop!_OS 24.04 with COSMIC/Wayland and Intel Iris Xe.
Other hardware and distributions are not yet validated. GPU H.264 encoding is
required; there is no CPU fallback. If your setup fails, please report it using
the [compatibility report guide](docs/compatibility.md).

## Features

- PNG, JPG and GIF layers with configurable position, size, order and visibility.
- Microphone-reactive avatar with idle and talking GIFs.
- System audio and microphone recording; SDR MKV output with GPU-encoded H.264.
- Reusable TOML profiles, an English/Spanish interface and direct command-line recording.

The current focus is local recording. Streaming and live preview are outside
the scope of this version.

## Getting started

Flatpak is the planned public distribution format (Linux x86_64). The package
includes the capture engine; no separate GSR installation is needed. The current
build is experimental and has no public download or Flathub listing yet.

See [Flatpak installation and testing](docs/flatpak.md). Once installed system-wide,
start it from a terminal:

```bash
flatpak run io.github.xoloitzcuintle95.Trama
```

The setup wizard lets you choose a display and microphone, load the avatar GIFs,
place the avatar in a corner and record a 30-second test. You can cancel the
wizard and configure a scene without an avatar.

After setup, **r** records, **x** or **Ctrl+C** stops, **o** shows the video path
and **?** opens help. Run Trama without sudo; GSR may request authorization to
capture the screen. [Installation and authorization](docs/flatpak.md).

## Documentation

- [TUI guide](docs/tui.md) and [CLI and profile reference](docs/guia-cli.md).
- [Building and contributing from source](docs/desarrollo.md).
- [Status, compatibility and testing](docs/estado.md).
- [Experimental Flatpak](docs/flatpak.md) and [publication checklist](docs/checklist-beta.md).

## License

Code and artwork are licensed under [GPL-3.0-only](LICENSE). Dependencies retain
their original licenses. Capture engine: [GPU Screen Recorder](https://git.dec05eba.com/gpu-screen-recorder/).
