"""TUI state and geometry; the existing TOML and Rust loader remain authoritative."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile

import compositor as backend
from compositor_profile import load_profile, new_profile, normalize, resolved, save_profile

CORNERS = ("Superior izquierda", "Superior derecha", "Inferior izquierda", "Inferior derecha")


def session_path():
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home()/".local/state")).expanduser()
    # Keep the established data location; renaming the app must not move user data.
    return base/"xolo/session.json"


def remember(path, state_file=None):
    target = state_file or session_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump({"last_profile":str(Path(path).resolve())},file)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def initial_path(explicit=None, cwd=None, state_file=None):
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    target = state_file or session_path()
    if target.is_file():
        try:
            last = json.loads(target.read_text()).get("last_profile")
            if isinstance(last,str) and last:
                return Path(last).expanduser().resolve()
        except (ValueError,OSError):
            pass
    default = (Path(cwd) if cwd else Path.cwd())/"perfil.toml"
    return default.resolve()


def corner_position(canvas, effective, corner, margin):
    if corner not in range(4) or not 0<=margin<=4096:
        raise ValueError("esquina/margen inválido")
    width,height = map(math.ceil,effective)
    cw,ch = canvas
    if width+2*margin>cw or height+2*margin>ch:
        raise ValueError("Tamaño: la capa no cabe con ese margen; reduce la caja o el margen")
    return (cw-width-margin if corner%2 else margin,
            ch-height-margin if corner>=2 else margin)


class Model:
    def __init__(self, path, state_file=None):
        self.path = Path(path).expanduser().resolve()
        self.state_file = state_file
        self.profile = load_profile(self.path) if self.path.exists() else new_profile(self.path.parent)
        self.profile = normalize(self.profile,self.profile["_base"])
        self.saved = copy.deepcopy(self.profile)
        self.is_new = not self.path.exists()
        self.screens = {}
        self.inputs = {}
        self.audio_devices = {}
        self.errors = {}
        self.selected = 0
        self.last_video = None
        self.last_success = None

    @property
    def dirty(self):
        return self.profile != self.saved

    @property
    def output_folder(self):
        return Path(self.profile["recording"]["output"]).parent

    @property
    def output_name(self):
        return Path(self.profile["recording"]["output"]).name

    def commit(self, candidate):
        self.profile = normalize(candidate,self.profile["_base"])

    def set_recording(self, key, value):
        candidate = copy.deepcopy(self.profile)
        candidate["recording"][key] = value
        self.commit(candidate)

    def set_folder(self, folder):
        folder = resolved(folder,self.profile["_base"])
        if "{" in str(folder) or "}" in str(folder):
            raise ValueError("Carpeta: {timestamp} solo se permite en el nombre del video")
        self.set_recording("output",str(folder/self.output_name))

    def set_name(self, name):
        if not name or name in (".","..") or "/" in name or "\\" in name:
            raise ValueError("Nombre: escribe solo el archivo .mkv, sin carpetas")
        self.set_recording("output",str(self.output_folder/name))

    def set_layer(self, index, key, value):
        candidate = copy.deepcopy(self.profile)
        if value is None:
            candidate["layers"][index].pop(key,None)
        else:
            if key in ("path","idle","talking"):
                value = str(resolved(value,self.profile["_base"]))
            candidate["layers"][index][key] = value
        self.commit(candidate)

    def add_layer(self, layer):
        candidate = copy.deepcopy(self.profile)
        candidate["layers"].append(layer)
        self.commit(candidate)
        self.selected = len(self.profile["layers"])-1

    def remove_layer(self, index):
        candidate = copy.deepcopy(self.profile)
        candidate["layers"].pop(index)
        self.commit(candidate)
        self.selected = max(0,min(index,len(candidate["layers"])-1))

    def move_layer(self, index, delta):
        target = index+delta
        if not 0<=target<len(self.profile["layers"]):
            return
        candidate = copy.deepcopy(self.profile)
        candidate["layers"].insert(target,candidate["layers"].pop(index))
        self.commit(candidate)
        self.selected = target

    def geometry(self, index, layer=None):
        profile = copy.deepcopy(self.profile)
        profile["layers"] = [layer or profile["layers"][index]]
        return backend.inspect_scene(profile,profile["recording"]["microphone"])["layers"][0]

    def place(self, index, corner, size, margin=20):
        screen = self.profile["recording"]["screen"]
        if screen not in self.screens:
            raise ValueError("Pantalla: elige un monitor disponible antes de colocar por esquina")
        candidate = copy.deepcopy(self.profile)
        layer = candidate["layers"][index]
        layer.update(width=size,height=size,keep_aspect=True)
        # The same decoder and aspect rules as production, including non-square
        # sources and the avatar's common idle box. No Python image dependency.
        candidate = normalize(candidate,candidate["_base"])
        effective = self.geometry(index,candidate["layers"][index])
        x,y = corner_position(self.screens[screen],(effective["width"],effective["height"]),corner,margin)
        candidate["layers"][index].update(x=x,y=y)
        self.commit(candidate)
        return effective | {"x":x,"y":y}

    def placement_hint(self,index):
        layer=self.profile["layers"][index]
        fallback=(3,max(layer.get("width",320),layer.get("height",0)),20)
        canvas=self.screens.get(self.profile["recording"]["screen"])
        if canvas is None: return fallback
        try: effective=self.geometry(index)
        except (ValueError,OSError): return fallback
        width,height=math.ceil(effective["width"]),math.ceil(effective["height"])
        size=max(width,height)
        for corner in range(4):
            xgap=canvas[0]-width-layer["x"] if corner%2 else layer["x"]
            ygap=canvas[1]-height-layer["y"] if corner>=2 else layer["y"]
            if xgap==ygap and 0<=xgap<=4096:
                return corner,size,xgap
        return 3,size,20

    def save(self, path=None):
        target = Path(path).expanduser().resolve() if path else self.path
        data = save_profile(self.profile,target)
        self.profile,self.path = data,target
        self.saved = copy.deepcopy(data)
        self.is_new = False
        return target

    def load(self, path):
        target = Path(path).expanduser().resolve()
        loaded = load_profile(target)
        self.profile,self.path = loaded,target
        self.saved = copy.deepcopy(loaded)
        self.is_new = False
        self.selected = 0
        self.errors.clear()


def browser_entries(folder, suffixes=None, directories=False):
    """Stable directory-first listing. It never follows symlinks recursively."""
    folder = Path(folder)
    entries = []
    for path in folder.iterdir():
        try:
            if path.is_dir() or (not directories and path.is_file() and
                               (suffixes is None or path.suffix.lower() in suffixes)):
                entries.append(path)
        except OSError:
            continue
    return sorted(entries,key=lambda p:(not p.is_dir(),p.name.casefold()))
