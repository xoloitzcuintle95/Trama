#!/usr/bin/env python3
"""Graba el monitor durante 10 minutos y guarda métricas, log y video MKV."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

from measure import ROOT, trial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", type=Path, default=ROOT / "examples/assets/idle.gif")
    parser.add_argument("--seconds", type=int, default=600, help="Duración total solicitada (predeterminado: 600)")
    parser.add_argument("--audio", action="store_true", help="Incluir sonido del sistema, sin micrófono")
    parser.add_argument("--no-overlay", action="store_true", help="Grabar GSR solo como referencia")
    args = parser.parse_args()
    if not 10 <= args.seconds <= 3600:
        parser.error("--seconds debe estar entre 10 y 3600")
    gsr = "/usr/local/bin/gpu-screen-recorder"
    plugin = ROOT / "build/overlay.so"
    if not os.access(gsr, os.X_OK):
        parser.error("Falta instalar GSR (ver README.md)")
    if not Path("/dev/dri").is_dir():
        parser.error("Ejecuta este script desde tu sesión gráfica con acceso a /dev/dri")
    media = args.media.resolve()
    if not args.no_overlay and (not media.is_file() or not plugin.is_file()):
        parser.error("Falta la imagen o build/overlay.so")
    identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    folder = ROOT / "build/minecraft" / identifier
    folder.mkdir(parents=True)
    command = [gsr, "-w", "screen", "-f", "30", "-fm", "cfr", "-k", "h264",
               "-q", "very_high", "-encoder", "gpu", "-fallback-cpu-encoding", "no"]
    environment = os.environ.copy()
    if not args.no_overlay:
        environment["GSR_OVERLAY_FILE"] = str(media)
        command += ["-p", str(plugin)]
    if args.audio:
        command += ["-a", "default_output"]
    video = folder / "minecraft.mkv"
    command += ["-o", str(video)]
    report = {"seconds_requested": args.seconds, "overlay": not args.no_overlay,
              "audio": "default_output" if args.audio else None,
              "overlay_settings": {key: environment.get(key, str(value)) for key, value in
                                   (("GSR_OVERLAY_X", 32), ("GSR_OVERLAY_Y", 32), ("GSR_OVERLAY_WIDTH", 320))}}
    if not args.no_overlay:
        report.update(media=str(media), media_sha256=hashlib.sha256(media.read_bytes()).hexdigest(),
                      plugin_sha256=hashlib.sha256(plugin.read_bytes()).hexdigest())
    print(f"Video: {video}\nLog y métricas: {folder}\n"
          f"Captura de todo el monitor, 30 FPS; audio del sistema: {'sí' if args.audio else 'no'}.\n"
          "Cambia ahora a Minecraft. Se detiene automáticamente; Ctrl+C termina antes.\n"
          "Se muestrean CPU y memoria cada segundo; el coste del observador se registra aparte.", flush=True)
    # Total launch time: 600 s by default; discard first 5 s from resource summary.
    result = trial("minecraft", command, environment, folder, 5, args.seconds - 5)
    report["result"] = result
    (folder / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    if not result["completed"]:
        print(f"Grabación interrumpida o incompleta. Revisa {folder / 'minecraft.log'}; "
              "se conservaron los archivos y las muestras.", file=sys.stderr)
        return 1
    print(f"Grabación terminada: {video}\nResumen: {folder / 'summary.json'}")
    if result["video"] is None:
        print("FFprobe no pudo completar la comprobación del video; consulta probe_error en summary.json.")
    else:
        print("Revisa visualmente fluidez, imagen y audio; las métricas no los certifican.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
