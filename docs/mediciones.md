# Reproducible resource measurements

These are **native development tools**, not production Flatpak benchmarks. No
resource advantage over GSR or OBS is established by this guide. Generated
recordings and reports are local outputs, not published project results.

## Prerequisites and scope

Follow [development](desarrollo.md) to build the pinned native GSR engine, Rust
plugin and validators. The tools require the matching engine specifically at
`/usr/local/bin/gpu-screen-recorder`, not an arbitrary PATH entry or the Flatpak
runtime. Rust tools reject engine/plugin fingerprint mismatches and test-hook
artifacts. For C comparisons also build the reference:

```bash
bash scripts/build-overlay.sh
```

Run from the repository root in a graphical Linux session with working KMS
capture authorization and drivers, `/dev/dri`, Python and FFprobe. Do not run the
recorder or observer with sudo to obtain missing metrics. C-reference build
prerequisites and KMS security constraints are in [development](desarrollo.md)
and [security](security-kms.md).

The commands below use full-monitor KMS (`screen`), H.264 GPU encoding, no CPU
fallback, 30 FPS CFR, `very_high` quality and **no audio**. Only overlay trials
load a plugin. These workloads do not measure the TUI, scene-profile handling,
microphone detector or the entire installed Flatpak application.

## Define a repeatable workload

Use a neutral, nonprivate desktop presentation with fixed window contents for a
static baseline. For a dynamic case, replay the same local, shareable presentation
or video sequence from the same starting point in every trial. Record:

- GPU/driver, kernel, desktop/session, monitor resolution/refresh, scaling and
  number of active displays; identify the actual encoder selected in the log.
- Engine/plugin hashes, asset hashes, tool options, overlay geometry and source
  dimensions/frame count; showing a GIF smaller does not reduce its decoded cache.
- Power/thermal settings, concurrent processes, observer configuration and trial
  order. Keep those conditions stable; allow equivalent settling time between runs.
- The exact workload sequence and duration. Avoid changing windows or interacting
  differently between trials, and do not run competing recorders concurrently.

Start with a shell without inherited `GSR_RUST_*` or `GSR_OVERLAY_*` overrides,
or explicitly document every inherited setting. In particular,
`measure-rust.py` does not clear an inherited scene manifest. These scripts are
not the production recorder's sanitized environment. An inconclusive run should
be reported as inconclusive, not rerun selectively until a preferred result appears.

## Animated GIF: GSR, C reference and Rust

```bash
python3 scripts/measure-gif.py --media examples/assets/idle.gif \
  --workload "Static desktop presentation; identical windows" \
  --seconds 30 --repeats 3
```

`--seconds` is the requested **measured** interval, **5..600 seconds**, after
5 seconds of warm-up per capture. `--repeats` accepts **1..10**. Each repeat
contains baseline, C and Rust trials, with three rotating orders to reduce
ordering bias. Defaults request about 315 seconds of capture in total, plus
startup/finalization overhead. The tool reports pairwise CPU/RSS differences and
medians across repeats, not confidence intervals or proof of significance.

The same animated GIF is used by both plugins. Comparable C geometry requires
nonnegative X/Y and proportional width-only sizing: height overrides, hidden
state and stretching are rejected. This is a comparison with the independent
C reference, not a production implementation selection.

Results are written under a unique `build/measurements-gif/<UTC-id>/` directory
with MKV captures. Failure or incomplete capture stops the comparison; retain
logs and do not interpret partial trials as a completed experiment.

## Static PNG: GSR and Rust

Generate a neutral static fixture and run alternating pairs:

```bash
python3 scripts/prepare-rust-example.py
python3 scripts/measure-rust.py --image build/rust-fixtures/idle-static.png \
  --workload "Static desktop presentation; identical windows" \
  --seconds 30 --repeats 3
```

Only PNG is accepted by this tool. Each capture adds 5 seconds of warm-up to the
requested **5..600 measured seconds**; repeats are **1..10**, default 3. Trial
order alternates baseline/Rust and Rust/baseline. Output is under
`build/measurements-rust/<UTC-id>/` with MKV captures and pairwise/median CPU/RSS
differences. This is not a GIF, multiscene or avatar benchmark.

## C reference only: GSR and overlay

```bash
python3 scripts/measure.py --media examples/assets/idle.gif \
  --workload "Static desktop presentation; identical windows"
python3 scripts/measure.py --media examples/assets/idle.gif \
  --workload "Static desktop presentation; identical windows" --order overlay-first
```

This tool loads `build/overlay.so`, **not** `overlay-rust.so`. Default warm-up is
5 seconds followed by a requested 30-second measured interval per capture.
`--seconds` accepts **1..3600** and `--warmup` **0..300**, in seconds. Both
`baseline-first` and `overlay-first` are supported. Output is under
`build/measurements/<UTC-id>/` with `baseline.mp4` and `overlay.mp4`. It records
engine version and plugin/media hashes, but does not perform the Rust tools'
engine/build-manifest integrity check; preserve exact build provenance separately.

## Reports and interruption

All three tools share the sampling implementation in
[`scripts/measure.py`](../scripts/measure.py). Each result directory contains:

- Videos and full per-trial GSR logs: review encoder selection, capture failures,
  driver diagnostics, finalization and the actual visible overlay.
- JSONL samples, including warm-up and process/permission details.
- CSV samples for the measured interval.
- `summary.json`: requested duration, actual sampled coverage, commands, available
  metadata, weighted means, sampled maxima and completion status.

Sampling is nominally once per second. An interval crossing the warm-up boundary
is entirely excluded; `sampled_seconds` can be less than the requested interval.
Means are interval-duration weighted, not averages of per-process peaks. Maxima
are observed samples, not absolute peaks. Compare actual coverage before
comparing numbers.

Ctrl+C requests SIGINT and keeps collected output. The observer waits up to
15 seconds for GSR to exit/finalize, then kills the process group if necessary
and marks the run incomplete. Check `completed`, return code, probe errors and
logs; a video file alone does not prove success.

## Interpret metrics carefully

- **CPU:** sum of observed processes' user/system time, excluding waited-child
  accounting to avoid double counting. **100% is one full CPU core** and values
  can exceed 100%; it is not a whole-machine CPU percentage.
- **Process tree:** GSR starts in its own session. The observer tracks session
  processes and descendants, retaining PID plus process start time so PID reuse
  is distinguished and observed detached children can remain tracked. Very short
  lived processes, or children detached before being observed, can be missed.
  Existing external services such as the compositor/audio server are not included.
- **RSS:** summed resident memory can count shared pages more than once. Report
  MiB as bytes divided by 2^20. A sampled RSS peak is not a hard memory ceiling.
- **PSS:** apportions shared pages. Total mean/peak is available only if all
  included samples have PSS for every observed process. Privileged helpers or
  `/proc` restrictions can make `smaps_rollup` unreadable; total is then `null`.
  Raw readable subtotals and process coverage are not total memory. Do not add
  RSS and PSS together or compare an incomplete subtotal with a complete total.
- **GPU:** optional DRM `/proc/<pid>/fdinfo` busy-time counters follow the
  [kernel interface](https://docs.kernel.org/gpu/drm-usage-stats.html). Shared
  descriptors are deduplicated by driver/device/client identity. Counter
  regressions retain the prior high-water mark. Busy-nanosecond deltas divided
  by elapsed time yield equivalent per-engine usage across observed clients.
  `core_percent` can exceed 100% for engine groups and is not normalized by engine
  capacity. It does not measure clocks, power, total GPU utilization or GPU
  memory. Clients need two observations; report `covered_seconds` and access
  errors. Missing counters/permissions mean unavailable, **not zero load**.
- **Observer:** `monitor_cpu_seconds` is measured separately, not charged to GSR.
  Reading `/proc` consumes resources and affects the experiment. Use the same
  observer/interval and account for that overhead across comparisons.
- **Video:** FFprobe records streams, duration and resolution. For recordings up
  to 120 seconds it attempts decoded frame counting with a 60-second timeout;
  a counting failure is reported separately without discarding valid metadata.
  CFR/frame counts do not prove absence of duplicates, dropped content, stutter
  or audio drift. Inspect video quality and motion as well as counters. Short
  trials do not establish long-term stability.

## Equivalent GSR and OBS comparisons

A single-element native trial isolates an overlay delta against the **same GSR
engine**. It is not an end-to-end Trama-versus-OBS benchmark. To compare the
installed application, measure that actual runtime separately and include its
interface, engine, detector and helper processes consistently.

There is no automated OBS runner in these tools. Design and disclose an
equivalent OBS experiment before drawing comparative conclusions:

1. Replay the identical workload at the same desktop resolution and refresh.
   Match the effective captured region/canvas, output resolution, FPS, color
   format and SDR range; document different capture APIs when unavoidable.
2. Match the hardware encoder, codec, container and observable output quality.
   A similarly named quality preset in another application is not automatically
   equivalent. Disable preview if comparing against Trama's no-preview workflow,
   or report preview overhead as a separate condition.
3. Use the same assets, geometry, visibility and animation. Either disable audio
   and avatar detection everywhere or enable an equivalent workload everywhere;
   do not compare a silent single GIF with a microphone/avatar scene.
4. Apply the same warm-up, measurement duration, process-tree rules, sampling,
   observer overhead and PSS/GPU permission policy. Include the full relevant
   OBS process tree and disclose shared services omitted by both measurements.
5. Rotate/randomize order, repeat independent trials, preserve raw data and
   report variability, incomplete coverage and failures. Review matched videos
   and logs before interpreting resource deltas.

Publish conditions and evidence, not unsupported resource targets. Lower RSS,
CPU or one engine counter alone does not demonstrate better quality, smoothness,
energy use or overall performance.

## Instrument tests

```bash
python3 tests/test_measure.py
```

These tests exercise parsing, PID reuse, unavailable PSS, DRM counters,
FFprobe behavior and synthetic parent/child recording shutdown. They do not
capture the desktop, test a hardware GPU or produce benchmark results.
