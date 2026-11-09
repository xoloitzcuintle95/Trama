#!/usr/bin/env python3
"""Compositor GSR: menú de texto, perfiles TOML y grabación sin menú."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from compositor_profile import load_profile, new_profile, normalize, resolved, save_profile
from compositor_devices import Devices, probe_microphone, run
from rust_runtime import ROOT, sha
from measure import stop


def verified_build(gsr):
    plugin = ROOT/"build/overlay-rust.so"
    manifest = ROOT/"build/overlay-rust.build.json"
    checker = ROOT/"build/rust-target/release/scene-check"
    if not all(p.is_file() for p in (plugin, manifest, checker)):
        raise ValueError("build: ejecuta bash scripts/build-rust-overlay.sh")
    build = json.loads(manifest.read_text())
    if build["test_hooks"] or sha(plugin)!=build["plugin_sha256"] or sha(Path(gsr))!=build["gsr_sha256"]:
        raise ValueError("build: GSR/plugin difiere de la ABI verificada; recompila y revisa la versión")
    # Packaged builds also bind the private helper and validator to this release.
    for key,path in (("gsr_helper_sha256",Path(gsr).parent/"gsr-kms-server"),
                     ("scene_checker_sha256",checker)):
        if key in build and (not path.is_file() or sha(path)!=build[key]):
            raise ValueError("build: helper/checker difiere del paquete verificado")
    return plugin, checker, build


def scene_manifest(profile, microphone):
    return {"microphone":microphone,"layers":[{k:v for k,v in layer.items() if k!="kind"} for layer in profile["layers"]]}


def output_path(profile):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return Path(profile["recording"]["output"].replace("{timestamp}",timestamp))


def inspect_scene(profile, microphone=None):
    """Use the production Rust loader without opening capture/audio or GL."""
    checker = ROOT/"build/rust-target/release/scene-check"
    manifest = scene_manifest(profile, microphone)
    with tempfile.TemporaryDirectory(prefix="gsr-scene-check-") as temporary:
        source = Path(temporary)/"scene.json"
        source.write_text(json.dumps(manifest))
        return json.loads(run([str(checker),str(source)]))


def validate(profile, devices=None, assets_only=False):
    """No recording. Full preload via the same Rust loader as plugin init."""
    profile = normalize(profile,profile["_base"])
    devices = devices or Devices()
    plugin, checker, build = verified_build(devices.gsr)
    for index,layer in enumerate(profile["layers"],1):
        for key in ("path","idle","talking"):
            if key in layer and not Path(layer[key]).is_file():
                raise ValueError(f"layers[{index}].{key}: no existe un archivo regular: {layer[key]}")
    recording = profile["recording"]
    microphone = recording["microphone"] or None
    dimensions = None
    if not assets_only:
        devices.capabilities()
        screens = devices.screens()
        screen = recording["screen"]
        if screen=="screen":  # Legacy scripts used GSR's full-screen alias.
            if len(screens)!=1:
                raise ValueError("recording.screen: perfil antiguo 'screen' ambiguo; elige un monitor explícito")
            screen = next(iter(screens))
            recording["screen"] = screen
        if screen not in screens:
            raise ValueError(f"recording.screen: '{screen}' no disponible; elige entre {', '.join(screens)}")
        dimensions = screens[screen]
        if recording["game_audio"] or microphone:
            audio = devices.audio()
            if recording["game_audio"] and "default_output" not in audio[0]:
                raise ValueError("recording.game_audio: GSR no anuncia default_output")
            microphone = devices.resolve_mic(recording["microphone"],audio)
        if microphone:
            probe_microphone(microphone)
    manifest = scene_manifest(profile,microphone)
    effective = inspect_scene(profile,microphone)
    output = output_path(profile)
    if output.exists():
        raise ValueError(f"recording.output: ya existe {output}; elige otro archivo o usa {{timestamp}}")
    parent = output.parent
    while not parent.exists() and parent!=parent.parent:
        parent = parent.parent
    if not parent.is_dir() or not os.access(parent,os.W_OK):
        raise ValueError(f"recording.output: carpeta no escribible {parent}")
    return {"profile":profile,"manifest":manifest,"effective":effective,"output":output,
            "plugin":plugin,"build":build,"gsr":devices.gsr,"dimensions":dimensions,"assets_only":assets_only}


def summary(prepared):
    recording = prepared["profile"]["recording"]
    print(f"Pantalla: {recording['screen'] or '(sin elegir)'}; resolución: {prepared['dimensions'] or '(sin consultar)'}; {recording['fps']} FPS")
    print(f"Micrófono: {prepared['manifest']['microphone'] or '(desactivado)'}; juego/sistema: {'sí' if recording['game_audio'] else 'no'}")
    for i,layer in enumerate(prepared["effective"]["layers"],1):
        print(f"  {i}. {layer['name']} ({'avatar' if layer['avatar'] else 'gráfico'}): "
              f"X/Y {layer['x']:g}/{layer['y']:g}, {layer['width']:g}×{layer['height']:g}, {'visible' if layer['visible'] else 'oculto'}")
        source = prepared["profile"]["layers"][i-1]
        if layer["avatar"]:
            print(f"     Reposo: {source['idle']} | habla: {source['talking']}")
            print(f"     Umbral RMS: {source['threshold']}; espera: {source['release_ms']} ms")
        else:
            print(f"     {source['path']}")
    print(f"Precarga RGBA: {prepared['effective']['rgba_bytes']/1024**2:.2f} MiB; orden de abajo hacia arriba")
    print(f"Salida: {prepared['output']}")
    if prepared["assets_only"]:
        print("SOLO RECURSOS: pantallas, audio y captura no comprobados.")


def recording_command(prepared):
    recording = prepared["profile"]["recording"]
    args = [prepared["gsr"],"-w",recording["screen"],"-f",str(recording["fps"]),"-fm","cfr",
            "-k","h264","-q","very_high","-encoder","gpu","-fallback-cpu-encoding","no",
            "-p",str(prepared["plugin"])]
    sources = []
    if recording["game_audio"]:
        sources.append("default_output")
    if prepared["manifest"]["microphone"]:
        sources.append("device:"+prepared["manifest"]["microphone"])
    if sources:
        args += ["-a","|".join(sources)]  # One mixed track, clocks/encoding owned by GSR.
    return args+["-o",str(prepared["output"])]


def record(prepared, seconds=None, *, stop_event=None, on_started=None, emit=print):
    if prepared["assets_only"]:
        raise ValueError("grabación: requiere validación de dispositivos")
    output = prepared["output"]
    output.parent.mkdir(parents=True,exist_ok=True)
    log = Path(str(output)+".gsr.log")
    report = Path(str(output)+".report.json")
    if log.exists() or report.exists():
        raise ValueError("recording.output: ya existen log/informe para este nombre")
    # Exclusive reservation: never silently overwrite an existing user recording.
    with output.open("xb"):
        pass
    environment = {k:v for k,v in os.environ.items() if not k.startswith(("GSR_RUST_","GSR_OVERLAY_"))}
    with tempfile.TemporaryDirectory(prefix="gsr-scene-") as temporary:
        scene = Path(temporary)/"scene.json"
        scene.write_text(json.dumps(prepared["manifest"]))
        scene.chmod(0o600)
        environment["GSR_RUST_SCENE"] = str(scene)
        command = recording_command(prepared)
        result = {"command":command,"build":prepared["build"],"scene":prepared["manifest"],
                  "effective":prepared["effective"],"output":str(output),"returncode":None}
        emit("Grabando. Ctrl+C termina y cierra el archivo.",flush=True)
        with log.open("x") as stream:
            process = subprocess.Popen(command,env=environment,stdin=subprocess.DEVNULL,
                                       stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            started = time.monotonic()
            try:
                if on_started is not None:
                    on_started()
                while process.poll() is None:
                    if stop_event is not None and stop_event.is_set():
                        break
                    if seconds is not None and time.monotonic()-started>=seconds:
                        break
                    time.sleep(0.2)
            except KeyboardInterrupt:
                pass
            finally:
                # Reuse the existing orderly GSR stop. Signal GSR alone so its
                # audio helper stays alive until plugin deinit closes it.
                result["forced_stop"] = not stop(process)
            result["returncode"] = process.returncode
            result["elapsed_seconds"] = time.monotonic()-started
    text = log.read_text(errors="replace")
    plugin_ok = "name: rust-media-overlay" in text and "unloaded plugin: rust-media-overlay" in text
    failure = (process.returncode!=0 or not output.stat().st_size or not plugin_ok
               or "gsr-rust:" in text or result.get("forced_stop"))
    try:
        metadata = json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(output)]))
        result["video"] = metadata
        streams = metadata.get("streams",[])
        if not any(s.get("codec_type")=="video" for s in streams):
            failure = True
        expected_audio = prepared["profile"]["recording"]["game_audio"] or prepared["manifest"]["microphone"]
        if expected_audio and not any(s.get("codec_type")=="audio" for s in streams):
            failure = True
    except ValueError as error:
        result["probe_error"] = str(error)
        failure = True
    result["completed"] = not failure
    report.write_text(json.dumps(result,indent=2)+"\n")
    if failure:
        raise ValueError(f"grabación incompleta: revisa {log} y {report}; se conserva el archivo parcial")
    emit(f"Guardado: {output}\nLog: {log}\nInforme: {report}")
    return result


def ask(label, current="", cast=str):
    value = input(f"{label} [{current}]: ").strip()
    return current if not value else cast(value)


def yes(label, current):
    value = ask(label+" (s/n)","s" if current else "n").lower()
    if value not in ("s","n"):
        raise ValueError("usa s o n")
    return value=="s"


def choose(label, items):
    if not items:
        raise ValueError(f"{label}: no hay opciones disponibles")
    for i,(_,description) in enumerate(items,1):
        print(f"{i}. {description}")
    selected = int(input(label+" (número): "))
    if not 1<=selected<=len(items):
        raise ValueError("número fuera de la lista")
    return items[selected-1][0]


def edit_geometry(layer):
    layer["name"] = ask("Nombre",layer["name"])
    layer["x"] = ask("X",layer.get("x",32),int)
    layer["y"] = ask("Y",layer.get("y",32),int)
    for key,label in (("width","Ancho"),("height","Alto")):
        value = ask(label+" (- = automático)",str(layer.get(key,"-")))
        if value=="-":
            layer.pop(key,None)
        else:
            layer[key] = int(value)
    layer["keep_aspect"] = yes("Conservar proporción",layer.get("keep_aspect",True))
    layer["visible"] = yes("Visible",layer.get("visible",True))


def edit_layer(layer, base):
    if layer["kind"]=="avatar":
        for key,label in (("idle","GIF reposo"),("talking","GIF habla")):
            layer[key] = str(resolved(ask(label,layer.get(key,"")),base))
        layer["threshold"] = ask("Umbral RMS 0..1 (menor = más sensible)",layer.get("threshold",0.04),float)
        layer["release_ms"] = ask("Espera antes de reposo (ms)",layer.get("release_ms",250),int)
    else:
        layer["path"] = str(resolved(ask("Ruta PNG/JPG/GIF",layer.get("path","")),base))
    edit_geometry(layer)


def layers_menu(profile):
    while True:
        print("\nCapas (primera = fondo):")
        for i,layer in enumerate(profile["layers"],1):
            print(f"{i}. {layer['name']} [{layer['kind']}] {'visible' if layer.get('visible',True) else 'oculto'}")
        action = input("a agregar gráfico | v agregar avatar | e editar/reemplazar | o ocultar/mostrar | q quitar | r reordenar | 0 volver: ").strip()
        if action=="0":
            return
        candidate = copy.deepcopy(profile)
        try:
            layers = candidate["layers"]
            if action in ("a","v"):
                layer = {"name":"Avatar" if action=="v" else "Gráfico","kind":"avatar" if action=="v" else "graphic"}
                edit_layer(layer,profile["_base"])
                layers.append(layer)
            elif action in ("e","o","q","r"):
                index = choose("Capa",[(i,l["name"]) for i,l in enumerate(layers)])
                if action=="e":
                    edit_layer(layers[index],profile["_base"])
                elif action=="o":
                    layers[index]["visible"] = not layers[index].get("visible",True)
                elif action=="q":
                    layers.pop(index)
                else:
                    target = int(input(f"Nueva posición 1..{len(layers)}: "))-1
                    if not 0<=target<len(layers):
                        raise ValueError("posición fuera de rango")
                    layers.insert(target,layers.pop(index))
            else:
                raise ValueError("opción desconocida")
            profile.update(normalize(candidate,profile["_base"]))
        except (ValueError,OSError) as error:
            print(f"Corregir: {error}")


def show_devices(devices):
    print("Pantallas GSR:")
    for name,dimensions in devices.screens().items():
        print(f"  {name}: {dimensions[0]}×{dimensions[1]}")
    audio,inputs = devices.audio()
    print("Micrófonos (identificador | descripción):")
    print("  default_input | predeterminado del sistema (se valida antes de grabar)")
    for name,description in inputs.items():
        print(f"  {name} | {description}")
    print(f"Audio de juego/default_output: {'disponible' if 'default_output' in audio else 'no disponible'}")


def edit(profile, path, devices):
    print("Compositor GSR — edita antes de grabar. Rutas relativas a la carpeta del perfil.")
    try:
        show_devices(devices)
    except ValueError as error:
        print(f"Dispositivos sin consultar: {error}. Puedes editar y guardar; se revalidan antes de grabar.")
    while True:
        print(f"\nPerfil: {path or '(sin guardar)'} | pantalla: {profile['recording']['screen'] or '(sin elegir)'} | micrófono: {profile['recording']['microphone'] or '(desactivado)'} | capas: {len(profile['layers'])}")
        action = input("1 pantalla | 2 micrófono/audio | 3 salida/FPS | 4 capas/avatar | 5 guardar | 6 cargar | 7 validar/resumen | 8 grabar | 0 salir: ").strip()
        try:
            recording = profile["recording"]
            if action=="0":
                return
            if action=="1":
                recording["screen"] = choose("Pantalla",[(name,f"{name}: {w}×{h}") for name,(w,h) in devices.screens().items()])
            elif action=="2":
                _,inputs = devices.audio()
                recording["microphone"] = choose("Micrófono",[("default_input","Predeterminado del sistema"),("","Sin micrófono (requiere no tener avatar)")]+list(inputs.items()))
                recording["game_audio"] = yes("Grabar juego/audio del sistema",recording["game_audio"])
            elif action=="3":
                candidate = copy.deepcopy(profile)
                candidate["recording"]["output"] = str(resolved(ask("Archivo MKV, admite {timestamp}",recording["output"]),profile["_base"]))
                candidate["recording"]["fps"] = ask("FPS",recording["fps"],int)
                profile = normalize(candidate,profile["_base"])
            elif action=="4":
                layers_menu(profile)
            elif action=="5":
                selected = Path(ask("Guardar TOML",str(path or Path.cwd()/"perfil.toml"))).expanduser().resolve()
                profile = save_profile(profile,selected)
                path = selected
                print(f"Guardado: {path}")
            elif action=="6":
                selected = Path(input("TOML a cargar: ").strip()).expanduser().resolve()
                loaded = load_profile(selected)
                profile,path = loaded,selected
            elif action in ("7","8"):
                prepared = validate(profile,devices)
                summary(prepared)
                if action=="8" and yes("Iniciar grabación",False):
                    record(prepared)
            else:
                print("Elige una opción del menú.")
        except (ValueError,OSError,subprocess.SubprocessError) as error:
            print(f"Corregir: {error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action")
    commands.add_parser("devices",help="Listar pantallas y entradas reales")
    editor = commands.add_parser("edit",help="Crear/cargar y editar desde menú")
    editor.add_argument("profile",nargs="?",type=Path)
    check = commands.add_parser("check",help="Validar sin grabar")
    check.add_argument("profile",type=Path)
    check.add_argument("--assets-only",action="store_true",help="No consultar dispositivos; NO certifica captura/audio")
    capture = commands.add_parser("record",help="Grabar perfil sin menú; Ctrl+C para terminar")
    capture.add_argument("profile",type=Path)
    capture.add_argument("--seconds",type=float,help="Parada automática opcional")
    args = parser.parse_args()
    if args.action=="record" and args.seconds is not None and not 1<=args.seconds<=7200:
        parser.error("--seconds: 1..7200")
    try:
        devices = Devices()
        if args.action=="devices":
            show_devices(devices)
        elif args.action in (None,"edit"):
            path = getattr(args,"profile",None)
            if path is not None:
                path = path.expanduser().resolve()
            profile = load_profile(path) if path is not None and path.exists() else new_profile(path.parent if path else Path.cwd())
            edit(profile,path,devices)
        else:
            profile = load_profile(args.profile)
            prepared = validate(profile,devices,getattr(args,"assets_only",False))
            summary(prepared)
            if args.action=="record":
                record(prepared,args.seconds)
        return 0
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print(f"Corregir: {error}",file=sys.stderr)
        return 2
    except (KeyboardInterrupt,EOFError):
        print("\nCerrado.")
        return 130


if __name__=="__main__":
    sys.exit(main())
