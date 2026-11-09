#!/usr/bin/env python3
"""Compara GSR solo con el plugin Rust estático; tres pares con orden alternado."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import uuid
from measure import ROOT, trial


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=ROOT / "build/rust-fixtures/idle-static.png")
    parser.add_argument("--workload", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=30, help="Periodo medido, además de 5 s de calentamiento")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10 or not 5 <= args.seconds <= 600:
        parser.error("--repeats: 1..10; --seconds: 5..600")
    plugin = ROOT / "build/overlay-rust.so"
    manifest = ROOT / "build/overlay-rust.build.json"
    gsr = Path("/usr/local/bin/gpu-screen-recorder")
    image = args.image.resolve()
    checker = ROOT / "build/rust-target/release/element-check"
    if not all(p.is_file() for p in (plugin, manifest, gsr, image, checker)):
        parser.error("Faltan archivos: ejecuta build-rust-overlay.sh y prepare-rust-example.py, o indica --image")
    with image.open("rb") as source:
        if source.read(8) != b"\x89PNG\r\n\x1a\n":
            parser.error("Esta comparación es PNG estático; usa scripts/measure-gif.py para GIF animado")
    build = json.loads(manifest.read_text())
    if build["test_hooks"] or sha(plugin) != build["plugin_sha256"] or sha(gsr) != build["gsr_sha256"]:
        parser.error("Plugin o GSR no coincide con el build/ABI verificado; revisa y recompila")
    check = subprocess.run([str(checker), str(image)], capture_output=True, text=True)
    if check.returncode:
        parser.error(check.stderr.strip())
    if not Path("/dev/dri").is_dir():
        parser.error("Sin /dev/dri: ejecuta esta prueba desde tu terminal en COSMIC, sin sudo")
    identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    folder = ROOT / "build/measurements-rust" / identifier
    folder.mkdir(parents=True)
    report = {"workload": args.workload, "seconds_requested": args.seconds, "warmup": 5,
              "repeats_requested": args.repeats, "image": str(image), "image_sha256": sha(image),
              "build": build, "kernel": platform.release(), "logical_cpus": os.cpu_count(),
              "os_release": Path("/etc/os-release").read_text(), "trials": {}, "pairs": []}
    report["element"] = json.loads(check.stdout)["element"]
    report["gsr_version"] = subprocess.check_output([str(gsr), "--version"], text=True).strip()
    environment = os.environ.copy()
    environment["GSR_RUST_IMAGE"] = str(image)
    environment.pop("GSR_RUST_TEST_PANIC", None)
    report["overlay_settings"] = {k: environment.get(k, v) for k, v in
        (("GSR_OVERLAY_X", "32"), ("GSR_OVERLAY_Y", "32"), ("GSR_OVERLAY_WIDTH", None),
         ("GSR_OVERLAY_HEIGHT", None), ("GSR_OVERLAY_KEEP_ASPECT", "true"), ("GSR_OVERLAY_VISIBLE", "true"))}
    def save():
        (folder / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{check.stdout.strip()}\nResultados: {folder}\n"
          f"{args.repeats} pares, aproximadamente {args.repeats * 2 * (args.seconds + 5)} s de captura.\n"
          "Mantén la misma carga en pantalla. El PNG es estático, no un GIF animado.", flush=True)
    save()
    for repeat in range(args.repeats):
        order = ["baseline", "rust"] if repeat % 2 == 0 else ["rust", "baseline"]
        pair = {}
        for kind in order:
            name = f"{repeat + 1:02d}-{kind}"
            command = [str(gsr), "-w", "screen", "-f", "30", "-fm", "cfr", "-k", "h264",
                       "-q", "very_high", "-encoder", "gpu", "-fallback-cpu-encoding", "no"]
            if kind == "rust":
                command += ["-p", str(plugin)]
            command += ["-o", str(folder / (name + ".mkv"))]
            result = trial(name, command, environment, folder, 5, args.seconds)
            report["trials"][name] = result
            save()
            if not result["completed"] or result["video"] is None:
                print(f"Prueba incompleta; conserva los archivos y revisa {folder / (name + '.log')}", file=sys.stderr)
                return 1
            pair[kind] = result
            print(f"{name}: CPU {result['cpu_percent_one_core_mean']:.2f}% de un núcleo; "
                  f"RSS máximo {result['rss_bytes_sum_peak'] / 2**20:.2f} MiB", flush=True)
        delta = {key: pair["rust"][key] - pair["baseline"][key] for key in
                 ("cpu_percent_one_core_mean", "rss_bytes_sum_mean", "rss_bytes_sum_peak")}
        report["pairs"].append({"order": order, "delta_rust_minus_baseline": delta})
        save()
    report["delta_median"] = {key: statistics.median(p["delta_rust_minus_baseline"][key]
                              for p in report["pairs"]) for key in delta}
    save()
    print(f"Comparación terminada: {folder / 'summary.json'}\n"
          "Revisa también imagen y fluidez; CPU/RSS no certifican paridad ni ventaja frente a OBS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
