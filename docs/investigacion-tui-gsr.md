# Research: TUI presentation and GSR capabilities

The first curses visual improvements and static recording view are implemented;
see the [current TUI guide](tui.md). New GSR capabilities remain proposals, not
enabled features. Wayland/COSMIC is the support target; X11 restrictions are
documented to avoid promising modes unavailable on that platform.

Scope: research/proposal, without library migration, package installation or
capture changes. Local reference: GSR 6.1.7, commit
`f97d1e392816503282d20a0804c3ce3fd2943767`, current SDR Rust plugin.

## Original visual diagnosis (before redesign)

The previous screen used fixed positions and nearly monochrome text. Its footer
mixed about twenty actions across several lines even when unrelated to the
selected field. Adding options there would worsen navigation.

Clearer presentation is not only about colors:

- Separate Capture, Layers, Audio, Output and Advanced.
- Keep status/profile in a short header.
- Give Record and 30-second test visible primary-action space.
- Use titled panels, margins and aligned values.
- Show selected-layer properties beside the list.
- Keep four/five **contextual** footer shortcuts; move others to Help/actions.
- Use Tab/Shift+Tab for focus, arrows for lists and Enter to edit; text-field
  letters must not trigger recording shortcuts.
- Use accent color, text+color states, contrast and monochrome fallback. Symbols
  must not be the only error indication.
- Reflow to a scrollable single column in narrow terminals.

Concept sketch, not an implemented screen:

```text
 COMPOSITOR                              Profile: session · Ready
 Capture     Layers     Audio     Output     Advanced

 ┌ Capture ──────────────────┐ ┌ Video ──────────────────────┐
 │ Selected monitor          │ │ H.264 · GPU · 30 FPS        │
 │ Canvas resolution         │ │ MKV · high quality          │
 └───────────────────────────┘ └────────────────────────────┘
 ┌ Layers ───────────────────┐ ┌ Properties ─────────────────┐
 │ ● Avatar                  │ │ Bottom-right corner         │
 │ ● Image                   │ │ Box 300 px · margin 20      │
 └───────────────────────────┘ └────────────────────────────┘
 Folder: …                     Name: session-{timestamp}.mkv

 [ Record ]      [ 30 s test ]      [ Save ]
 Tab Navigate    Enter Edit     ? Help     q Quit
```

## Libraries investigated

| Option | Benefit | Cost or limitation |
| --- | --- | --- |
| Current curses | No new dependencies; retains code and tested terminal integration | Manual layout, focus, widgets and styling |
| prompt_toolkit | Layouts, inputs, styles and keybindings for full applications | New dependency/event adaptation; visual design still ours |
| Textual | CSS, panels, tables, file tree, focus/context footer, workers and headless tests | More dependencies and visual-layer migration; CPU/memory cost unmeasured |

Inspected environment: curses available, Rich 13.7.1 installed; Textual and
prompt_toolkit absent. No library was installed. A globally available version
does not constitute a project dependency decision.

Immediate recommendation: **redesign curses first**, addressing hierarchy, focus
and actions without changing recording. Current issues do not require migration.
If growth demands too many custom widgets, compare a Textual prototype before
committing to a change.

Textual is a viable growth option, not a promise of lower usage. A prototype
would preserve TOML/backend/plugin and compare startup, keyboard response, TUI
memory, dependency size and total recording resources. Do not change interface
and engine together if regressions must be attributable.

Primary sources:

- [curses: colors, windows and terminals](https://docs.python.org/3/library/curses.html).
- [prompt_toolkit: full-screen applications](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html).
- Textual [layouts](https://textual.textualize.io/guide/layout/),
  [widgets](https://textual.textualize.io/widget_gallery/) and
  [focus-sensitive footer](https://textual.textualize.io/widgets/footer/).
- Textual [workers](https://textual.textualize.io/guide/workers/) and
  [keyboard, click and screen-size testing](https://textual.textualize.io/guide/testing/).

## What the pinned engine can expose

General help does not prove a feature is compiled or available in a session.
Local manual/code were checked against project build options. The table is about
integration feasibility, **not new recordings validating these modes**.

| Capability | Evidence and condition | Compositor work |
| --- | --- | --- |
| Monitor | Already integrated | Preserve tested flow |
| Region | `-w region`/`-region`, monitor backend; transforms screen coordinates/scaling | Selection/configuration, validation and correct output canvas |
| Codec, quality, bitrate and container | Engine options exist; `--info` advertises local codecs/containers | Replace H.264/very_high/MKV constants, filter combinations, retain defaults |
| Resolution and cursor | `-s` limits resolution while preserving aspect; `-cursor` controls pointer | Recalculate canvas/placement; do not assume exact W×H in every mode |
| Pause | SIGUSR2 or IPC in normal recording; not replay/stream pause | Confirmed engine state and GIF clock policy |
| Replay | `-r`, RAM/disk, save via signal or IPC | Duration/bitrate/budget, multiple saves and GSR-returned paths |
| Streaming | Network destination with appropriate muxer supported | Specific configuration, connection state and protected keys |
| Record during replay/streaming | `-ro`, SIGRTMIN/IPC control and shared encoder destinations | Controls/output collection; validate plugin/audio/resource use |
| Window and focus | Pure X11 only; code rejects Wayland/Xwayland | Expose only where valid; no COSMIC promise |
| Portal | Disabled with `-Dportal=false` | Rebuild engine and validate COSMIC portal; a TUI toggle is insufficient |
| Per-app audio | Disabled with `-Dapp_audio=false`; enumeration conditional in code | Rebuild with dependencies and test PipeWire |
| V4L2 camera | Enumerates modes and accepts camera sources, including combinations | Permissions, formats, FPS, device availability and source layout; not a GIF layer |
| HDR/10-bit | Engine supports modes; plugin rejects depth other than 8-bit SDR | Plugin color/format/blending changes and tests; keep disabled now |
| Audio only | Engine supports no video source | Separate mode without video overlays; adapt final validation |

Codec capability also depends on GPU/driver. An option or decoder does not prove
AV1/HEVC encoding works. Combining monitors on different GPUs has explicit engine
limits and is not declared supported by this integration.

### Findings that constrain implementation

1. **Pause/GIF:** our monotonic real-time clock receives no GSR pause state.
   Resuming may advance animation phase. Choose/test real-time continuation versus
   frozen animation; merely signaling GSR does not establish the latter.
2. **Replay:** SIGINT exits without automatically saving the buffer. The current
   recorder expects one final MKV, unsuitable for replay. Save last N seconds and
   Stop buffer must be separate actions.
3. **Streaming with local output:** this commit supports it in docs and
   `recorder.c`; two instances need not be the default. Shared capture/encoding is
   an engine capability still needing integration validation and target measurements.
4. **Protocols:** local FFmpeg 6.1.1 advertises RTMP, RTMPS, SRT, HTTP and HTTPS
   output, not a WHIP muxer. The manual requires FFmpeg 8+ for WHIP. Enumeration
   does not validate a connection or service account.
5. **Keys:** file reports currently record full commands/destinations. Network
   output needs key/credential redaction and must avoid public profiles. Do not
   reuse current reporting for streaming without review.
6. **Coordinates:** region/scaling changes output video. Corner placement must
   use that canvas rather than always native monitor dimensions.

Official docs also cover [replay, streaming and concurrent recording](https://git.dec05eba.com/gpu-screen-recorder/about/).
No stream or new device test was performed during this research.

## Option organization and proposed deliveries

Separate two choices:

- **Source:** monitor, region, supported window, enabled portal or camera.
- **Output mode:** normal recording, replay or streaming, with additional local
  recording only where the engine permits it.

Layers, audio and quality belong in their own sections. Unavailable options
should be hidden or disabled with a reason (build, session, GPU or plugin).
Capabilities come from engine/build/environment, not an optimistic help-only list.

Evolve TOML through explicit migration and compatible defaults: existing `screen`
profiles remain monitor capture/normal recording. Do not introduce an unchecked
free-text field sending shell arguments to the engine.

Recommended order:

1. Visual redesign/context navigation, retaining features.
2. Video/output settings and region capture, testing canvas/overlays.
3. Pause/replay, engine control and per-mode result checks.
4. Streaming/concurrent recording, secure credentials and real testing.
5. Optional camera, X11/portal/per-app-audio backends as needed.
6. HDR only after resolving the plugin color path.

The original proposal excluded packaging/engine replacement during those deliveries.
Packaging is now tracked separately in the [package guide](paquete-preliminar.md).
Do not bypass ABI/hash checks to test another binary; engine rebuilds must keep
manifest and plugin aligned.

## Files cross-checked

- [Current TUI](../scripts/trama_tui.py).
- [Current command/validation](../scripts/compositor.py).
- [GSR build options](../scripts/prepare-gsr.sh).
- [Pinned GSR manual](../third_party/gpu-screen-recorder/gpu-screen-recorder.1).
- [Engine Meson options](../third_party/gpu-screen-recorder/meson_options.txt).
- [Engine enumeration](../third_party/gpu-screen-recorder/src/cli/commands.c).
- [Capture/session restrictions](../third_party/gpu-screen-recorder/src/recorder/capture_setup.c).
- [Selection/regions](../third_party/gpu-screen-recorder/src/recorder/capture_source.c).
- [Pause, streaming and destinations](../third_party/gpu-screen-recorder/src/recorder/recorder.c).
- [Plugin/clock](../rust/src/lib.rs).
