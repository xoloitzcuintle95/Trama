# Reproducible CLI measurement

Development tools; generated results are not part of the project. Build the C
reference with `bash scripts/build-overlay.sh` for prototype comparison. For
Rust/GIF, use `scripts/measure-gif.py` with the same asset.

## Run

From a normal COSMIC terminal, without sudo or additional installations:

```sh
cd "$HOME/project-gsr-compositor"
python3 scripts/measure.py --media examples/assets/idle.gif \
  --workload "Escritorio quieto, mismas ventanas"
```

Keep windows unchanged and do not interact for roughly 70 seconds: first GSR
alone, then GSR with overlay. Each run has 5 seconds of warm-up excluded from the
summary and a requested 30-second measurement. Do not open OBS or another recorder.
This static scenario is only a baseline, not representative of games, video
playback or smoothness. A dynamic workload needs the same sequence replayed
from the same starting point in each run.

Both captures use KMS (`screen`), H.264 GPU without CPU fallback, 30 FPS CFR,
`very_high` and no audio. Only the second loads the plugin. Configured
`GSR_OVERLAY_X/Y/WIDTH` position/width is preserved and recorded. Failure stops
the comparison; partial results are not presented as success. Ctrl+C stops capture
and retains collected data. The tool sends SIGINT to GSR to finalize MP4; after
15 seconds without exit it forces termination and marks the run incomplete.

The printed `build/measurements/<UTC-date-id>/` folder contains:

- `baseline.mp4`, `overlay.mp4`: videos; previous captures are not overwritten.
- `baseline.log`, `overlay.log`: full GSR output for capture, driver, encoder and errors.
- `*.jsonl`: raw samples including warm-up, processes and coverage.
- `*.csv`: CPU/memory samples for the measured period.
- `summary.json`: interval-duration-weighted averages, sampled maxima, commands,
  plugin/image hashes, kernel, GSR version and FFprobe data.

Nominal sampling is 1 second. An interval crossing the warm-up boundary is fully
excluded, so summarized time may be under 30 seconds. Actual coverage is
`sampled_seconds`; it is not assumed exact.

To reduce ordering/temperature bias, repeat later in reverse order:

```sh
python3 scripts/measure.py --media examples/assets/idle.gif \
  --workload "Escritorio quieto, mismas ventanas" --order overlay-first
```

## Interpret carefully

- **CPU:** summed utime+stime for observed processes, excluding waited-child
  accounting to avoid double counting. 100% equals one full core and values can
  exceed 100%. This is not a percentage of the whole CPU.
- **Processes:** GSR starts in its own session. Session processes and descendants
  are tracked with PID+start-time identity to follow detached children. Processes
  born/dying between samples, or detached before observation, can escape sampling.
  Names/PIDs and access errors are retained. Existing external services (COSMIC,
  audio server) are not included; this is not whole-system accounting.
- **RSS:** sum of resident memory, potentially counting shared pages repeatedly.
  Maxima are observed at one-second samples, not absolute peaks. MiB = 2^20 bytes.
- **PSS:** apportions shared pages among processes. Total PSS is published only
  when every process was readable in every sample. Capabilities on a helper may
  block `smaps_rollup`; total is then `null`, with readable subtotal and coverage
  in raw data. Do not interpret that subtotal as total memory or add RSS to PSS.
- **Optional GPU:** reads `/proc/<pid>/fdinfo` following the
  [official DRM specification](https://docs.kernel.org/gpu/drm-usage-stats.html).
  Shared descriptors are deduplicated by driver/device/client-id, retaining the
  previous maximum if a counter temporarily decreases. Busy-nanosecond deltas
  divided by elapsed time are calculated per engine/device across observed
  clients. `core_percent` represents equivalent engine usage, can exceed 100%
  for groups of engines and is not normalized by capacity. It does not measure
  frequency, power, total GPU load or GPU memory. New clients need two observations;
  coverage is reported in seconds. Missing permissions/counters mean unavailable,
  never assumed zero usage.
- **Observer:** its CPU is recorded separately as `monitor_cpu_seconds`, not added
  to GSR. Reading `/proc` affects the machine and must be considered in comparisons;
  observation is not free.
- **Video:** FFprobe records duration/resolution. For files up to 120 seconds it
  also attempts decoded frame counting with a 60-second timeout. Counting failure
  does not invalidate metadata and is reported separately. CFR frame count does
  not prove there were no duplicates/stutters. Review both videos and logs; a
  35-second test does not establish long-term stability.

Do not infer an OBS advantage or achievement of 150 MB from this initial
comparison. Before expanding functionality, review actual data, verify coverage
and design an equivalent OBS workload/configuration.

## Instrument checks

```sh
python3 tests/test_measure.py
```

Seven tests cover quick inspection of long videos, metadata retention when frame
counting times out, stat parsing with unusual names, PID reuse, missing PSS,
regressing DRM counters and client identity; an integrated test uses a CPU-consuming
parent/child, SIGINT shutdown and synthetic video analyzed by FFprobe. They do
not capture the desktop, test a GPU or produce GSR benchmark results.
