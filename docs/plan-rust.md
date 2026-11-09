# Technical direction and next stages

Current status: plugin, GIFs, avatar, layers and bilingual TUI are implemented.
The user confirmed the TUI and a 10-minute recording on their laptop. Current
work is the [local preliminary package](paquete-preliminar.md), without streaming
or GSR-core changes. The rest of this document preserves the technical plan and
validation criteria; it does not imply that the proposed tests have been run.

Priority: screen recording with good performance, stability and synchronized
audio. GSR handles capture/audio/encoding; Rust composes and Python controls.
Changing languages does not guarantee resource savings.

Target platform: Wayland, with COSMIC as the reference. No X11-only modes are
being developed; this does not require removing upstream engine internals.

## Current foundation

The [TUI](tui.md) and [CLI](guia-cli.md) share TOML profiles and a recorder. The
Rust plugin loads PNG/JPG/GIF, orders layers and switches idle/talking according
to microphone level. Composition and behavior are separate without an ECS or
custom framework. Files are preloaded with limits; screen frames are not decoded
on the CPU.

## Before distribution

1. Validate the TUI with real GSR and comparable long sessions.
2. Choose the application's own name and mascot; geometric examples are not its mascot.
3. Prepare a reproducible build from a tree without private profiles or assets.
4. Design a joint package with a known GSR build, KMS helper and plugin, without
   replacing system GSR or adding its GUI.
5. Review dependencies, licenses and the compatibility matrix before publication.

Each item requires a concrete task. The original plan predated packaging;
Trama now has its name, artwork and a preliminary local package. See
[current status](estado.md) for completed work and remaining validation.

## GSR updates

Pin a commit per delivery and inspect ABI, capture, rendering and audio changes
before updating. Compare layouts, run automated tests and make real recordings
before changing the distributed version. Do not promise compatibility with any
executable bearing the same version or bypass hashes to accept it.

## Future features

Streaming requires checking actual GSR and destination transports/controls;
credentials must stay outside the repository and logs. Recording and streaming
simultaneously in one instance is unverified. Do not build another capture engine
in advance. Text, live control and multiple scenes belong to later deliveries
based on requirements and measurements.
