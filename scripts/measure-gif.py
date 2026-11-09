#!/usr/bin/env python3
"""Compara GSR solo, referencia C y Rust con el mismo GIF, en orden rotado."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import uuid
from measure import ROOT, trial
from rust_runtime import prepare, command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", type=Path, default=ROOT / "examples/assets/idle.gif")
    parser.add_argument("--workload", required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 600 or not 1 <= args.repeats <= 10:
        parser.error("--seconds: 5..600; --repeats: 1..10")
    try:
        gsr, plugin, environment, report = prepare(args.media, require_c=True)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    folder = ROOT / "build/measurements-gif" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    report.update(workload=args.workload, seconds_requested=args.seconds, warmup=5,
                  repeats_requested=args.repeats, audio=None, trials={}, comparisons=[])
    def save():
        (folder / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Resultados: {folder}\n{args.repeats * 3 * (args.seconds + 5)} s de captura aprox.; "
          "mantén las mismas ventanas y carga. Ctrl+C conserva lo recogido.", flush=True)
    orders = [("baseline", "c", "rust"), ("rust", "baseline", "c"), ("c", "rust", "baseline")]
    metrics = ("cpu_percent_one_core_mean", "rss_bytes_sum_mean", "rss_bytes_sum_peak")
    save()
    for repeat in range(args.repeats):
        results = {}
        order = orders[repeat % 3]
        for kind in order:
            name = f"{repeat+1:02d}-{kind}"
            chosen = None if kind == "baseline" else ROOT / "build/overlay.so" if kind == "c" else plugin
            result = trial(name, command(gsr, folder / f"{name}.mkv", chosen), environment, folder, 5, args.seconds)
            report["trials"][name] = result
            save()
            if not result["completed"] or result["video"] is None:
                print(f"Prueba incompleta: revisa {folder / (name + '.log')}", file=sys.stderr)
                return 1
            results[kind] = result
            print(f"{name}: CPU {result['cpu_percent_one_core_mean']:.2f}% de un núcleo; "
                  f"RSS máximo {result['rss_bytes_sum_peak']/2**20:.2f} MiB", flush=True)
        differences = {label: {key: results[left][key] - results[right][key] for key in metrics}
                       for label, left, right in [("rust_minus_baseline", "rust", "baseline"),
                                                  ("c_minus_baseline", "c", "baseline"),
                                                  ("rust_minus_c", "rust", "c")]}
        report["comparisons"].append({"order": order, **differences})
        save()
    report["delta_medians"] = {label: {key: statistics.median(row[label][key] for row in report["comparisons"])
                              for key in metrics} for label in differences}
    save()
    print(f"Terminado: {folder / 'summary.json'}\nRevisa también videos; CFR y memoria no certifican fluidez.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
