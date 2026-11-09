#!/usr/bin/env python3
"""Graba con un elemento PNG/JPG/GIF configurable; no escenas ni control en vivo."""
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
    parser.add_argument("--media", type=Path, required=True, help="PNG/JPG estático o GIF animado")
    parser.add_argument("--x", type=int, help="Píxeles desde izquierda; admite negativos")
    parser.add_argument("--y", type=int, help="Píxeles desde arriba; admite negativos")
    parser.add_argument("--width", type=int, help="Ancho o ancho de caja si también se indica alto")
    parser.add_argument("--height", type=int, help="Alto o alto de caja si también se indica ancho")
    aspect = parser.add_mutually_exclusive_group()
    aspect.add_argument("--stretch", action="store_true", help="Deformar explícitamente; requiere ancho y alto")
    aspect.add_argument("--keep-aspect", action="store_true", help="Conservar proporción (predeterminado)")
    visibility = parser.add_mutually_exclusive_group()
    visibility.add_argument("--hidden", action="store_true", help="Conservar el recurso cargado sin dibujarlo")
    visibility.add_argument("--visible", action="store_true", help="Dibujar el recurso (predeterminado)")
    parser.add_argument("--seconds", type=int, default=30, help="Duración total de captura, default 30")
    parser.add_argument("--audio", action="store_true", help="Audio del sistema, sin micrófono")
    parser.add_argument("--check", action="store_true", help="Validar y mostrar geometría; no capturar")
    args = parser.parse_args()
    if not 10 <= args.seconds <= 7200:
        parser.error("--seconds: 10..7200")
    overrides = {f"GSR_OVERLAY_{name.upper()}": str(getattr(args,name))
                 for name in ("x","y","width","height") if getattr(args,name) is not None}
    if args.stretch or args.keep_aspect:
        overrides["GSR_OVERLAY_KEEP_ASPECT"] = "false" if args.stretch else "true"
    if args.hidden or args.visible:
        overrides["GSR_OVERLAY_VISIBLE"] = "false" if args.hidden else "true"
    try:
        gsr, plugin, environment, report = prepare(args.media, require_gif=False,
            overrides=overrides, check_device=not args.check)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report["element"], ensure_ascii=False), flush=True)
    if args.check:
        return 0
    folder = ROOT / "build/recordings-element" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    video = folder / "recording.mkv"
    report.update(seconds_requested=args.seconds, audio="default_output" if args.audio else None, result=None)
    summary = folder / "summary.json"
    summary.write_text(json.dumps(report,indent=2)+"\n")
    print(f"Video: {video}\nCaptura el monitor completo durante {args.seconds} s. "
          "Ctrl+C termina antes y conserva lo recogido.", flush=True)
    report["result"] = trial("recording", command(gsr,video,plugin,args.audio), environment,
                             folder,5,args.seconds-5)
    summary.write_text(json.dumps(report,indent=2)+"\n")
    if not report["result"]["completed"] or report["result"]["video"] is None:
        print(f"Captura o comprobación incompleta: revisa {summary}",file=sys.stderr)
        return 1
    print(f"Guardado: {video}\nResumen: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
