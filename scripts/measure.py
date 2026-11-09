#!/usr/bin/env python3
"""Compara GSR solo y con overlay; sin sudo ni dependencias Python adicionales."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
TICKS = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")


def process_stat(text):
    pid, name = text.split(" (", 1)
    name, tail = name.rsplit(") ", 1)
    fields = tail.split()
    return {"pid": int(pid), "name": name, "ppid": int(fields[1]),
            "group": int(fields[2]), "session": int(fields[3]),
            "ticks": int(fields[11]) + int(fields[12]),
            "start": int(fields[19]), "rss_bytes": max(0, int(fields[21])) * PAGE}


def drm_client(text):
    fields = dict(line.split(":", 1) for line in text.splitlines() if ":" in line)
    fields = {k: v.strip() for k, v in fields.items()}
    if "drm-client-id" not in fields or "drm-driver" not in fields:
        return None
    identity = "/".join(fields.get(k, "") for k in ("drm-driver", "drm-pdev", "drm-client-id"))
    engines = {}
    for key, value in fields.items():
        if key.startswith("drm-engine-") and not key.startswith("drm-engine-capacity-"):
            parts = value.split()
            if len(parts) == 2 and parts[1] == "ns" and parts[0].isdigit():
                engines[key.removeprefix("drm-engine-")] = int(parts[0])
    return identity, engines


def snapshot(session, known):
    processes = {}
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            p = process_stat(path.read_text())
            processes[p["pid"]] = p
        except (OSError, ValueError, IndexError):
            continue
    selected = {pid for pid, p in processes.items()
                if p["session"] == session or (pid, p["start"]) in known}
    while True:
        children = {pid for pid, p in processes.items() if p["ppid"] in selected}
        if children <= selected:
            break
        selected |= children
    clients = {}
    for pid in selected:
        p = processes[pid]
        known.add((pid, p["start"]))
        p["pss_bytes"] = None
        try:
            for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
                if line.startswith("Pss:"):
                    p["pss_bytes"] = int(line.split()[1]) * 1024
        except (OSError, ValueError):
            pass
        p["fdinfo_errors"] = 0
        try:
            paths = list(Path(f"/proc/{pid}/fdinfo").iterdir())
        except OSError:
            paths = []
            p["fdinfo_errors"] += 1
        for path in paths:
            try:
                client = drm_client(path.read_text())
                if client:
                    identity, engines = client
                    # Shared/duplicated descriptors represent one DRM client.
                    values = clients.setdefault(identity, {})
                    for engine, ns in engines.items():
                        values[engine] = max(values.get(engine, 0), ns)
            except OSError:
                p["fdinfo_errors"] += 1
    return {pid: processes[pid] for pid in selected}, clients


def sample(previous, current, gpu_previous, gpu, dt):
    cpu_ticks = 0
    for pid, p in current.items():
        old = previous.get(pid)
        # New processes in this recording session started within this interval.
        before = old["ticks"] if old and old["start"] == p["start"] else 0
        cpu_ticks += max(0, p["ticks"] - before)
    engines = {}
    for client, values in gpu.items():
        for engine, ns in values.items():
            key = client + "/" + engine
            if key in gpu_previous:
                delta = max(0, ns - gpu_previous[key])
                engine_key = client.rsplit("/", 1)[0] + "/" + engine
                engines[engine_key] = engines.get(engine_key, 0) + delta / (dt * 1e7)
            # DRM counters may temporarily regress: retain their high-water mark.
            gpu_previous[key] = max(gpu_previous.get(key, 0), ns)
    readable = [p["pss_bytes"] for p in current.values() if p["pss_bytes"] is not None]
    return {"interval_seconds": dt, "cpu_percent_one_core": cpu_ticks / TICKS / dt * 100,
            "rss_bytes_sum": sum(p["rss_bytes"] for p in current.values()),
            "pss_bytes_sum": sum(readable) if len(readable) == len(current) else None,
            "pss_readable_bytes": sum(readable), "pss_readable_processes": len(readable),
            "process_count": len(current), "gpu_engine_core_percent": engines or None,
            "fdinfo_errors": sum(p["fdinfo_errors"] for p in current.values())}


def summarize(rows):
    total = sum(r["interval_seconds"] for r in rows)
    result = {"samples": len(rows), "sampled_seconds": total}
    for key in ("cpu_percent_one_core", "rss_bytes_sum", "pss_bytes_sum"):
        values = [r[key] for r in rows]
        complete = bool(rows) and all(v is not None for v in values)
        result[key + "_mean"] = (sum(r[key] * r["interval_seconds"] for r in rows) / total
                                if complete else None)
        result[key + "_peak"] = max(values) if complete else None
    result["gpu"] = {}
    keys = {k for r in rows for k in (r["gpu_engine_core_percent"] or {})}
    for key in sorted(keys):
        available = [r for r in rows if key in (r["gpu_engine_core_percent"] or {})]
        seconds = sum(r["interval_seconds"] for r in available)
        result["gpu"][key] = {
            "core_percent_mean": sum(r["gpu_engine_core_percent"][key] * r["interval_seconds"]
                                     for r in available) / seconds,
            "covered_seconds": seconds}
    return result


def stop(process):
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return False
    return True


def probe_video(path):
    """Keep metadata even if a full frame count is too expensive or fails."""
    result = {"video": None, "probe_error": "", "frame_count_status": "not_run"}
    entries = ("stream=codec_name,codec_type,width,height,avg_frame_rate,sample_rate,channels:"
               "format=duration,size,bit_rate")
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries,
                                "-of", "json", str(path)],
                               capture_output=True, text=True, timeout=30)
        result["probe_error"] = probe.stderr
        if probe.returncode != 0:
            return result
        result["video"] = json.loads(probe.stdout)
        duration = float(result["video"].get("format", {}).get("duration", "inf"))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        result["probe_error"] = str(error)
        return result
    if duration > 120:
        result["frame_count_status"] = "skipped_long_recording"
        return result
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
            entries.replace(":format", ",nb_read_frames:format"), "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60)
        if probe.returncode != 0:
            result.update(frame_count_status="failed", frame_count_error=probe.stderr)
        else:
            result.update(video=json.loads(probe.stdout), frame_count_status="counted")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        result.update(frame_count_status="failed", frame_count_error=str(error))
    return result


def trial(name, command, environment, folder, warmup, seconds):
    known, gpu_previous, rows = set(), {}, []
    start = time.monotonic()
    monitor_cpu = time.process_time()
    print(f"{name}: {warmup:g} s de calentamiento + {seconds:g} s de medición", flush=True)
    with (folder / f"{name}.log").open("w") as log, (folder / f"{name}.jsonl").open("w") as raw:
        process = subprocess.Popen(command, env=environment, stdout=log, stderr=log,
                                   start_new_session=True)
        graceful = True
        interrupted = False
        try:
            previous, gpu = snapshot(process.pid, known)
            previous_time = time.monotonic()
            sample(previous, previous, gpu_previous, gpu, 1)
            while process.poll() is None and time.monotonic() - start < warmup + seconds:
                time.sleep(min(1, max(0, warmup + seconds - (time.monotonic() - start))))
                if process.poll() is not None:
                    break
                current, gpu = snapshot(process.pid, known)
                if not current:
                    break
                now = time.monotonic()
                row = sample(previous, current, gpu_previous, gpu, now - previous_time)
                row["elapsed_seconds"] = now - start
                row["measured"] = previous_time - start >= warmup
                row["processes"] = list(current.values())
                raw.write(json.dumps(row) + "\n")
                raw.flush()
                if row["measured"]:
                    rows.append(row)
                previous, previous_time = current, now
        except KeyboardInterrupt:
            interrupted = True
        finally:
            reached_duration = time.monotonic() - start >= warmup + seconds - 0.05
            graceful = stop(process)
    result = summarize(rows)
    result.update(command=command, returncode=process.returncode, graceful_stop=graceful,
                  completed=bool(rows) and reached_duration and not interrupted and graceful and process.returncode == 0,
                  monitor_cpu_seconds=time.process_time() - monitor_cpu,
                  observed_processes=sorted(known))
    fields = ["elapsed_seconds", "interval_seconds", "cpu_percent_one_core", "rss_bytes_sum",
              "pss_bytes_sum", "pss_readable_bytes", "pss_readable_processes", "process_count"]
    with (folder / f"{name}.csv").open("w") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    result.update(probe_video(command[-1]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", type=Path, required=True)
    parser.add_argument("--workload", required=True, help="Describe qué permanece en pantalla durante ambas pruebas")
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--warmup", type=float, default=5)
    parser.add_argument("--order", choices=("baseline-first", "overlay-first"), default="baseline-first")
    args = parser.parse_args()
    if not (1 <= args.seconds <= 3600 and 0 <= args.warmup <= 300):
        parser.error("--seconds: 1..3600; --warmup: 0..300")
    media = args.media.resolve(strict=True)
    plugin = ROOT / "build/overlay.so"
    gsr = "/usr/local/bin/gpu-screen-recorder"
    if not plugin.is_file() or not os.access(gsr, os.X_OK):
        parser.error("Falta compilar el plugin o instalar GSR (ver README.md)")
    if not Path("/dev/dri").is_dir():
        parser.error("No hay /dev/dri accesible. Ejecuta la prueba desde tu sesión gráfica.")
    identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    folder = ROOT / "build/measurements" / identifier
    folder.mkdir(parents=True)
    report = {"workload": args.workload, "seconds_requested": args.seconds, "warmup": args.warmup,
              "order": args.order, "kernel": platform.release(), "logical_cpus": os.cpu_count(),
              "media": str(media), "media_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
              "plugin_sha256": hashlib.sha256(plugin.read_bytes()).hexdigest(), "trials": {}}
    report["gsr_version"] = subprocess.check_output([gsr, "--version"], text=True).strip()
    report["os_release"] = Path("/etc/os-release").read_text()
    environment = os.environ.copy()
    environment["GSR_OVERLAY_FILE"] = str(media)
    report["overlay_settings"] = {key: environment.get(key, str(value)) for key, value in
                                  (("GSR_OVERLAY_X", 32), ("GSR_OVERLAY_Y", 32), ("GSR_OVERLAY_WIDTH", 320))}
    names = ["baseline", "overlay"] if args.order == "baseline-first" else ["overlay", "baseline"]
    print(f"Resultados: {folder}\nMantén la misma carga en pantalla. Ctrl+C interrumpe y guarda resultados parciales.", flush=True)
    for name in names:
        command = [gsr, "-w", "screen", "-f", "30", "-fm", "cfr", "-k", "h264",
                   "-q", "very_high", "-encoder", "gpu", "-fallback-cpu-encoding", "no"]
        if name == "overlay":
            command += ["-p", str(plugin)]
        command += ["-o", str(folder / f"{name}.mp4")]
        result = trial(name, command, environment, folder, args.warmup, args.seconds)
        report["trials"][name] = result
        (folder / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
        if not result["completed"] or result["video"] is None:
            print(f"Prueba {name} incompleta: revisa {folder / (name + '.log')}", file=sys.stderr)
            return 1
        cpu = result["cpu_percent_one_core_mean"]
        rss = result["rss_bytes_sum_peak"]
        pss = result["pss_bytes_sum_peak"]
        print(f"{name}: CPU media {cpu:.2f}% de un núcleo; RSS máximo sumado {rss / 2**20:.1f} MiB; "
              + (f"PSS máximo {pss / 2**20:.1f} MiB" if pss is not None else "PSS total no disponible"), flush=True)
    print("Completado. Revisa también ambos videos: estos contadores no certifican fluidez ni calidad visual.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
