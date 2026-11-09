"""Versioned, small TOML profile. No device names or personal paths in defaults."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import tomllib

DEFAULT_RECORDING = {"screen": "", "output": "recordings/{timestamp}.mkv", "fps": 30,
                     "game_audio": True, "microphone": "default_input"}
COMMON = {"name", "kind", "path", "idle", "talking", "x", "y", "width", "height", "visible", "keep_aspect", "threshold", "release_ms"}


def new_profile(base):
    return {"schema_version": 2, "recording": DEFAULT_RECORDING.copy(), "layers": [], "_base": Path(base).resolve()}


def resolved(value, base):
    path = Path(value).expanduser()
    return path if path.is_absolute() else (Path(base)/path).resolve()


def normalize(data, base):
    data = copy.deepcopy(data)
    if not isinstance(data, dict):
        raise ValueError("perfil: tabla TOML requerida")
    version = data.get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("schema_version: se admite 1 o 2")
    # No TOML profiles existed in the inspected tree. Support the documented
    # single-element v1 shape as an import, without changing old env/script CLIs.
    if version == 1:
        element = data.pop("element", None)
        media = data.pop("media", None)
        if element is not None or media is not None:
            element = dict(element or {})
            if media is not None:
                element.setdefault("path", media)
            if "media" in element:
                element.setdefault("path", element.pop("media"))
            element.setdefault("name", "Elemento")
            element.setdefault("kind", "graphic")
            if "layers" in data:
                raise ValueError("perfil v1: no mezclar element/media y layers")
            data["layers"] = [element]
        data["schema_version"] = 2
    unknown = set(data)-{"schema_version", "recording", "layers", "_base"}
    if unknown:
        raise ValueError(f"perfil: claves desconocidas {sorted(unknown)}")
    if not isinstance(data.get("recording", {}), dict):
        raise ValueError("recording: tabla requerida")
    recording = DEFAULT_RECORDING | data.get("recording", {})
    if set(recording)-set(DEFAULT_RECORDING):
        raise ValueError("recording: clave desconocida")
    for key in ("screen", "output", "microphone"):
        if not isinstance(recording[key], str) or "\x00" in recording[key]:
            raise ValueError(f"recording.{key}: se requiere texto sin NUL")
    if not recording["output"] or not recording["output"].endswith(".mkv"):
        raise ValueError("recording.output: elige un archivo .mkv (puede incluir {timestamp})")
    if "{" in recording["output"].replace("{timestamp}", "") or "}" in recording["output"].replace("{timestamp}", ""):
        raise ValueError("recording.output: solo se admite la plantilla {timestamp}")
    if type(recording["fps"]) is not int or not 1 <= recording["fps"] <= 120:
        raise ValueError("recording.fps: entero 1..120")
    if type(recording["game_audio"]) is not bool:
        raise ValueError("recording.game_audio: booleano")
    layers = data.get("layers", [])
    if not isinstance(layers, list) or len(layers)>16:
        raise ValueError("layers: lista de hasta 16 capas")
    out = []
    avatars = 0
    for index, raw in enumerate(layers):
        prefix = f"layers[{index+1}]"
        if not isinstance(raw, dict) or set(raw)-COMMON:
            raise ValueError(f"{prefix}: tabla o clave inválida")
        layer = {"name": f"Capa {index+1}", "kind": "graphic", "x": 32, "y": 32,
                 "visible": True, "keep_aspect": True} | raw
        if not isinstance(layer["name"],str) or not 1 <= len(layer["name"].encode()) <= 128:
            raise ValueError(f"{prefix}.name: 1..128 bytes")
        for key in ("x", "y", "width", "height"):
            if key in layer and (type(layer[key]) is not int or not (-16384 if key in ("x", "y") else 1) <= layer[key] <= 16384):
                raise ValueError(f"{prefix}.{key}: entero fuera de rango")
        for key in ("visible", "keep_aspect"):
            if type(layer[key]) is not bool:
                raise ValueError(f"{prefix}.{key}: booleano")
        if not layer["keep_aspect"] and not all(key in layer for key in ("width", "height")):
            raise ValueError(f"{prefix}: deformar requiere width y height")
        if layer["kind"] == "graphic":
            paths = ("path",)
            if any(k in layer for k in ("idle", "talking", "threshold", "release_ms")):
                raise ValueError(f"{prefix}: una capa graphic solo usa path")
        elif layer["kind"] == "avatar":
            avatars += 1
            paths = ("idle", "talking")
            if "path" in layer or avatars>1:
                raise ValueError(f"{prefix}: máximo un avatar; usa idle/talking")
            layer.setdefault("threshold", 0.04)
            layer.setdefault("release_ms", 250)
            value = layer["threshold"]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError(f"{prefix}.threshold: número RMS mayor de 0 y hasta 1")
            if type(layer["release_ms"]) is not int or not 0 <= layer["release_ms"] <= 5000:
                raise ValueError(f"{prefix}.release_ms: entero 0..5000")
        else:
            raise ValueError(f"{prefix}.kind: graphic o avatar")
        for key in paths:
            if not isinstance(layer.get(key), str) or not layer[key] or "\x00" in layer[key]:
                raise ValueError(f"{prefix}.{key}: ruta obligatoria")
            layer[key] = str(resolved(layer[key], base))
        out.append(layer)
    if avatars and not recording["microphone"]:
        raise ValueError("recording.microphone: el avatar necesita una entrada de audio")
    recording["output"] = str(resolved(recording["output"], base))
    return {"schema_version": 2, "recording": recording, "layers": out, "_base": Path(base).resolve()}


def load_profile(path):
    path = Path(path).expanduser().resolve()
    if path.stat().st_size > 128*1024:
        raise ValueError("perfil excede 128 KiB")
    with path.open("rb") as file:
        data = tomllib.load(file)
    return normalize(data, path.parent)


def save_profile(profile, path):
    path = Path(path).expanduser().resolve()
    data = normalize(profile, profile["_base"])
    def value(v):
        if isinstance(v, str):
            return json.dumps(v, ensure_ascii=False)
        if type(v) is bool:
            return "true" if v else "false"
        return str(v)
    def relative(p):
        return os.path.relpath(p, path.parent)
    recording = data["recording"].copy()
    recording["output"] = relative(recording["output"])
    lines = ["schema_version = 2", "", "[recording]"]
    lines += [f"{key} = {value(v)}" for key,v in recording.items()]
    for raw in data["layers"]:
        layer = raw.copy()
        for key in ("path", "idle", "talking"):
            if key in layer:
                layer[key] = relative(layer[key])
        lines += ["", "[[layers]]"] + [f"{key} = {value(v)}" for key,v in layer.items()]
    text = "\n".join(lines)+"\n"
    if len(text.encode("utf-8")) > 128*1024:
        raise ValueError("perfil excede 128 KiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,delete=False) as file:
            temporary = Path(file.name)
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    data["_base"] = path.parent
    return data
