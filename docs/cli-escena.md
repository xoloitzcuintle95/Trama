# Compositor architecture

## Components

- **Interface:** Python, curses TUI and text CLI. Configure before recording.
- **Profile:** one TOML schema shared by the TUI, menu and direct command.
- **Composition:** Rust `cdylib` plugin, rendering RGBA into GSR's framebuffer.
- **Engine:** native GPU Screen Recorder for capture, audio, encoding and output.

```text
TOML → Python validation → temporary manifest → Rust preload
                                               ↓
Monitor → GSR/KMS → GL/GLES layer composition → GPU encoding → MKV
Microphone → GSR audio ────────────────────────────────────────┘
           → parec → atomic RMS level → idle/talking state
```

The API is plugin header 0.1 from GSR commit
`f97d1e392816503282d20a0804c3ce3fd2943767`, version 6.1.7. GSR's core is not
modified. The build compares C/Rust layouts and records engine/plugin hashes.
Finding another executable that reports 6.1.7 is not sufficient.

Only the TUI thread calls curses. Queries and recording run outside that thread.
The shared recorder preserves SIGINT shutdown and waits for file finalization;
the TUI controls it through an event, without a separate capture implementation.

## Layers and avatar

Concrete types, without a generic framework: a PNG/JPG/GIF graphic, or an avatar
with two GIFs. Configuration is resolved during init; draw performs no file reads,
decoding or parsing. Scaling changes the GPU quad, not the preloaded pixels.

Transparency is preserved with premultiplied alpha blending. GIFs use a monotonic
clock, file timings/disposal/loops and a bounded full-frame cache. A missing/zero
delay uses 100 ms; a finite animation holds its last frame. Changing avatar state
restarts the incoming GIF's clock.

The detector measures amplitude; it does not recognize speech. `parec` produces
mono float32 at 16 kHz; a thread computes RMS in 20 ms blocks and publishes atomic
booleans. The same resolved input goes to GSR and the detector, but these are
**two captures**. GSR maintains recorded-audio clocks; the detector does not
access its buffers.

Hiding a layer keeps its resources loaded and skips drawing. It neither releases
all memory nor permits an invalid source. There are no scene changes or live edits.

## Limits

| Resource | Limit |
| --- | --- |
| Layers / avatar | 16 layers, at most one avatar |
| Profile / manifest | 128 KiB each |
| Compressed file | 8 MiB per source |
| Source dimension | 1..4096 per axis, subject to the RGBA limit |
| Image / GIF cache | 16 MiB per source |
| GIF | Up to 1024 frames; managed temporaries up to 8 MiB |
| Preloaded scene | 64 MiB RGBA, including hidden layers and both avatar GIFs |
| Composition | 8-bit SDR |

These limits are not an RSS ceiling: GSR, textures, the allocator, decoders and
the driver use additional memory. Rejection may occur after decoding another
layer. Repeated sources are not deduplicated. PNG/JPG release CPU RGBA after upload.

JPEG is converted to RGB/Luma, then opaque RGBA. ICC color handling and automatic
EXIF orientation are not promised. The renderer preserves the host's GL context,
thread and state; an error disables the instance and is logged. This is not a
sandbox: the plugin and GSR share a process.

## Code and contracts

- [CLI and shared recorder](../scripts/compositor.py).
- [TUI](../scripts/trama_tui.py) and [model](../scripts/trama_model.py).
- [Profile](../scripts/compositor_profile.py) and [devices](../scripts/compositor_devices.py).
- Rust [scene](../rust/src/scene.rs), [media](../rust/src/media.rs) and [renderer](../rust/src/render.rs).
- [Unsafe, ABI and OpenGL contract](../rust/SAFETY.md).
- [Development and testing](desarrollo.md).
