# Visual element configuration

This command sets the **initial** position, dimensions and visibility of one
Rust element. Static PNG/JPG and animated GIF are supported; APNG and text are
not. The loader identifies content by signature, not extension. The renderer
receives RGBA and a rectangle without knowing about GIF or PNGtuber behavior.

For multiple layers and an avatar use the [TUI](tui.md) or
[scene CLI profiles](guia-cli.md). This single-element command has no watcher,
IPC or changes during recording. Changing options requires another capture.
Configuration stays outside the callback, avoiding premature live control.

## CLI usage

Already built as `build/overlay-rust.so`. To rebuild/verify without sudo:

```sh
bash scripts/check-rust-overlay.sh
```

From the project root, first validate without recording or GPU access:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --x 100 --y 80 --width 300 --height 200 --check
```

Because this GIF is square, the result is 200×200 at 100/80, visible and
proportional. `--check` validates source/configuration with the same Rust code as
init and creates no capture. It still requires the build and known installed GSR
fingerprint.

To record 30 seconds with system audio but no microphone, from a graphical terminal:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --x 100 --y 80 --width 300 --height 200 --audio --seconds 30
```

It stops automatically. Capture uses the full monitor through KMS, H.264 GPU,
30 FPS, `very_high` and MKV. Video/log/metrics go to
`build/recordings-element/<date-id>/` without overwriting recordings. Ctrl+C
stops early and retains partial results. Without `--audio`, sound is not recorded.

For a static PNG with height only:

```sh
python3 scripts/record-element.py --media build/rust-fixtures/idle-static.png \
  --height 180 --seconds 30
```

Recreate the sample PNG with `python3 scripts/prepare-rust-example.py`. Any other
valid PNG/GIF may be used; the command does not depend on those names.

Hide **without removing the source**:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif --hidden --seconds 30
```

The file is validated, the GIF retains its cache and the texture stays loaded.
While hidden, the callback neither draws, updates its texture nor requests its
own damage. For a later capture omit `--hidden` or use `--visible`. Hiding does
not release RAM or remove the asset; GSR retains its plugin/capture path. It is
not claimed to eliminate all GPU/memory costs of the pipeline.

Stretching is explicit:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --width 300 --height 200 --stretch --seconds 30
```

## Geometry semantics

Coordinates are pixels on the **recorded canvas**, measured from its upper-left
corner, not window coordinates or original image pixels.

| Options | Result |
| --- | --- |
| Neither dimension | Width 320, height derived from aspect ratio |
| Width only | Derived height |
| Height only | Derived width |
| Width and height | Maximum box: uniform scaling to fit both dimensions |
| Width and height with --stretch | Exact dimensions, allowing distortion |

The proportional box aligns its upper-left corner at X/Y: no automatic centering,
internal cropping or enlargement to fill the box. Space may remain on the right
or bottom. Default position remains 32/32. Negative coordinates allow partially
offscreen placement; OpenGL clips to the canvas. Completely offscreen elements
are not visible.

X/Y are integers −16384..16384. Explicit dimensions are integers 1..16384.
Derived dimensions must be positive and at most 16384; they may be fractional to
avoid rounding distortion. Extreme aspect ratios may need a smaller box so both
final dimensions remain within limits.

## Environment variables and precedence

The direct plugin can also be configured without the wrapper. Variables are read
once during init:

| Variable | Initial value / contract |
| --- | --- |
| GSR_RUST_IMAGE | Required PNG/JPG/GIF path |
| GSR_OVERLAY_X, GSR_OVERLAY_Y | 32, 32; signed integers |
| GSR_OVERLAY_WIDTH | Optional; effective 320 if height is also unspecified |
| GSR_OVERLAY_HEIGHT | Optional |
| GSR_OVERLAY_KEEP_ASPECT | true; false requires both effective dimensions explicitly |
| GSR_OVERLAY_VISIBLE | true |

Environment booleans are exactly `true` or `false`. Invalid values are rejected,
not silently corrected. Hidden state does not permit an invalid source/geometry.
CLI flags override only their corresponding variables; other exported variables
remain active. `--keep-aspect` and `--visible` override exported `false`. An
inherited width plus CLI height forms a box; for height only, do not export width.
Child processes receive structured arguments/environment, not shell command strings.

The report stores original variables and Rust-resolved effective geometry and
visibility. Earlier Rust GIF scripts also recognize the new variables. Comparison
with the **C** reference rejects height, hidden state, stretching or negative X/Y
because C does not implement them; different layouts must not be compared.
The C prototype scripts do not acquire these options and remain unchanged.

## Design and preserved guarantees

`config.rs` validates `ElementConfig` and resolves `Placement` from intrinsic
source dimensions. It contains neither OpenGL nor avatar behavior. The renderer
uses only that rectangle; the loader retains its actual formats. These are
concrete types, without engine traits, ECS or a custom plugin system. The current
cdylib is 0.4.0 / plugin version 4, using the known GSR ABI.

Configuration is resolved before rendering: no reads/parsing in draw. Scaling
changes the GPU quad, **not** decoded image resolution. Displaying a small GIF
does not automatically reduce its original cache. PNG releases CPU RGBA after
upload. GIF remains preloaded with cache ≤16 MiB, managed temporaries ≤8 MiB and
input ≤8 MiB, preserving timing/disposal/loops. Premultiplied alpha, GL state,
context/thread, deinit and panic barriers are retained.

## Verification and limitations

The suite checks ABI, geometry, transparency, GIFs and shutdown in offscreen GL.
CLI tests cover defaults, precedence, sizes and invalid input. See
[development](desarrollo.md) and [status](estado.md) to repeat tests and distinguish
them from real capture. No metrics from another build are promised.
