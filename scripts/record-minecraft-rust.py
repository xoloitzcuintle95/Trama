#!/usr/bin/env python3
"""Prueba prolongada de Minecraft/desarrollo con GIF Rust y audio de GSR."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid
from measure import ROOT, trial
from rust_runtime import prepare, command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", type=Path, default=ROOT / "examples/assets/idle.gif")
    parser.add_argument("--seconds", type=int, default=600, help="Tiempo total, incluido calentamiento; default 600")
    parser.add_argument("--audio", action="store_true", help="Sonido del sistema, sin micrófono")
    args = parser.parse_args()
    if not 10 <= args.seconds <= 7200:
        parser.error("--seconds debe estar entre 10 y 7200")
    try:
        gsr, plugin, environment, report = prepare(args.media)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    folder = ROOT / "build/minecraft-rust" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    video = folder / "minecraft.mkv"
    report.update(seconds_requested=args.seconds, audio="default_output" if args.audio else None, result=None)
    summary = folder / "summary.json"
    summary.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Video: {video}\nCaptura TODO el monitor, GIF animado Rust, "
          f"audio del sistema: {'sí' if args.audio else 'no'}.\n"
          f"Cambia a Minecraft. Parada automática a los {args.seconds} s; Ctrl+C termina antes.\n"
          "CPU/memoria se muestrean cada segundo; el observador consume recursos aparte.", flush=True)
    result = trial("minecraft", command(gsr, video, plugin, args.audio), environment, folder, 5, args.seconds-5)
    report["result"] = result
    summary.write_text(json.dumps(report, indent=2) + "\n")
    if not result["completed"]:
        print(f"Prueba interrumpida/incompleta: {folder / 'minecraft.log'}. Archivos conservados.", file=sys.stderr)
        return 1
    print(f"Grabación guardada: {video}\nResumen: {summary}\n"
          "Revisa inicio, mitad y final: movimiento, GIF, sonido y sincronización.")
    if result["video"] is None:
        print("La comprobación de metadatos falló; revisa probe_error. No se borró el video.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
