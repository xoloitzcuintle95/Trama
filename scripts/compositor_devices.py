"""Probe real GSR capture options and PulseAudio/PipeWire sources."""
import json
import os
import re
import select
import shutil
import subprocess
from pathlib import Path
import time


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=12)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"{args[0]}: {error}") from error
    if result.returncode:
        raise ValueError(f"{' '.join(args)}: {result.stderr.strip() or 'falló la consulta'}")
    return result.stdout


class Devices:
    def __init__(self, gsr=None):
        # A packaged engine is private to Trama; never shadow the system's GSR.
        bundled = Path(__file__).resolve().parent.parent/"engine/gpu-screen-recorder"
        self.gsr = gsr or (str(bundled) if bundled.parent.is_dir() else shutil.which("gpu-screen-recorder"))
        if not self.gsr:
            raise ValueError("Falta gpu-screen-recorder en PATH")

    def capabilities(self):
        sections = {}
        section = ""
        for line in run([self.gsr,"--info"]).splitlines():
            if line.startswith("section="):
                section = line[8:]
                sections.setdefault(section,[])
            else:
                sections.setdefault(section,[]).append(line)
        if "h264" not in sections.get("video_codecs",[]):
            raise ValueError("codificación: GSR no anuncia H.264 GPU en este equipo")
        if "mkv" not in sections.get("containers",[]):
            raise ValueError("salida: GSR no anuncia contenedor MKV")

    def screens(self):
        output = run([self.gsr,"--list-capture-options"])
        screens = {}
        for line in output.splitlines():
            parts = line.split("|")
            if len(parts)==2 and re.fullmatch(r"\d+x\d+",parts[1]):
                screens[parts[0]] = tuple(map(int, parts[1].split("x")))
        if not screens:
            raise ValueError("pantalla: GSR no anunció monitores; ejecuta en tu sesión gráfica COSMIC, sin sudo")
        return screens

    def audio(self):
        gsr = dict(line.split("|",1) for line in run([self.gsr,"--list-audio-devices"]).splitlines() if "|" in line)
        sources = json.loads(run(["pactl","--format=json","list","sources"]))
        inputs = {}
        for source in sources:
            name = source["name"]
            monitor = source.get("monitor_of_sink")
            if not name.endswith(".monitor") and monitor in (None,4294967295,"4294967295") and name in gsr:
                inputs[name] = source.get("description",name)
        return gsr, inputs

    def resolve_mic(self, selected, audio=None):
        if not selected:
            return None
        gsr, inputs = audio if audio is not None else self.audio()
        if selected == "default_input":
            selected = run(["pactl","get-default-source"]).strip()
        if selected not in inputs or selected not in gsr:
            raise ValueError(f"recording.microphone: '{selected}' no está disponible como entrada; elige otra en el menú de micrófono")
        return selected


def probe_microphone(source):
    if not shutil.which("parec"):
        raise ValueError("micrófono: falta parec (paquete pulseaudio-utils)")
    with subprocess.Popen(["parec","--raw","--format=float32le","--rate=16000","--channels=1",
                           "--latency-msec=30","--device",source],stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE) as process:
        try:
            end = time.monotonic()+4
            remaining = 1280
            while remaining and time.monotonic()<end:
                ready,_,_ = select.select([process.stdout],[],[],max(0,end-time.monotonic()))
                if not ready:
                    break
                chunk = os.read(process.stdout.fileno(),remaining)
                if not chunk:
                    break
                remaining -= len(chunk)
            if remaining:
                raise ValueError(f"recording.microphone: no se pudo capturar audio de '{source}'; revisa permisos, conexión y pactl")
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
